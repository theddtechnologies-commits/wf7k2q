"""Forecast accuracy metrics on aligned frames (columns: start_time, actual_mw,
forecast_mw, error_mw, and horizon_h where relevant).

Sign convention (see processing.py): error = forecast - actual, so a positive error
is a shortfall of wind versus what the buyer planned for.
"""

import math
from typing import Any

import numpy as np
import pandas as pd

from .config import UK_TZ

# Candidate histogram bin widths (MW); the smallest giving at most ~30 bins is used.
_BIN_WIDTHS = (50, 100, 200, 250, 500, 1000, 2000, 5000)


def _q(values: pd.Series, q: float) -> float:
    return float(np.quantile(values, q))


def summary(df: pd.DataFrame) -> dict[str, Any]:
    """Headline accuracy statistics for a set of matched forecast/actual pairs."""
    err = df["error_mw"]
    abs_err = err.abs()
    actual = df["actual_mw"]
    return {
        "n": int(len(df)),
        "mae_mw": float(abs_err.mean()),
        "rmse_mw": float(math.sqrt((err**2).mean())),
        "bias_mw": float(err.mean()),
        # Normalised MAE. MAPE is avoided because it explodes in low-wind hours.
        "nmae_pct_of_mean_actual": float(abs_err.sum() / actual.sum() * 100),
        "nmae_pct_of_max_actual": float(abs_err.mean() / actual.max() * 100),
        "p10_error_mw": _q(err, 0.10),
        "p50_error_mw": _q(err, 0.50),
        "p90_error_mw": _q(err, 0.90),
        "p90_abs_error_mw": _q(abs_err, 0.90),
        "mean_actual_mw": float(actual.mean()),
        "max_actual_mw": float(actual.max()),
    }


def by_hour(df: pd.DataFrame, confidence: float) -> list[dict[str, Any]]:
    """Error statistics per UK local hour of day (0–23)."""
    hours = df["start_time"].dt.tz_convert(UK_TZ).dt.hour
    rows = []
    for hour, group in df.groupby(hours):
        err = group["error_mw"]
        rows.append(
            {
                "hour": int(hour),
                "n": int(len(group)),
                "mae_mw": float(err.abs().mean()),
                "bias_mw": float(err.mean()),
                "p10_error_mw": _q(err, 0.10),
                "p90_error_mw": _q(err, 0.90),
                "buffer_mw": max(0.0, _q(err, confidence)),
            }
        )
    return rows


def by_day(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Error statistics per UK delivery day."""
    days = df["start_time"].dt.tz_convert(UK_TZ).dt.date
    rows = []
    for day, group in df.groupby(days):
        err = group["error_mw"]
        rows.append(
            {
                "date": day.isoformat(),
                "n": int(len(group)),
                "mae_mw": float(err.abs().mean()),
                "bias_mw": float(err.mean()),
                "mean_actual_mw": float(group["actual_mw"].mean()),
                "mean_forecast_mw": float(group["forecast_mw"].mean()),
            }
        )
    return rows


def histogram(errors: pd.Series, max_bins: int = 30) -> list[dict[str, Any]]:
    """Counts of errors in fixed-width bins aligned to multiples of the width (0 is an edge)."""
    if errors.empty:
        return []
    lo, hi = float(errors.min()), float(errors.max())
    width = next((w for w in _BIN_WIDTHS if (hi - lo) / w <= max_bins), _BIN_WIDTHS[-1])
    start = math.floor(lo / width) * width
    stop = (math.floor(hi / width) + 1) * width
    edges = np.arange(start, stop + width / 2, width)
    counts, _ = np.histogram(errors, bins=edges)
    return [
        {"bin_start_mw": float(a), "bin_end_mw": float(b), "count": int(c)}
        for a, b, c in zip(edges[:-1], edges[1:], counts)
    ]


def horizon_curve(pairs: pd.DataFrame, bucket_hours: int = 3) -> list[dict[str, Any]]:
    """Accuracy as a function of forecast lead time, in `bucket_hours`-wide buckets."""
    buckets = (pairs["horizon_h"] // bucket_hours * bucket_hours).astype(int)
    rows = []
    for start, group in pairs.groupby(buckets):
        err = group["error_mw"]
        rows.append(
            {
                "horizon_start_h": int(start),
                "horizon_end_h": int(start + bucket_hours),
                "n": int(len(group)),
                "mae_mw": float(err.abs().mean()),
                "rmse_mw": float(math.sqrt((err**2).mean())),
                "bias_mw": float(err.mean()),
                "p90_abs_error_mw": _q(err.abs(), 0.90),
            }
        )
    return rows


def _hours_in_n(pct: int) -> str:
    """Confidence as plain odds: 90 -> "9 hours in 10", 95 -> "19 hours in 20"."""
    for n in (10, 20, 100):
        if pct * n % 100 == 0:
            return f"{pct * n // 100} hours in {n}"
    return f"{pct} hours in 100"


def recommendation(df: pd.DataFrame, confidence: float) -> dict[str, Any]:
    """Procurement buffer: the error quantile at `confidence`.

    If the buyer adds `buffer_mw` on top of the forecast, historical shortfalls were
    covered in `confidence` of hours. Negative quantiles mean no buffer is needed.
    """
    err = df["error_mw"]
    buffer = max(0.0, _q(err, confidence))
    hourly = sorted(by_hour(df, confidence), key=lambda r: r["buffer_mw"], reverse=True)
    pct = round(confidence * 100)
    bias = float(err.mean())
    bias_text = (
        f"On average the forecast was {abs(bias):,.0f} MW too "
        f"{'high' if bias > 0 else 'low'}."
    )
    return {
        "confidence": confidence,
        "buffer_mw": buffer,
        "buffer_pct_of_mean_forecast": float(buffer / df["forecast_mw"].mean() * 100),
        "shortfall_hours_pct": float((err > 0).mean() * 100),
        "riskiest_hours": [r["hour"] for r in hourly[:3]],
        "headline": (
            f"In {pct}% of hours, actual wind was no more than {buffer:,.0f} MW below the "
            f"forecast, so consider procuring an extra {buffer:,.0f} MW to cover "
            f"{_hours_in_n(pct)}. {bias_text}"
        ),
    }
