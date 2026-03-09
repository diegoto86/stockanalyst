"""
run_quarterly.py
----------------
Quarterly pipeline — runs when new earnings are detected or once per quarter.

Tasks:
    1. Refresh full fundamental data
    2. Recalculate quality score
    3. Recalculate valuation score
    4. Regenerate the medium-term eligible universe
"""

from config import UNIVERSE_TICKERS
from providers import yahoo_fundamentals
from storage import fundamentals_repository


def run():
    print("[quarterly] Starting quarterly pipeline...")

    # 1. Fundamentals
    print("[quarterly] Refreshing fundamentals...")
    # fundamentals_df = yahoo_fundamentals.fetch_fundamentals(UNIVERSE_TICKERS)
    # fundamentals_repository.save_fundamentals(fundamentals_df)

    # 2. Quality score
    print("[quarterly] Recalculating quality score...")

    # 3. Valuation score
    print("[quarterly] Recalculating valuation score...")

    # 4. Eligible universe
    print("[quarterly] Regenerating eligible universe...")

    print("[quarterly] Pipeline complete.")


if __name__ == "__main__":
    run()
