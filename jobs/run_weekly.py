"""
run_weekly.py
-------------
Weekly pipeline — runs once per week (Monday recommended).

Tasks:
    1. Recalculate average liquidity and volume
    2. Refresh sector / industry mapping if needed
    3. Recompose the watchlist base with combined score
    4. Light universe cleanup
"""

from config import UNIVERSE_TICKERS


def run():
    print("[weekly] Starting weekly pipeline...")

    # 1. Liquidity & volume averages
    print("[weekly] Recalculating liquidity metrics...")
    # liquidity_df = compute_liquidity(UNIVERSE_TICKERS)

    # 2. Sector / industry mapping
    print("[weekly] Refreshing sector mapping...")
    # sector_df = fetch_sector_mapping(UNIVERSE_TICKERS)

    # 3. Watchlist base
    print("[weekly] Recomposing watchlist base...")
    # watchlist = build_watchlist(liquidity_df, sector_df, ...)
    # watchlist_repository.save_watchlist(watchlist)

    # 4. Light universe cleanup
    print("[weekly] Light universe cleanup...")

    print("[weekly] Pipeline complete.")


if __name__ == "__main__":
    run()
