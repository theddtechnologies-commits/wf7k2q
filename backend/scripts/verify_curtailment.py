"""Offline check: how much of the forecast bias is explained by wind curtailment?

NOT part of the app. The dashboard deliberately uses only FUELHH and WINDFOR (the
brief's scope). This script additionally reads Physical Notifications (PN) and
Bid-Offer Acceptances (BOALF) to explain the bias the app reports.

Method, per half-hour and per wind BM unit (minute resolution):
  planned    = PN level (what the unit expected to generate)
  instructed = level from the latest accepted bid/offer covering that minute, else PN
Summed over wind units, planned - instructed is the output cut by the system operator.
Compared with FUELHH (metered) and the decision-time WINDFOR forecast (09:50 UK, D-1).

Usage (from backend/):
    python scripts/verify_curtailment.py                       # 60 random half-hours, seed 7
    python scripts/verify_curtailment.py --sample 120 --seed 1
    python scripts/verify_curtailment.py --periods 2026-01-12T01:00:00Z 2026-01-28T15:00:00Z
"""

import argparse
import json
import random
import statistics
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

API = "https://data.elexon.co.uk/bmrs/api/v1"
UTC = timezone.utc


def get(path: str):
    return json.load(urllib.request.urlopen(f"{API}/{path}", timeout=120))


def ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def level_at(segments, t: datetime):
    """Linear interpolation over (timeFrom, timeTo, levelFrom, levelTo) segments."""
    for a, b, la, lb in segments:
        if a <= t <= b:
            return la if b == a else la + (lb - la) * (t - a) / (b - a)
    return None


def planned_vs_instructed(start: datetime, wind_units: set[str]) -> tuple[float, float]:
    """Average MW over the half-hour: (sum of wind PN, sum of instructed wind level)."""
    sp = start.hour * 2 + start.minute // 30 + 1  # January: settlement day == UTC day
    day = start.date()
    pn: dict[str, list] = {}
    boa: dict[str, list] = {}
    for r in get(f"datasets/PN?settlementDate={day}&settlementPeriod={sp}")["data"]:
        if r["nationalGridBmUnit"] in wind_units:
            pn.setdefault(r["nationalGridBmUnit"], []).append(
                (ts(r["timeFrom"]), ts(r["timeTo"]), r["levelFrom"], r["levelTo"]))
    # Acceptances issued up to 3 h earlier can still cover this period.
    for r in get(f"datasets/BOALF?from={day}&to={day}&settlementPeriodFrom={max(1, sp - 6)}&settlementPeriodTo={sp}")["data"]:
        if r["nationalGridBmUnit"] in wind_units:
            boa.setdefault(r["nationalGridBmUnit"], []).append(
                (r["acceptanceNumber"], ts(r["timeFrom"]), ts(r["timeTo"]), r["levelFrom"], r["levelTo"]))

    minutes = [start + timedelta(minutes=m + 0.5) for m in range(30)]
    planned = instructed = 0.0
    for unit, segments in pn.items():
        acceptances = sorted(boa.get(unit, []), reverse=True)  # latest acceptance first
        for t in minutes:
            p = level_at(segments, t) or 0.0
            i = next((level_at([(a, b, la, lb)], t) for _, a, b, la, lb in acceptances if a <= t <= b), None)
            planned += p / 30
            instructed += (p if i is None else i) / 30
    return planned, instructed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample", type=int, default=60, help="Random half-hours (hh:00) to check")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--periods", nargs="*", help="Explicit half-hour starts (UTC, ISO 8601)")
    args = parser.parse_args()

    if args.periods:
        starts = [ts(p) for p in args.periods]
    else:
        first = datetime(2026, 1, 2, tzinfo=UTC)
        starts = [first + timedelta(hours=h) for h in sorted(random.Random(args.seed).sample(range(744), args.sample))]

    wind_units = {u["nationalGridBmUnit"] for u in get("reference/bmunits/all") if u.get("fuelType") == "WIND"}
    fuel = {ts(r["startTime"]): r["generation"]
            for r in get("datasets/FUELHH/stream?settlementDateFrom=2026-01-02&settlementDateTo=2026-02-01&fuelType=WIND")}
    forecast = {}  # decision-time forecast: latest publish <= 09:50 on D-1 (January: UK time == UTC)
    for r in get("datasets/WINDFOR/stream?publishDateTimeFrom=2025-12-29T00:00:00Z&publishDateTimeTo=2026-02-02T00:00:00Z"):
        t, p = ts(r["startTime"]), ts(r["publishTime"])
        if p <= datetime(t.year, t.month, t.day, 9, 50, tzinfo=UTC) - timedelta(days=1) and (t not in forecast or p > forecast[t][0]):
            forecast[t] = (p, r["generation"])

    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda s: planned_vs_instructed(s, wind_units), starts))

    rows = []
    for start, (planned, instructed) in zip(starts, results):
        fc = forecast[start.replace(minute=0)][1]
        rows.append({"start": start, "fc": fc, "fuelhh": fuel[start], "pn": planned, "cut": planned - instructed,
                     "residual": instructed - fuel[start]})
        if args.periods:
            print(f"{start:%Y-%m-%d %H:%M}Z  forecast {fc:>6}  PN {planned:8.0f}  instructed {instructed:8.0f}  "
                  f"FUELHH {fuel[start]:>6}  cut by bids {planned - instructed:6.0f} MW")

    mean = lambda key: statistics.fmean(r[key] for r in rows)
    err = [r["fc"] - r["fuelhh"] for r in rows]
    adjusted = [e - r["cut"] for e, r in zip(err, rows)]
    print(f"\n{len(rows)} half-hours, January 2026 (decision-time forecast, 09:50 UK D-1)")
    print(f"  Forecast - FUELHH (bias reported by the app)  {statistics.fmean(err):7.0f} MW")
    print(f"  Wind output cut by accepted bids              {mean('cut'):7.0f} MW  "
          f"(> 500 MW in {sum(r['cut'] > 500 for r in rows) / len(rows):.0%} of half-hours, max {max(r['cut'] for r in rows):.0f})")
    print(f"  Instructed level - FUELHH (unexplained)       {mean('residual'):7.0f} MW")
    print(f"  Bias after adding curtailment back            {statistics.fmean(adjusted):7.0f} MW")
    print(f"  Share of bias explained by curtailment        {mean('cut') / statistics.fmean(err):7.0%}")
    print(f"  MAE before -> after adding curtailment back   {statistics.fmean(map(abs, err)):7.0f} -> "
          f"{statistics.fmean(map(abs, adjusted)):.0f} MW")


if __name__ == "__main__":
    main()
