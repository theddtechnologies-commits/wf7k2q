"""Integration tests: the API served from the committed January 2026 data snapshot."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta_defaults() -> None:
    body = client.get("/api/meta").json()
    assert body["delivery_start"] == "2026-01-02"
    assert body["delivery_end"] == "2026-02-01"
    assert body["default_cutoff_time"] == "09:50"


def test_timeseries_uses_forecasts_published_before_cutoff() -> None:
    body = client.get("/api/timeseries", params={"start": "2026-01-10", "end": "2026-01-10"}).json()
    points = body["points"]
    assert len(points) == 24
    for p in points:
        # Default cutoff is 09:50 on 9 Jan (GMT = UTC in January).
        assert p["publish_time"] <= "2026-01-09T09:50:00Z"
        assert p["error_mw"] == pytest.approx(p["forecast_mw"] - p["actual_mw"])


def test_metrics_shape_and_cache_header() -> None:
    response = client.get("/api/metrics", params={"confidence": 0.8})
    assert response.status_code == 200
    assert "s-maxage" in response.headers["cache-control"]
    body = response.json()
    assert body["summary"]["n"] == 744  # 31 days x 24 hours
    assert body["summary"]["coverage_pct"] == pytest.approx(100)
    assert len(body["by_hour"]) == 24
    assert body["recommendation"]["confidence"] == 0.8


def test_horizon_mae_grows_with_lead_time() -> None:
    buckets = client.get("/api/horizon", params={"bucket_hours": 6}).json()["buckets"]
    assert buckets[0]["horizon_start_h"] == 0
    assert buckets[0]["mae_mw"] < buckets[6]["mae_mw"]


@pytest.mark.parametrize(
    "params",
    [
        {"start": "2026-01-10", "end": "2026-01-05"},  # reversed range
        {"start": "2025-12-01"},  # outside data window
        {"cutoff_time": "25:00"},
        {"cutoff_days_before": 5},
    ],
)
def test_invalid_params_rejected(params: dict[str, str]) -> None:
    assert client.get("/api/metrics", params=params).status_code == 422


def test_missing_forecasts_are_null_and_excluded_from_metrics() -> None:
    # At a D-2 cutoff the forecast doesn't reach the last hours of the delivery day.
    params = {"start": "2026-01-10", "end": "2026-01-10", "cutoff_days_before": 2}
    points = client.get("/api/timeseries", params=params).json()["points"]
    missing = [p for p in points if p["forecast_mw"] is None]
    assert missing, "expected uncovered hours at a D-2 cutoff"
    for p in missing:
        assert p["error_mw"] is None and p["publish_time"] is None  # null, never 0
        assert p["actual_mw"] > 0
    summary = client.get("/api/metrics", params=params).json()["summary"]
    assert summary["n"] == len(points) - len(missing)
    assert summary["coverage_pct"] == pytest.approx(summary["n"] / len(points) * 100)
