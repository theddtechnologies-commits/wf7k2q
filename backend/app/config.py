"""Central configuration: study window, Elexon endpoints and decision-cutoff defaults."""

import os
from datetime import date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

UK_TZ = ZoneInfo("Europe/London")

ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1/datasets"

# Purchase decisions are made on day D-1 for delivery on day D.
# Decisions made 1–31 Jan 2026 therefore cover delivery days 2 Jan – 1 Feb 2026.
DECISION_START = date(2026, 1, 1)
DECISION_END = date(2026, 1, 31)
DELIVERY_START = DECISION_START + timedelta(days=1)
DELIVERY_END = DECISION_END + timedelta(days=1)

# Forecasts are fetched from a few days before the first delivery day so that
# horizon analysis has the longest-range forecasts (WINDFOR reaches ~66 h ahead).
FORECAST_LOOKBACK_DAYS = 4

# Default decision cutoff: gate closure of Nord Pool's GB day-ahead (N2EX) auction,
# 09:50 UK time on the day before delivery. EPEX SPOT's GB auction closes at 09:20.
DEFAULT_CUTOFF_TIME = time(9, 50)
DEFAULT_CUTOFF_DAYS_BEFORE = 1
DEFAULT_CONFIDENCE = 0.90

DATA_DIR = Path(os.environ.get("WIND_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
