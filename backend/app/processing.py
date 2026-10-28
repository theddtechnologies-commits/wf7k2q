"""Alignment of actuals and forecasts, and the decision-time forecast selection.

Conventions used throughout:
- All timestamps are timezone-aware UTC; "delivery day" is the UK local calendar day.
- WINDFOR is hourly while FUELHH is half-hourly, so actuals are averaged to hourly
  means (labelled by the hour start) before they are compared with forecasts.
- error_mw = forecast_mw - actual_mw  → positive means the forecast was too high,
  i.e. less wind arrived than expected and the buyer was short.
"""

from datetime import date, time

import numpy as np
import pandas as pd

from .config import UK_TZ


def to_hourly(actuals: pd.DataFrame) -> pd.DataFrame:
    """Average half-hourly outturn into hourly means; drop hours missing a half-hour."""
    series = actuals.set_index("start_time")["actual_mw"].resample("1h")
    hourly = series.mean()[series.count() == 2]
    return hourly.rename("actual_mw").reset_index()


def delivery_date(start_times: pd.Series) -> pd.Series:
    """UK local calendar date each UTC timestamp is delivered on."""
    return start_times.dt.tz_convert(UK_TZ).dt.date


def decision_cutoff(start_times: pd.Series, cutoff_time: time, days_before: int) -> pd.Series:
    """Decision cutoff (UTC) for each target time.

    The cutoff is `cutoff_time` UK local time, `days_before` days before the target's
    UK delivery day. Working on naive local wall-clock time and localising at the end
    keeps the cutoff at e.g. 09:50 local even across a BST/GMT change.
    """
    local_midnight = start_times.dt.tz_convert(UK_TZ).dt.tz_localize(None).dt.normalize()
    cutoff_local = (
        local_midnight
        - pd.Timedelta(days=days_before)
        + pd.Timedelta(hours=cutoff_time.hour, minutes=cutoff_time.minute)
    )
    return cutoff_local.dt.tz_localize(
        UK_TZ, ambiguous=np.zeros(len(cutoff_local), dtype=bool), nonexistent="shift_forward"
    ).dt.tz_convert("UTC")


def select_latest_forecasts(
    forecasts: pd.DataFrame, cutoff_time: time, days_before: int
) -> pd.DataFrame:
    """For each target start_time, keep the most recent forecast published at or before
    its decision cutoff (and never after the target time itself).

    Returns columns: start_time, publish_time, forecast_mw, horizon_h.
    """
    cutoffs = decision_cutoff(forecasts["start_time"], cutoff_time, days_before)
    eligible = forecasts[
        (forecasts["publish_time"] <= cutoffs)
        & (forecasts["publish_time"] <= forecasts["start_time"])
    ]
    latest = (
        eligible.sort_values("publish_time")
        .drop_duplicates("start_time", keep="last")
        .sort_values("start_time")
        .reset_index(drop=True)
    )
    latest["horizon_h"] = (latest["start_time"] - latest["publish_time"]) / pd.Timedelta(hours=1)
    return latest[["start_time", "publish_time", "forecast_mw", "horizon_h"]]


def align(hourly_actuals: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    """Inner-join forecasts to hourly actuals on start_time and compute the error."""
    merged = forecasts.merge(hourly_actuals, on="start_time", how="inner")
    merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    return merged.sort_values(["start_time"]).reset_index(drop=True)


def filter_delivery_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Keep rows whose UK delivery date lies in [start, end] (inclusive)."""
    days = delivery_date(df["start_time"])
    return df[(days >= start) & (days <= end)].reset_index(drop=True)


def horizon_pairs(forecasts: pd.DataFrame, hourly_actuals: pd.DataFrame) -> pd.DataFrame:
    """Every (forecast, actual) pair regardless of cutoff, with its lead time in hours.

    Forecast rows for times already in the past when published (negative horizon)
    are dropped: they are not forecasts in any useful sense.
    """
    pairs = align(hourly_actuals, forecasts)
    pairs["horizon_h"] = (pairs["start_time"] - pairs["publish_time"]) / pd.Timedelta(hours=1)
    return pairs[pairs["horizon_h"] >= 0].reset_index(drop=True)
