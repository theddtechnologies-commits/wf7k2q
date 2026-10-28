from datetime import date, time

import pandas as pd
import pytest

from app import processing


def ts(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def forecasts(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "publish_time": [ts(p) for p, _, _ in rows],
            "start_time": [ts(s) for _, s, _ in rows],
            "forecast_mw": [f for _, _, f in rows],
        }
    )


class TestDecisionCutoff:
    @pytest.mark.parametrize(
        ("target", "expected"),
        [
            # Winter (GMT = UTC): every hour of 10 Jan uses 09:50 on 9 Jan.
            ("2026-01-10 00:00", "2026-01-09 09:50"),
            ("2026-01-10 23:00", "2026-01-09 09:50"),
            # Summer (BST = UTC+1): 09:50 local is 08:50 UTC.
            ("2026-06-10 12:00", "2026-06-09 08:50"),
            # 23:30 UTC on 10 Jun is 00:30 BST on 11 Jun → delivery day is 11 Jun.
            ("2026-06-10 23:30", "2026-06-10 08:50"),
        ],
    )
    def test_day_ahead_cutoff(self, target: str, expected: str) -> None:
        result = processing.decision_cutoff(pd.Series([ts(target)]), time(9, 50), 1)
        assert result.iloc[0] == ts(expected)

    def test_days_before_is_configurable(self) -> None:
        result = processing.decision_cutoff(pd.Series([ts("2026-01-10 12:00")]), time(9, 20), 2)
        assert result.iloc[0] == ts("2026-01-08 09:20")


class TestSelectLatestForecasts:
    def test_picks_latest_at_or_before_cutoff(self) -> None:
        f = forecasts(
            [
                ("2026-01-09 07:30", "2026-01-10 12:00", 100),
                ("2026-01-09 09:30", "2026-01-10 12:00", 200),
                ("2026-01-09 09:50", "2026-01-10 12:00", 300),  # exactly at cutoff → allowed
                ("2026-01-09 11:30", "2026-01-10 12:00", 400),  # after cutoff → excluded
            ]
        )
        result = processing.select_latest_forecasts(f, time(9, 50), 1)
        assert len(result) == 1
        row = result.iloc[0]
        assert row.forecast_mw == 300
        assert row.publish_time == ts("2026-01-09 09:50")
        assert row.horizon_h == pytest.approx(26 + 10 / 60)

    def test_each_target_selected_independently(self) -> None:
        f = forecasts(
            [
                ("2026-01-09 07:30", "2026-01-10 00:00", 10),
                ("2026-01-09 09:30", "2026-01-10 00:00", 20),
                ("2026-01-09 09:30", "2026-01-11 00:00", 30),  # eligible but older
                ("2026-01-10 09:30", "2026-01-11 00:00", 40),  # latest before 10 Jan 09:50
            ]
        )
        result = processing.select_latest_forecasts(f, time(9, 50), 1)
        assert result.forecast_mw.tolist() == [20, 40]

    def test_target_without_eligible_forecast_is_dropped(self) -> None:
        f = forecasts([("2026-01-09 11:30", "2026-01-10 12:00", 400)])
        assert processing.select_latest_forecasts(f, time(9, 50), 1).empty

    def test_never_uses_forecast_published_after_target(self) -> None:
        # Same-day cutoff at 23:00: the 13:00 forecast is before the cutoff but after
        # the 12:00 target, so only the 11:00 one is a genuine forecast.
        f = forecasts(
            [
                ("2026-01-10 11:00", "2026-01-10 12:00", 1),
                ("2026-01-10 13:00", "2026-01-10 12:00", 2),
            ]
        )
        result = processing.select_latest_forecasts(f, time(23, 0), 0)
        assert result.forecast_mw.tolist() == [1]


def test_to_hourly_averages_and_drops_incomplete_hours() -> None:
    actuals = pd.DataFrame(
        {
            "start_time": [ts("2026-01-10 10:00"), ts("2026-01-10 10:30"), ts("2026-01-10 11:00")],
            "actual_mw": [100.0, 200.0, 300.0],
        }
    )
    hourly = processing.to_hourly(actuals)
    assert hourly.start_time.tolist() == [ts("2026-01-10 10:00")]
    assert hourly.actual_mw.tolist() == [150.0]


def test_align_error_sign_is_forecast_minus_actual() -> None:
    actual = pd.DataFrame({"start_time": [ts("2026-01-10 10:00")], "actual_mw": [800.0]})
    f = pd.DataFrame({"start_time": [ts("2026-01-10 10:00")], "forecast_mw": [1000.0]})
    assert processing.align(actual, f).error_mw.tolist() == [200.0]


def test_filter_delivery_range_is_inclusive() -> None:
    df = pd.DataFrame(
        {"start_time": [ts("2026-01-01 23:00"), ts("2026-01-02 00:00"), ts("2026-01-03 23:00"),
                        ts("2026-01-04 00:00")]}
    )
    result = processing.filter_delivery_range(df, date(2026, 1, 2), date(2026, 1, 3))
    assert result.start_time.tolist() == [ts("2026-01-02 00:00"), ts("2026-01-03 23:00")]


def test_horizon_pairs_drop_negative_horizons() -> None:
    actual = pd.DataFrame({"start_time": [ts("2026-01-10 10:00")], "actual_mw": [500.0]})
    f = forecasts(
        [
            ("2026-01-10 04:30", "2026-01-10 10:00", 600),  # 5.5 h ahead
            ("2026-01-10 11:30", "2026-01-10 10:00", 510),  # published afterwards
        ]
    )
    pairs = processing.horizon_pairs(f, actual)
    assert pairs.horizon_h.tolist() == [5.5]
    assert pairs.error_mw.tolist() == [100.0]
