"""Re-download the January 2026 Elexon data into backend/data/.

Usage (from backend/):  python -m scripts.refresh_data
"""

from app import elexon


def main() -> None:
    actuals = elexon.load_actuals(refresh=True)
    forecasts = elexon.load_forecasts(refresh=True)
    print(
        f"Actuals:   {len(actuals):>6} rows  "
        f"{actuals.start_time.min()} → {actuals.start_time.max()}"
    )
    print(
        f"Forecasts: {len(forecasts):>6} rows  "
        f"{forecasts.publish_time.nunique()} publishes  "
        f"{forecasts.publish_time.min()} → {forecasts.publish_time.max()}"
    )


if __name__ == "__main__":
    main()
