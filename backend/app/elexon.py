"""Elexon BMRS client with an on-disk CSV cache.

Each dataset is fetched once for the study window and stored as a gzipped CSV in
DATA_DIR. Subsequent loads read the file, so the public API is not hit repeatedly
(and the deployed app never depends on Elexon being reachable).
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def fetch_dataset(dataset: str, params: dict[str, str]) -> list[dict[str, Any]]:
    """Call the BMRS `/datasets/{dataset}/stream` endpoint and return its JSON rows."""
    url = f"{config.ELEXON_BASE_URL}/{dataset}/stream"
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = httpx.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            if attempt == _MAX_RETRIES:
                raise
            logger.warning("Elexon %s attempt %d failed (%s), retrying", dataset, attempt, exc)
            time.sleep(2**attempt)
    raise RuntimeError("unreachable")


def _cached(path: Path, fetch: Any, refresh: bool, parse_dates: list[str]) -> pd.DataFrame:
    """Return the cached frame at `path`, fetching and writing it first if needed."""
    if path.exists() and not refresh:
        return pd.read_csv(path, parse_dates=parse_dates)
    df: pd.DataFrame = fetch()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    except OSError as exc:  # e.g. read-only filesystem on serverless hosts
        logger.warning("Could not write cache %s: %s", path, exc)
    return df


def load_actuals(refresh: bool = False) -> pd.DataFrame:
    """Half-hourly national wind outturn (FUELHH, fuelType=WIND).

    Columns: start_time (UTC), actual_mw.
    """
    start, end = config.DELIVERY_START, config.DELIVERY_END
    path = config.DATA_DIR / f"fuelhh_wind_{start}_{end}.csv.gz"

    def fetch() -> pd.DataFrame:
        rows = fetch_dataset(
            "FUELHH",
            {"settlementDateFrom": str(start), "settlementDateTo": str(end), "fuelType": "WIND"},
        )
        df = pd.DataFrame(rows)
        df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
        df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
        # Keep the most recently published value if a period was revised.
        df = df.sort_values("publish_time").drop_duplicates("start_time", keep="last")
        df = df.rename(columns={"generation": "actual_mw"})
        return df[["start_time", "actual_mw"]].sort_values("start_time").reset_index(drop=True)

    return _cached(path, fetch, refresh, parse_dates=["start_time"])


def load_forecasts(refresh: bool = False) -> pd.DataFrame:
    """Every hourly national wind forecast (WINDFOR) published around the study window.

    Columns: publish_time (UTC), start_time (UTC), forecast_mw.
    """
    pub_from = datetime.combine(
        config.DELIVERY_START - timedelta(days=config.FORECAST_LOOKBACK_DAYS),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    pub_to = datetime.combine(
        config.DELIVERY_END + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
    )
    path = config.DATA_DIR / f"windfor_{pub_from.date()}_{pub_to.date()}.csv.gz"

    def fetch() -> pd.DataFrame:
        rows = fetch_dataset(
            "WINDFOR",
            {
                "publishDateTimeFrom": pub_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "publishDateTimeTo": pub_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
        df = pd.DataFrame(rows)
        df["publish_time"] = pd.to_datetime(df["publishTime"], utc=True)
        df["start_time"] = pd.to_datetime(df["startTime"], utc=True)
        df = df.rename(columns={"generation": "forecast_mw"})
        df = df.drop_duplicates(["publish_time", "start_time"], keep="last")
        cols = ["publish_time", "start_time", "forecast_mw"]
        return df[cols].sort_values(["publish_time", "start_time"]).reset_index(drop=True)

    return _cached(path, fetch, refresh, parse_dates=["publish_time", "start_time"])
