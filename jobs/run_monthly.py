"""
run_monthly.py
--------------
Monthly maintenance pipeline.

Tasks:
    1. Clean the tracked universe using the latest local metadata
    2. Exclude stale or likely delisted tickers
    3. Recalculate monthly aggregate review tables
    4. Consolidate a master watchlist snapshot
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pandas as pd

from config import DATA_DIR, MIN_AVG_DAILY_VOLUME, MIN_MARKET_CAP
from storage import fundamentals_repository, watchlist_repository
from storage.db import get_connection, init_db

UNIVERSE_PATH = Path(DATA_DIR) / "universe_tickers.csv"
HISTORY_DIR = Path(DATA_DIR) / "history"
MONTHLY_DIR = Path(DATA_DIR) / "monthly"
MASTER_WATCHLIST_PATH = Path(DATA_DIR) / "master_watchlist.csv"
PRICE_STALE_DAYS = 15


def _load_universe() -> pd.DataFrame:
    if not UNIVERSE_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(UNIVERSE_PATH)
    df.columns = [str(col).strip().lower() for col in df.columns]
    if "ticker" not in df.columns:
        return pd.DataFrame()

    df["ticker"] = df["ticker"].astype(str).str.strip().str.upper()
    return df.drop_duplicates(subset=["ticker"]).reset_index(drop=True)


def _latest_price_dates() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT ticker, MAX(date) AS latest_price_date
        FROM price_bars_daily
        GROUP BY ticker
        """,
        conn,
    )
    conn.close()
    return df


def _load_current_watchlist() -> pd.DataFrame:
    try:
        return watchlist_repository.load_watchlist()
    except Exception:
        return pd.DataFrame()


