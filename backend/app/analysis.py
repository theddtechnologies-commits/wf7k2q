"""Glue between cached data, processing and metrics.

Data is loaded once per process and results are memoised per parameter set, so
repeated requests (and warm serverless invocations) are effectively free.
"""

from datetime import date, time
from functools import lru_cache
from typing import Any

import pandas as pd

from . import elexon, metrics, processing


@lru_cache(maxsize=1)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(hourly actuals, all forecasts). Callers must not mutate the returned frames."""
    return processing.to_hourly(elexon.load_actuals()), elexon.load_forecasts()


@lru_cache(maxsize=128)
def timeseries(start: date, end: date, cutoff: time, days_before: int) -> pd.DataFrame:
    """Hourly actuals in range, left-joined with the decision-time forecast."""
    actuals, forecasts = load_data()
    selected = processing.select_latest_forecasts(forecasts, cutoff, days_before)
    df = processing.filter_delivery_range(actuals, start, end).merge(
        selected, on="start_time", how="left"
    )
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df


@lru_cache(maxsize=128)
def accuracy(
    start: date, end: date, cutoff: time, days_before: int, confidence: float
) -> dict[str, Any] | None:
    """All accuracy outputs for one parameter set, or None if nothing matched."""
    df = timeseries(start, end, cutoff, days_before)
    matched = df.dropna(subset=["forecast_mw"])
    if matched.empty:
        return None
    return {
        "summary": {**metrics.summary(matched), "coverage_pct": len(matched) / len(df) * 100},
        "by_hour": metrics.by_hour(matched, confidence),
        "by_day": metrics.by_day(matched),
        "histogram": metrics.histogram(matched["error_mw"]),
        "recommendation": metrics.recommendation(matched, confidence),
    }


@lru_cache(maxsize=32)
def horizon(start: date, end: date, bucket_hours: int) -> list[dict[str, Any]]:
    """Error vs lead time using every forecast for target times in range."""
    actuals, forecasts = load_data()
    pairs = processing.filter_delivery_range(processing.horizon_pairs(forecasts, actuals), start, end)
    return metrics.horizon_curve(pairs, bucket_hours) if not pairs.empty else []
