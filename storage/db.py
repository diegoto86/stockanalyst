"""
db.py
-----
SQLite database initialisation and connection management.
Creates all tables on first run if they don't exist.
"""

import sqlite3
from pathlib import Path
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    with conn:
        conn.executescript("""
            -- Daily OHLCV price bars
            CREATE TABLE IF NOT EXISTS price_bars_daily (
                ticker      TEXT NOT NULL,
                date        TEXT NOT NULL,
                open        REAL,
                high        REAL,
                low         REAL,
                close       REAL,
                adj_close   REAL,
                volume      INTEGER,
                PRIMARY KEY (ticker, date)
            );

            -- Daily technical snapshot
            CREATE TABLE IF NOT EXISTS technical_snapshot_daily (
                ticker          TEXT NOT NULL,
                date            TEXT NOT NULL,
                ma20            REAL,
                ma50            REAL,
                ma200           REAL,
                rsi14           REAL,
                atr14           REAL,
                pullback_pct    REAL,
                trend_state     TEXT,
                setup_flags     TEXT,
                PRIMARY KEY (ticker, date)
            );

            -- Daily news and events
            CREATE TABLE IF NOT EXISTS news_events_daily (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT NOT NULL,
                date            TEXT NOT NULL,
                headline        TEXT,
                source          TEXT,
                category        TEXT,
                sentiment_proxy REAL,
                impact_level    TEXT,
                event_type      TEXT,
                event_date      TEXT
            );

            -- Quarterly fundamentals snapshot
            CREATE TABLE IF NOT EXISTS fundamentals_snapshot_quarterly (
                ticker                  TEXT NOT NULL,
                as_of_date              TEXT NOT NULL,
                fiscal_period           TEXT,
                revenue_growth_ttm      REAL,
                eps_growth_ttm          REAL,
                gross_margin            REAL,
                operating_margin        REAL,
                net_debt_to_ebitda      REAL,
                pe_ttm                  REAL,
                ev_to_ebitda            REAL,
                fcf_yield               REAL,
                fundamental_score       REAL,
                PRIMARY KEY (ticker, as_of_date)
            );

            -- Weekly universe watchlist
            CREATE TABLE IF NOT EXISTS universe_watchlist_weekly (
                ticker          TEXT NOT NULL,
                week_of         TEXT NOT NULL,
                liquidity_ok    INTEGER,
                size_ok         INTEGER,
                quality_ok      INTEGER,
                valuation_ok    INTEGER,
                score           REAL,
                included        INTEGER,
                PRIMARY KEY (ticker, week_of)
            );

            -- Daily buy candidates output
            CREATE TABLE IF NOT EXISTS buy_candidates_daily (
                ticker              TEXT NOT NULL,
                date                TEXT NOT NULL,
                entry_price         REAL,
                stop_price          REAL,
                target_price        REAL,
                shares              INTEGER,
                risk_pct            REAL,
                r_multiple_target   REAL,
                score               REAL,
                rationale           TEXT,
                PRIMARY KEY (ticker, date)
            );

            -- Daily sell actions output
            CREATE TABLE IF NOT EXISTS sell_actions_daily (
                ticker      TEXT NOT NULL,
                date        TEXT NOT NULL,
                action      TEXT,
                new_stop    REAL,
                sell_pct    REAL,
                rationale   TEXT,
                PRIMARY KEY (ticker, date)
            );

            -- Metadata: track last update time per dataset
            CREATE TABLE IF NOT EXISTS refresh_log (
                dataset     TEXT PRIMARY KEY,
                last_updated TEXT NOT NULL
            );
        """)
    conn.close()