def _is_valid_ticker(ticker: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{1,5}", ticker or ""))


def _build_review(universe_df: pd.DataFrame) -> pd.DataFrame:
    review_df = universe_df.copy()
    today = pd.Timestamp(date.today())

    latest_price_df = _latest_price_dates()
    if latest_price_df.empty:
        review_df["latest_price_date"] = pd.NaT
    else:
        review_df = review_df.merge(latest_price_df, on="ticker", how="left")

    review_df["latest_price_date"] = pd.to_datetime(
        review_df["latest_price_date"], errors="coerce"
    )
    review_df["days_since_price"] = (today - review_df["latest_price_date"]).dt.days
    review_df["market_cap"] = pd.to_numeric(review_df.get("market_cap"), errors="coerce")
    review_df["avg_volume"] = pd.to_numeric(review_df.get("avg_volume"), errors="coerce")

    fundamentals_df = fundamentals_repository.load_fundamentals(
        tickers=review_df["ticker"].tolist()
    )
    if fundamentals_df.empty:
        review_df["fundamentals_as_of"] = pd.NA
        review_df["fundamental_score"] = pd.NA
    else:
        review_df = review_df.merge(
            fundamentals_df[["ticker", "as_of_date", "fundamental_score"]].rename(
                columns={"as_of_date": "fundamentals_as_of"}
            ),
            on="ticker",
            how="left",
        )

    review_df["ticker_valid"] = review_df["ticker"].apply(_is_valid_ticker)
    review_df["market_cap_ok"] = review_df["market_cap"].fillna(0) >= MIN_MARKET_CAP
    review_df["avg_volume_ok"] = review_df["avg_volume"].fillna(0) >= MIN_AVG_DAILY_VOLUME
    review_df["price_recent"] = review_df["days_since_price"].fillna(9999) <= PRICE_STALE_DAYS
    review_df["has_fundamentals"] = review_df["fundamental_score"].notna()

    def _status(row: pd.Series) -> str:
        reasons = []
        if not row["ticker_valid"]:
            reasons.append("invalid_ticker")
        if not row["market_cap_ok"]:
            reasons.append("below_market_cap")
        if not row["avg_volume_ok"]:
            reasons.append("below_volume")
        if not row["price_recent"]:
            reasons.append("stale_or_missing_prices")
        if not row["has_fundamentals"]:
            reasons.append("missing_fundamentals")
        return "ok" if not reasons else ",".join(reasons)

    review_df["status"] = review_df.apply(_status, axis=1)
    review_df["keep"] = (
        review_df["ticker_valid"]
        & review_df["market_cap_ok"]
        & review_df["avg_volume_ok"]
        & review_df["price_recent"]
    )

    return review_df.sort_values(
        ["keep", "market_cap"], ascending=[False, False]
    ).reset_index(drop=True)


def _save_universe_outputs(review_df: pd.DataFrame) -> pd.DataFrame:
    cleaned_df = review_df[review_df["keep"]].copy()
    if cleaned_df.empty:
        return cleaned_df

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    backup_path = HISTORY_DIR / f"universe_tickers_{today}.csv"
    review_path = MONTHLY_DIR / f"universe_review_{today}.csv"
    summary_path = MONTHLY_DIR / f"universe_summary_{today}.csv"

    if UNIVERSE_PATH.exists() and not backup_path.exists():
        pd.read_csv(UNIVERSE_PATH).to_csv(backup_path, index=False)

    keep_cols = [
        col
        for col in ["ticker", "name", "sector", "market_cap", "avg_volume", "exchange"]
        if col in cleaned_df.columns
    ]
    cleaned_df[keep_cols].to_csv(UNIVERSE_PATH, index=False)
    review_df.to_csv(review_path, index=False)

    pd.DataFrame(
        [
            {"metric": "total_before", "value": int(len(review_df))},
            {"metric": "total_after", "value": int(len(cleaned_df))},
            {"metric": "removed_count", "value": int((~review_df["keep"]).sum())},
            {
                "metric": "stale_or_missing_prices",
                "value": int((~review_df["price_recent"]).sum()),
            },
            {
                "metric": "missing_fundamentals",
                "value": int((~review_df["has_fundamentals"]).sum()),
            },
        ]
    ).to_csv(summary_path, index=False)

    return cleaned_df


def _save_master_watchlist(universe_df: pd.DataFrame) -> pd.DataFrame:
    watchlist_df = _load_current_watchlist()
    if watchlist_df.empty:
        return pd.DataFrame()

    master_df = watchlist_df.merge(
        universe_df[
            [col for col in ["ticker", "name", "sector", "exchange"] if col in universe_df.columns]
        ],
        on="ticker",
        how="left",
    )

    fundamentals_df = fundamentals_repository.load_fundamentals(
        tickers=master_df["ticker"].tolist()
    )
    if not fundamentals_df.empty:
        master_df = master_df.merge(
            fundamentals_df[["ticker", "fundamental_score", "as_of_date"]],
            on="ticker",
            how="left",
        )

    master_df = master_df.sort_values("score", ascending=False).reset_index(drop=True)
    master_df.to_csv(MASTER_WATCHLIST_PATH, index=False)
    return master_df


def run() -> None:
    today = date.today().isoformat()

    print("\n" + "=" * 60)
    print(f"[monthly] Starting monthly pipeline - {today}")
    print("=" * 60)

    init_db()

    print("[monthly] Loading current universe...")
    universe_df = _load_universe()
    if universe_df.empty:
        print("[monthly] ERROR: data/universe_tickers.csv is missing or invalid.")
        return

    print(f"[monthly] Reviewing {len(universe_df)} tracked tickers...")
    review_df = _build_review(universe_df)
    cleaned_df = _save_universe_outputs(review_df)
    removed_count = len(review_df) - len(cleaned_df)
    print(
        f"[monthly] Clean universe saved with {len(cleaned_df)} tickers "
        f"({removed_count} removed)."
    )

    print("[monthly] Consolidating master watchlist snapshot...")
    master_df = _save_master_watchlist(cleaned_df if not cleaned_df.empty else universe_df)
    if master_df.empty:
        print("[monthly] No current weekly watchlist available. Skipped master watchlist export.")
    else:
        print(f"[monthly] Master watchlist saved with {len(master_df)} tickers.")

    print(f"[monthly] Pipeline complete - {today}\n")


if __name__ == "__main__":
    run()
