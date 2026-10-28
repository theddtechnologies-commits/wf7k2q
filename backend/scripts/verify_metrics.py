"""Recompute the headline metrics from a fresh Elexon download (stdlib only, no app code).

Usage (from backend/):  python scripts/verify_metrics.py [http://localhost:8000]
With an app URL, prints the app's /api/metrics summary underneath for comparison.
"""
import json, math, sys, urllib.request
from datetime import datetime, timedelta, timezone

B, UTC = "https://data.elexon.co.uk/bmrs/api/v1/datasets", timezone.utc
get = lambda url: json.load(urllib.request.urlopen(url, timeout=120))
ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
fuel = {ts(r["startTime"]): r["generation"] for r in get(f"{B}/FUELHH/stream?settlementDateFrom=2026-01-02&settlementDateTo=2026-02-01&fuelType=WIND")}
best = {}  # target -> (publish, MW): latest publish <= 09:50 on the previous day (January: UK time == UTC)
for r in get(f"{B}/WINDFOR/stream?publishDateTimeFrom=2025-12-29T00:00:00Z&publishDateTimeTo=2026-02-02T00:00:00Z"):
    t, p = ts(r["startTime"]), ts(r["publishTime"])
    if p <= datetime(t.year, t.month, t.day, 9, 50, tzinfo=UTC) - timedelta(days=1) and (t not in best or p > best[t][0]):
        best[t] = (p, r["generation"])
err = sorted(best[t][1] - (fuel[t] + fuel[t + timedelta(minutes=30)]) / 2
             for t in best if t in fuel and t + timedelta(minutes=30) in fuel)
q = lambda p: err[int(k := p * (len(err) - 1))] + (k % 1) * (err[min(int(k) + 1, len(err) - 1)] - err[int(k)])
print(f"independent  n={len(err)}  MAE={sum(map(abs, err)) / len(err):.1f}  RMSE={math.sqrt(sum(e * e for e in err) / len(err)):.1f}  "
      f"bias={sum(err) / len(err):.1f}  P10={q(0.1):.1f}  P50={q(0.5):.1f}  P90={q(0.9):.1f}")
if len(sys.argv) > 1:
    s = get(f"{sys.argv[1]}/api/metrics")["summary"]
    print(f"app          n={s['n']}  MAE={s['mae_mw']:.1f}  RMSE={s['rmse_mw']:.1f}  bias={s['bias_mw']:.1f}  "
          f"P10={s['p10_error_mw']:.1f}  P50={s['p50_error_mw']:.1f}  P90={s['p90_error_mw']:.1f}")
