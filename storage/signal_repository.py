"""
signal_repository.py
--------------------
Persistence for buy/sell signals.
Saves to SQLite (append-only by date) and optional CSV archive.
"""

import pandas as pd
from datetime import date, datetime
from pathlib import Path
from storage.db import get_connection
from config import DATA_DIR


# ---------------------------------------------------------------------------
# Buy candidates
# ---------------------------------------------------------------------------

def save_buy_candidates(df: pd.DataFrame) -> None:
    """Upsert buy candidates into buy_candidates_daily (PK = ticker + date)."""
    if df is None or df.empty:
        return
    conn = get_connection()
    with conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO buy_candidates_daily
                    (ticker, date, entry_price, stop_price, target_price,
                     shares, risk_pct, r_multiple_target, score, rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                    entry_price=excluded.entry_price,
                    stop_price=excluded.stop_price,
                    target_price=excluded.target_price,
                    shares=excluded.shares,
                    risk_pct=excluded.risk_pct,
                    r_multiple_target=excluded.r_multiple_target,
                    score=excluded.score,
                    rationale=excluded.rationale
            """, (
                row["ticker"], row["date"],
                row.get("entry_price"), row.get("stop_price"), row.get("target_price"),
                row.get("shares"), row.get("risk_pct"), row.get("r_multiple_target"),
                row.get("score"), row.get("rationale"),
            ))
    conn.close()


def save_sell_actions(df: pd.DataFrame) -> None:
    """Upsert sell actions into sell_actions_daily (PK = ticker + date)."""
    if df is None or df.empty:
        return
    conn = get_connection()
    with conn:
        for _, row in df.iterrows():
            conn.execute("""
                INSERT INTO sell_actions_daily
                    (ticker, date, action, current_price, entry_price,
                     current_stop, new_stop, sell_pct, current_r, rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, date) DO UPDATE SET
                    action=excluded.action,
                    current_price=excluded.current_price,
                    entry_price=excluded.entry_price,
                    current_stop=excluded.current_stop,
                    new_stop=excluded.new_stop,
                    sell_pct=excluded.sell_pct,
                    current_r=excluded.current_r,
                    rationale=excluded.rationale
            """, (
                row["ticker"], row["date"], row.get("action"),
                row.get("current_price"), row.get("entry_price"),
                row.get("current_stop"), row.get("new_stop"),
                row.get("sell_pct"), row.get("current_r"),
                row.get("rationale"),
            ))
    conn.close()


# ---------------------------------------------------------------------------
# Load historical signals
# ---------------------------------------------------------------------------

def load_buy_history(days_back: int = 30) -> pd.DataFrame:
    """Load buy candidates from the last N days."""
    conn = get_connection()
    query = """
        SELECT * FROM buy_candidates_daily
        WHERE date >= date('now', ?)
        ORDER BY date DESC, score DESC
    """
    df = pd.read_sql_query(query, conn, params=[f"-{days_back} days"])
    conn.close()
    return df


def load_sell_history(days_back: int = 30) -> pd.DataFrame:
    """Load sell actions from the last N days."""
    conn = get_connection()
    query = """
        SELECT * FROM sell_actions_daily
        WHERE date >= date('now', ?)
        ORDER BY date DESC, ticker ASC
    """
    df = pd.read_sql_query(query, conn, params=[f"-{days_back} days"])
    conn.close()
    return df


def load_buy_candidates_for_date(target_date: str) -> pd.DataFrame:
    """Load buy candidates for a specific date."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM buy_candidates_daily WHERE date = ? ORDER BY score DESC",
        conn, params=[target_date],
    )
    conn.close()
    return df


def load_sell_actions_for_date(target_date: str) -> pd.DataFrame:
    """Load sell actions for a specific date."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM sell_actions_daily WHERE date = ? ORDER BY ticker",
        conn, params=[target_date],
    )
    conn.close()
    return df


def get_signal_dates(limit: int = 60) -> list[str]:
    """Return distinct dates that have signals, most recent first."""
    conn = get_connection()
    cursor = conn.execute("""
        SELECT DISTINCT date FROM (
            SELECT date FROM buy_candidates_daily
            UNION
            SELECT date FROM sell_actions_daily
        ) ORDER BY date DESC LIMIT ?
    """, [limit])
    dates = [row[0] for row in cursor.fetchall()]
    conn.close()
    return dates


def get_signal_summary() -> pd.DataFrame:
    """Daily summary: count of buy candidates and sell actions per date."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT
            date,
            SUM(buy_count) AS buy_count,
            SUM(sell_count) AS sell_count
        FROM (
            SELECT date, COUNT(*) AS buy_count, 0 AS sell_count
            FROM buy_candidates_daily GROUP BY date
            UNION ALL
            SELECT date, 0 AS buy_count, COUNT(*) AS sell_count
            FROM sell_actions_daily GROUP BY date
        )
        GROUP BY date
        ORDER BY date DESC
        LIMIT 60
    """, conn)
    conn.close()
    return df


# ---------------------------------------------------------------------------
# CSV archive (date-stamped snapshots)
# ---------------------------------------------------------------------------

HISTORY_DIR = Path(DATA_DIR) / "history"


def archive_csv(df: pd.DataFrame, prefix: str) -> None:
    """Save a date-stamped CSV copy to data/history/."""
    if df is None or df.empty:
        return
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    path = HISTORY_DIR / f"{prefix}_{today}.csv"
    df.to_csv(path, index=False)
