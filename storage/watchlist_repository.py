"""
watchlist_repository.py
-----------------------
Persist and retrieve weekly watchlist / universe scores.
"""

import pandas as pd
from datetime import datetime, date, timedelta
from storage.db import get_connection


def _current_week_start() -> str:
    """Return the Monday of the current week as YYYY-MM-DD."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def save_watchlist(df: pd.DataFrame) -> None:
    """
    Upsert weekly watchlist scores into storage.
    Expected columns: ticker, week_of, liquidity_ok, size_ok,
                      quality_ok, valuation_ok, score, included
    """
    if df.empty:
        return
    conn = get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO universe_watchlist_weekly
                (ticker, week_of, liquidity_ok, size_ok, quality_ok, valuation_ok, score, included)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, week_of) DO UPDATE SET
                liquidity_ok=excluded.liquidity_ok, size_ok=excluded.size_ok,
                quality_ok=excluded.quality_ok, valuation_ok=excluded.valuation_ok,
                score=excluded.score, included=excluded.included
            """,
            df[["ticker", "week_of", "liquidity_ok", "size_ok",
                "quality_ok", "valuation_ok", "score", "included"]].values.tolist(),
        )
        conn.execute(
            "INSERT OR REPLACE INTO refresh_log VALUES ('watchlist_base', ?)",
            (datetime.utcnow().isoformat(),),
        )
    conn.close()


def load_watchlist(week_of: str = None) -> pd.DataFrame:
    """Load the watchlist for a given week (defaults to current week). Returns only included tickers."""
    if week_of is None:
        week_of = _current_week_start()
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM universe_watchlist_weekly WHERE week_of = ? AND included = 1 ORDER BY score DESC",
        conn,
        params=[week_of],
    )
    conn.close()
    return df


def current_week_exists() -> bool:
    """Return True if a watchlist has already been computed for the current week."""
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) FROM universe_watchlist_weekly WHERE week_of = ?",
        (_current_week_start(),),
    ).fetchone()
    conn.close()
    return row[0] > 0 if row else False


def get_last_updated() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_updated FROM refresh_log WHERE dataset = 'watchlist_base'"
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None
