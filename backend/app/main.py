"""FastAPI application exposing the wind forecast accuracy API under /api.

All routes live under /api so the same app works behind the Vite dev proxy, the
nginx container and Vercel's /api rewrite without path rewriting.
"""

from datetime import date, time
from typing import Annotated, Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.gzip import GZipMiddleware

from . import analysis, config
from .schemas import (
    AnalysisParams,
    HorizonResponse,
    Meta,
    MetricsResponse,
    TimeseriesPoint,
    TimeseriesResponse,
)

app = FastAPI(
    title="GB Wind Forecast Accuracy API",
    description="Day-ahead wind forecast vs actual generation for January 2026 (Elexon BMRS).",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.middleware("http")
async def cache_headers(request: Request, call_next: Any) -> Response:
    """The underlying data is a fixed historical snapshot, so let CDNs cache responses."""
    response: Response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        response.headers["Cache-Control"] = "public, max-age=300, s-maxage=86400"
    return response


_HHMM = r"^([01]\d|2[0-3]):[0-5]\d$"


def common_params(
    start: Annotated[date, Query(description="First UK delivery day (inclusive)")] = config.DELIVERY_START,
    end: Annotated[date, Query(description="Last UK delivery day (inclusive)")] = config.DELIVERY_END,
    cutoff_time: Annotated[
        str, Query(pattern=_HHMM, description="Decision cutoff, UK local time")
    ] = config.DEFAULT_CUTOFF_TIME.strftime("%H:%M"),
    cutoff_days_before: Annotated[
        int, Query(ge=1, le=2, description="Days before delivery the decision is made")
    ] = config.DEFAULT_CUTOFF_DAYS_BEFORE,
) -> AnalysisParams:
    if start > end:
        raise HTTPException(422, "start must be on or before end")
    if start < config.DELIVERY_START or end > config.DELIVERY_END:
        raise HTTPException(
            422, f"Dates must be within {config.DELIVERY_START} and {config.DELIVERY_END}"
        )
    return AnalysisParams(
        start=start, end=end, cutoff_time=cutoff_time, cutoff_days_before=cutoff_days_before
    )


Params = Annotated[AnalysisParams, Depends(common_params)]


def _cutoff(params: AnalysisParams) -> time:
    return time.fromisoformat(params.cutoff_time)


def _optional(value: Any) -> Any:
    """Map pandas missing values (NaN/NaT) to None and Timestamps to datetimes."""
    if pd.isna(value):
        return None
    return value.to_pydatetime() if isinstance(value, pd.Timestamp) else value


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/meta", response_model=Meta)
def meta() -> Meta:
    actuals, forecasts = analysis.load_data()
    return Meta(
        delivery_start=config.DELIVERY_START,
        delivery_end=config.DELIVERY_END,
        default_cutoff_time=config.DEFAULT_CUTOFF_TIME.strftime("%H:%M"),
        default_cutoff_days_before=config.DEFAULT_CUTOFF_DAYS_BEFORE,
        default_confidence=config.DEFAULT_CONFIDENCE,
        cutoff_rationale=(
            "Gate closure of the Nord Pool (N2EX) GB day-ahead auction: 09:50 UK time on "
            "the day before delivery. EPEX SPOT's GB day-ahead auction closes at 09:20."
        ),
        actuals_rows=len(actuals),
        forecast_rows=len(forecasts),
        forecast_publishes=int(forecasts["publish_time"].nunique()),
    )


@app.get("/api/timeseries", response_model=TimeseriesResponse)
def timeseries(params: Params) -> TimeseriesResponse:
    """Hourly actual generation and the latest forecast available at the decision cutoff."""
    df = analysis.timeseries(params.start, params.end, _cutoff(params), params.cutoff_days_before)
    points = [
        TimeseriesPoint(
            start_time=row.start_time.to_pydatetime(),
            actual_mw=row.actual_mw,
            forecast_mw=_optional(row.forecast_mw),
            publish_time=_optional(row.publish_time),
            horizon_h=_optional(row.horizon_h),
            error_mw=_optional(row.error_mw),
        )
        for row in df.itertuples(index=False)
    ]
    return TimeseriesResponse(params=params, points=points)


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(
    params: Params,
    confidence: Annotated[
        float, Query(ge=0.5, le=0.99, description="Confidence level for the buffer")
    ] = config.DEFAULT_CONFIDENCE,
) -> MetricsResponse:
    """Accuracy metrics and procurement buffer for decision-time forecasts."""
    result = analysis.accuracy(
        params.start, params.end, _cutoff(params), params.cutoff_days_before, round(confidence, 2)
    )
    if result is None:
        raise HTTPException(404, "No forecasts available for these settings")
    return MetricsResponse(params=params, **result)


@app.get("/api/horizon", response_model=HorizonResponse)
def horizon(
    params: Params,
    bucket_hours: Annotated[int, Query(ge=1, le=12)] = 3,
) -> HorizonResponse:
    """Error vs forecast lead time using every published forecast (cutoff not applied)."""
    buckets = analysis.horizon(params.start, params.end, bucket_hours)
    return HorizonResponse(
        start=params.start, end=params.end, bucket_hours=bucket_hours, buckets=buckets
    )
