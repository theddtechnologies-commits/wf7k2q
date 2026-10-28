import math

import pandas as pd
import pytest

from app import metrics


def aligned(errors: list[float], actuals: list[float], hours: list[int] | None = None) -> pd.DataFrame:
    """Hand-made aligned frame: forecast = actual + error."""
    hours = hours or list(range(len(errors)))
    return pd.DataFrame(
        {
            "start_time": [pd.Timestamp(f"2026-01-10 {h:02d}:00", tz="UTC") for h in hours],
            "actual_mw": actuals,
            "forecast_mw": [a + e for a, e in zip(actuals, errors)],
            "error_mw": errors,
        }
    )


# errors -100, 0, 100, 200 on actuals 500..2000: every statistic is easy to verify by hand.
SAMPLE = aligned([-100, 0, 100, 200], [500, 1000, 1500, 2000])


def test_summary_known_values() -> None:
    s = metrics.summary(SAMPLE)
    assert s["n"] == 4
    assert s["mae_mw"] == pytest.approx(100)  # (100+0+100+200)/4
    assert s["rmse_mw"] == pytest.approx(math.sqrt(15000))  # (1e4+0+1e4+4e4)/4
    assert s["bias_mw"] == pytest.approx(50)
    assert s["nmae_pct_of_mean_actual"] == pytest.approx(8)  # 400 / 5000
    assert s["nmae_pct_of_max_actual"] == pytest.approx(5)  # 100 / 2000
    # Linear-interpolated quantiles of [-100, 0, 100, 200]
    assert s["p10_error_mw"] == pytest.approx(-70)
    assert s["p50_error_mw"] == pytest.approx(50)
    assert s["p90_error_mw"] == pytest.approx(170)


def test_recommendation_buffer_is_error_quantile() -> None:
    r = metrics.recommendation(SAMPLE, 0.9)
    assert r["buffer_mw"] == pytest.approx(170)
    assert r["shortfall_hours_pct"] == pytest.approx(50)
    assert r["riskiest_hours"][0] == 3  # the +200 MW hour
    assert r["headline"].startswith("In 90% of hours, actual wind was no more than 170 MW below")
    assert "9 hours in 10" in r["headline"] and "too high" in r["headline"]


@pytest.mark.parametrize(("confidence", "odds"), [(0.8, "8 hours in 10"), (0.95, "19 hours in 20")])
def test_recommendation_headline_odds(confidence: float, odds: str) -> None:
    assert odds in metrics.recommendation(SAMPLE, confidence)["headline"]


def test_recommendation_no_buffer_when_forecast_always_low() -> None:
    r = metrics.recommendation(aligned([-300, -200, -100], [1000, 1000, 1000]), 0.9)
    assert r["buffer_mw"] == 0
    assert "too low" in r["headline"]


def test_histogram_bins_aligned_to_width() -> None:
    bins = metrics.histogram(SAMPLE["error_mw"])
    assert bins[0]["bin_start_mw"] == -100
    assert all(b["bin_end_mw"] - b["bin_start_mw"] == 50 for b in bins)
    assert sum(b["count"] for b in bins) == 4
    assert [b["count"] for b in bins] == [1, 0, 1, 0, 1, 0, 1]


def test_by_hour_groups_by_local_hour() -> None:
    df = aligned([100, 300, -50], [1000, 1000, 1000], hours=[6, 6, 7])
    rows = {r["hour"]: r for r in metrics.by_hour(df, 0.9)}
    assert rows[6]["n"] == 2 and rows[6]["mae_mw"] == pytest.approx(200)
    assert rows[6]["bias_mw"] == pytest.approx(200)
    assert rows[7]["buffer_mw"] == 0  # only an over-delivery in that hour


def test_by_day() -> None:
    rows = metrics.by_day(SAMPLE)
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-01-10"
    assert rows[0]["mean_actual_mw"] == pytest.approx(1250)


def test_horizon_curve_buckets() -> None:
    pairs = SAMPLE.assign(horizon_h=[1.5, 2.5, 4.5, 5.5])
    rows = metrics.horizon_curve(pairs, bucket_hours=3)
    assert [(r["horizon_start_h"], r["n"]) for r in rows] == [(0, 2), (3, 2)]
    assert rows[0]["mae_mw"] == pytest.approx(50)
    assert rows[1]["mae_mw"] == pytest.approx(150)
