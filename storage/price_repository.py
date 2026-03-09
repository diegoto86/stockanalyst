"""
price_repository.py
-------------------
Persist and retrieve daily price bars (price_bars_daily table).
"""

import pandas as pd
from datetime import datetime
from storage.db import get_connection


def save_price_bars(df: pd.DataFrame) -> None:
    """
    Upsert daily OHLCV bars into storage.
    Expected columns: ticker, date, open, high, low, close, adj_close, volume
    """
    if df.empty:
        return
    conn = get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO price_bars_daily
                (ticker, date, open, high, low, close, adj_close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                open=excluded.open, high=excluded.high, low=excluded.low,
                close=excluded.close, adj_close=excluded.adj_close,
                volume=excluded.volume
            """,
            df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]].values.tolist(),
        )
        conn.execute(
            "INSERT OR REPLACE INTO refresh_log VALUES ('prices_daily', ?)",
            (datetime.utcnow().isoformat(),),
        )
    conn.close()


def load_price_bars(
    tickers: list = None,
    start_date: str = None,
    end_date: str = None,
) -> pd.DataFrame:
    """Load daily price bars, optionally filtered by ticker and date range."""
    conn = get_connection()
    query = "SELECT * FROM price_bars_daily WHERE 1=1"
    params = []
    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query += f" AND ticker IN ({placeholders})"
        params.extend(tickers)
    if start_date:
        query += " AND date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date <= ?"
        params.append(end_date)
    query += " ORDER BY ticker, date"
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_latest_date(ticker: str) -> str | None:
    """Return the most recent date stored for a given ticker."""
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(date) FROM price_bars_daily WHERE ticker = ?", (ticker,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def get_last_updated() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_updated FROM refresh_log WHERE dataset = 'prices_daily'"
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None
