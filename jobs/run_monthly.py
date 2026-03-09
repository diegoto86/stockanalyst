"""
run_monthly.py
--------------
Monthly pipeline — runs once per month.

Tasks:
    1. Full universe cleanup (remove illiquid / delisted tickers)
    2. Review filter parameters
    3. Recalculate aggregated tables
    4. Consolidate master watchlist
"""


def run():
    print("[monthly] Starting monthly pipeline...")

    # 1. Universe cleanup
    print("[monthly] Cleaning universe...")

    # 2. Review filter parameters
    print("[monthly] Reviewing filter parameters...")

    # 3. Aggregated tables
    print("[monthly] Recalculating aggregated tables...")

    # 4. Master watchlist
    print("[monthly] Consolidating master watchlist...")

    print("[monthly] Pipeline complete.")


if __name__ == "__main__":
    run()
