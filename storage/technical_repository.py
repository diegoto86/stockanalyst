"""
technical_repository.py
-----------------------
Persist and retrieve daily technical snapshots (technical_snapshot_daily table).
"""

import pandas as pd
from datetime import datetime
from storage.db import get_connection


def save_technical_snapshot(df: pd.DataFrame) -> None:
    """
    Upsert daily technical indicators into storage.
    Expected columns: ticker, date, ma20, ma50, ma200,
                      rsi14, atr14, pullback_pct, trend_state, setup_flags
    """
    if df.empty:
        return
    conn = get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO technical_snapshot_daily
                (ticker, date, ma20, ma50, ma200, rsi14, atr14, pullback_pct, trend_state, setup_flags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, date) DO UPDATE SET
                ma20=excluded.ma20, ma50=excluded.ma50, ma200=excluded.ma200,
                rsi14=excluded.rsi14, atr14=excluded.atr14,
                pullback_pct=excluded.pullback_pct,
                trend_state=excluded.trend_state, setup_flags=excluded.setup_flags
            """,
            df[["ticker", "date", "ma20", "ma50", "ma200", "rsi14", "atr14",
                "pullback_pct", "trend_state", "setup_flags"]].values.tolist(),
        )
        conn.execute(
            "INSERT OR REPLACE INTO refresh_log VALUES ('technical_snapshot', ?)",
            (datetime.utcnow().isoformat(),),
        )
    conn.close()


def load_technical_snapshot(tickers: list = None, date: str = None) -> pd.DataFrame:
    """
    Load the latest technical snapshot per ticker.
    If date is None, returns the most recent row per ticker.
    """
    conn = get_connection()
    if date:
        query = "SELECT * FROM technical_snapshot_daily WHERE date = ?"
        params = [date]
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            query += f" AND ticker IN ({placeholders})"
            params.extend(tickers)
    else:
        # Latest row per ticker
        query = """
            SELECT t.* FROM technical_snapshot_daily t
            INNER JOIN (
                SELECT ticker, MAX(date) AS max_date
                FROM technical_snapshot_daily
                GROUP BY ticker
            ) latest ON t.ticker = latest.ticker AND t.date = latest.max_date
        """
        params = []
        if tickers:
            placeholders = ",".join("?" * len(tickers))
            query += f" WHERE t.ticker IN ({placeholders})"
            params.extend(tickers)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def get_last_updated() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_updated FROM refresh_log WHERE dataset = 'technical_snapshot'"
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None
