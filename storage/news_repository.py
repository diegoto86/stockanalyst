"""
news_repository.py
------------------
Persist and retrieve news and events (news_events_daily table).
"""

import pandas as pd
from datetime import datetime, timedelta
from storage.db import get_connection


def save_news(df: pd.DataFrame) -> None:
    """
    Insert news records into storage (no deduplication by content — deduplicate by headline+ticker+date).
    Expected columns: ticker, date, headline, source, category,
                      sentiment_proxy, impact_level, event_type, event_date
    """
    if df.empty:
        return
    conn = get_connection()
    with conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO news_events_daily
                (ticker, date, headline, source, category,
                 sentiment_proxy, impact_level, event_type, event_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            df[["ticker", "date", "headline", "source", "category",
                "sentiment_proxy", "impact_level", "event_type", "event_date"]].values.tolist(),
        )
        conn.execute(
            "INSERT OR REPLACE INTO refresh_log VALUES ('news_events', ?)",
            (datetime.utcnow().isoformat(),),
        )
    conn.close()


def load_news(tickers: list = None, days_back: int = 7) -> pd.DataFrame:
    """Load recent news records, optionally filtered by ticker and recency."""
    conn = get_connection()
    cutoff = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    query = "SELECT * FROM news_events_daily WHERE date >= ?"
    params = [cutoff]
    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query += f" AND ticker IN ({placeholders})"
        params.extend(tickers)
    query += " ORDER BY ticker, date DESC"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_last_updated() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_updated FROM refresh_log WHERE dataset = 'news_events'"
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None
