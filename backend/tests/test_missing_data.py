"""Missing values must become gaps (NaN/null), never zeros, and never enter the metrics."""

from datetime import date, time

import pandas as pd
import pytest

from app import analysis


def ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


@pytest.fixture
def tiny_data(monkeypatch: pytest.MonkeyPatch):
    # Hours 00, 01, 02 on 10 Jan have actuals; only 00 and 01 have a forecast before the cutoff.
    actuals = pd.DataFrame(
        {"start_time": [ts("2026-01-10 00:00"), ts("2026-01-10 01:00"), ts("2026-01-10 02:00")],
         "actual_mw": [1000.0, 2000.0, 3000.0]}
    )
    forecasts = pd.DataFrame(
        {"publish_time": [ts("2026-01-09 09:30")] * 2 + [ts("2026-01-09 11:30")],  # last one is after cutoff
         "start_time": [ts("2026-01-10 00:00"), ts("2026-01-10 01:00"), ts("2026-01-10 02:00")],
         "forecast_mw": [1100.0, 2300.0, 9999.0]}
    )
    analysis.timeseries.cache_clear()
    analysis.accuracy.cache_clear()
    monkeypatch.setattr(analysis, "load_data", lambda: (actuals, forecasts))
    yield
    analysis.timeseries.cache_clear()
    analysis.accuracy.cache_clear()


def test_hour_without_forecast_is_nan_not_zero(tiny_data: None) -> None:
    df = analysis.timeseries(date(2026, 1, 10), date(2026, 1, 10), time(9, 50), 1)
    gap = df[df.start_time == ts("2026-01-10 02:00")].iloc[0]
    assert pd.isna(gap.forecast_mw) and pd.isna(gap.error_mw)
    assert gap.actual_mw == 3000.0


def test_metrics_ignore_missing_hours(tiny_data: None) -> None:
    result = analysis.accuracy(date(2026, 1, 10), date(2026, 1, 10), time(9, 50), 1, 0.9)
    s = result["summary"]
    assert s["n"] == 2  # the uncovered hour is excluded, not counted as a 0 MW forecast
    assert s["mae_mw"] == pytest.approx((100 + 300) / 2)
    assert s["bias_mw"] == pytest.approx(200)
    assert s["coverage_pct"] == pytest.approx(200 / 3)
