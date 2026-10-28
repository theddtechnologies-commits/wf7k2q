"""Pydantic response models: the typed contract between backend and frontend."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class AnalysisParams(BaseModel):
    start: date
    end: date
    cutoff_time: str = Field(description="Decision cutoff, UK local time (HH:MM)")
    cutoff_days_before: int


class Meta(BaseModel):
    delivery_start: date
    delivery_end: date
    default_cutoff_time: str
    default_cutoff_days_before: int
    default_confidence: float
    cutoff_rationale: str
    actuals_rows: int
    forecast_rows: int
    forecast_publishes: int


class TimeseriesPoint(BaseModel):
    start_time: datetime
    actual_mw: float
    forecast_mw: float | None
    publish_time: datetime | None
    horizon_h: float | None
    error_mw: float | None


class TimeseriesResponse(BaseModel):
    params: AnalysisParams
    points: list[TimeseriesPoint]


class Summary(BaseModel):
    n: int
    coverage_pct: float = Field(description="Share of hours with actuals that had a forecast")
    mae_mw: float
    rmse_mw: float
    bias_mw: float = Field(description="Mean of forecast - actual; positive = over-forecast")
    nmae_pct_of_mean_actual: float
    nmae_pct_of_max_actual: float
    p10_error_mw: float
    p50_error_mw: float
    p90_error_mw: float
    p90_abs_error_mw: float
    mean_actual_mw: float
    max_actual_mw: float


class HourStats(BaseModel):
    hour: int
    n: int
    mae_mw: float
    bias_mw: float
    p10_error_mw: float
    p90_error_mw: float
    buffer_mw: float


class DayStats(BaseModel):
    date: date
    n: int
    mae_mw: float
    bias_mw: float
    mean_actual_mw: float
    mean_forecast_mw: float


class HistogramBin(BaseModel):
    bin_start_mw: float
    bin_end_mw: float
    count: int


class Recommendation(BaseModel):
    confidence: float
    buffer_mw: float
    buffer_pct_of_mean_forecast: float
    shortfall_hours_pct: float
    riskiest_hours: list[int]
    headline: str


class MetricsResponse(BaseModel):
    params: AnalysisParams
    summary: Summary
    by_hour: list[HourStats]
    by_day: list[DayStats]
    histogram: list[HistogramBin]
    recommendation: Recommendation


class HorizonBucket(BaseModel):
    horizon_start_h: int
    horizon_end_h: int
    n: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    p90_abs_error_mw: float


class HorizonResponse(BaseModel):
    start: date
    end: date
    bucket_hours: int
    buckets: list[HorizonBucket]
