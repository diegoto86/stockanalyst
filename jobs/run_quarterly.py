"""
run_quarterly.py
----------------
Quarterly pipeline — runs when new earnings are detected or once per quarter.

Tasks:
    1. Init DB
    2. Refresh full fundamental data from Yahoo Finance
    3. Save to fundamentals_snapshot_quarterly
"""

from datetime import date
from storage.db import init_db
from providers import yahoo_fundamentals
from storage import fundamentals_repository
from config import UNIVERSE_TICKERS


def run():
    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"[quarterly] Starting quarterly pipeline — {today}")
    print(f"{'='*60}")

    init_db()

    print(f"[quarterly] Fetching fundamentals for {len(UNIVERSE_TICKERS)} tickers...")
    print("[quarterly] This may take a few minutes...")

    fundamentals_df = yahoo_fundamentals.fetch_fundamentals(UNIVERSE_TICKERS)

    if not fundamentals_df.empty:
        fundamentals_repository.save_fundamentals(fundamentals_df)
        print(f"[quarterly] Saved fundamentals for {len(fundamentals_df)} tickers.")

        # Print summary
        if "fundamental_score" in fundamentals_df.columns:
            top = fundamentals_df.nlargest(5, "fundamental_score")[["ticker", "fundamental_score"]]
            print("\n[quarterly] Top 5 by fundamental score:")
            for _, row in top.iterrows():
                print(f"  {row['ticker']:<8} score={row['fundamental_score']:.3f}")
    else:
        print("[quarterly] WARNING: No fundamental data received.")

    print(f"[quarterly] Pipeline complete — {today}\n")


if __name__ == "__main__":
    run()
