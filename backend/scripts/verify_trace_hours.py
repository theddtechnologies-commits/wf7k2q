"""Independent trace of random hours, straight from Elexon (stdlib only, no app code).

For each hour it prints the two FUELHH half-hours, their mean, every WINDFOR forecast
for that hour with its publishTime, and the one a 09:50 UK D-1 cutoff selects.
With --api, the same hours are fetched from a running app and compared.

Usage (from backend/):
    python scripts/verify_trace_hours.py --seed 4152 [--api http://localhost:8000]
"""

import argparse
import json
import random
import urllib.request
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
UK, UTC = ZoneInfo("Europe/London"), timezone.utc


def get(url: str):
    return json.load(urllib.request.urlopen(url, timeout=60))


def iso(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt(d: datetime) -> str:
    return d.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=random.randrange(10**6))
    parser.add_argument("--hours", type=int, default=3)
    parser.add_argument("--api", help="Base URL of a running app to compare against")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    first = datetime(2026, 1, 2, tzinfo=UTC)
    targets = sorted(first + timedelta(hours=h) for h in rng.sample(range(31 * 24), args.hours))
    print(f"seed={args.seed}")
    mismatches = 0

    for t in targets:
        uk_day = t.astimezone(UK).date()
        # 09:50 UK local time on the day before the UK delivery day.
        cutoff = datetime.combine(uk_day - timedelta(days=1), time(9, 50), tzinfo=UK).astimezone(UTC)

        fuel = get(f"{BASE}/FUELHH/stream?settlementDateFrom={uk_day}&settlementDateTo={uk_day}&fuelType=WIND")
        halves = {r["startTime"]: r["generation"] for r in fuel}
        a1, a2 = halves[fmt(t)], halves[fmt(t + timedelta(minutes=30))]
        actual = (a1 + a2) / 2

        window = f"publishDateTimeFrom={fmt(t - timedelta(days=4))}&publishDateTimeTo={fmt(t + timedelta(hours=1))}"
        forecasts = sorted((r for r in get(f"{BASE}/WINDFOR/stream?{window}") if r["startTime"] == fmt(t)),
                           key=lambda r: r["publishTime"])
        eligible = [r for r in forecasts if iso(r["publishTime"]) <= cutoff and iso(r["publishTime"]) <= t]
        chosen = eligible[-1]

        print(f"\n=== Target {fmt(t)}  (UK {t.astimezone(UK):%Y-%m-%d %H:%M %Z}, delivery day {uk_day})")
        print(f"Cutoff {cutoff.astimezone(UK):%Y-%m-%d %H:%M %Z} = {fmt(cutoff)}")
        print(f"FUELHH {fmt(t)[11:16]} = {a1} MW, {fmt(t + timedelta(minutes=30))[11:16]} = {a2} MW -> mean {actual} MW")
        for r in forecasts:
            lead = (t - iso(r["publishTime"])).total_seconds() / 3600
            tag = "  <== SELECTED" if r is chosen else ("  (after cutoff)" if iso(r["publishTime"]) > cutoff else "")
            print(f"  publish {r['publishTime']}  {lead:6.1f} h ahead  {r['generation']:>6} MW{tag}")

        if args.api:
            points = get(f"{args.api}/api/timeseries?start={uk_day}&end={uk_day}")["points"]
            app = next(p for p in points if iso(p["start_time"]) == t)
            same = (app["actual_mw"] == actual and app["forecast_mw"] == chosen["generation"]
                    and iso(app["publish_time"]) == iso(chosen["publishTime"]))
            mismatches += not same
            print(f"App: actual {app['actual_mw']}, forecast {app['forecast_mw']}, published {app['publish_time']} "
                  f"-> {'MATCH' if same else 'MISMATCH'}")

    if args.api:
        print(f"\n{len(targets) - mismatches}/{len(targets)} hours match the app")


if __name__ == "__main__":
    main()
