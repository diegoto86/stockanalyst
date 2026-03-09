"""
fundamentals_repository.py
--------------------------
Persist and retrieve quarterly fundamental snapshots.
"""

import pandas as pd
from datetime import datetime, timedelta
from storage.db import get_connection


def save_fundamentals(df: pd.DataFrame) -> None:
    """
    Upsert quarterly fundamental data into storage.
    Expected columns: ticker, as_of_date, fiscal_period,
                      revenue_growth_ttm, eps_growth_ttm, gross_margin,
                      operating_margin, net_debt_to_ebitda, pe_ttm,
                      ev_to_ebitda, fcf_yield, fundamental_score
    """
    if df.empty:
        return
    conn = get_connection()
    with conn:
        conn.executemany(
            """
            INSERT INTO fundamentals_snapshot_quarterly
                (ticker, as_of_date, fiscal_period, revenue_growth_ttm, eps_growth_ttm,
                 gross_margin, operating_margin, net_debt_to_ebitda, pe_ttm,
                 ev_to_ebitda, fcf_yield, fundamental_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker, as_of_date) DO UPDATE SET
                fiscal_period=excluded.fiscal_period,
                revenue_growth_ttm=excluded.revenue_growth_ttm,
                eps_growth_ttm=excluded.eps_growth_ttm,
                gross_margin=excluded.gross_margin,
                operating_margin=excluded.operating_margin,
                net_debt_to_ebitda=excluded.net_debt_to_ebitda,
                pe_ttm=excluded.pe_ttm,
                ev_to_ebitda=excluded.ev_to_ebitda,
                fcf_yield=excluded.fcf_yield,
                fundamental_score=excluded.fundamental_score
            """,
            df[["ticker", "as_of_date", "fiscal_period", "revenue_growth_ttm",
                "eps_growth_ttm", "gross_margin", "operating_margin",
                "net_debt_to_ebitda", "pe_ttm", "ev_to_ebitda",
                "fcf_yield", "fundamental_score"]].values.tolist(),
        )
        conn.execute(
            "INSERT OR REPLACE INTO refresh_log VALUES ('fundamentals_snapshot', ?)",
            (datetime.utcnow().isoformat(),),
        )
    conn.close()


def load_fundamentals(tickers: list = None) -> pd.DataFrame:
    """Load the most recent fundamental snapshot per ticker."""
    conn = get_connection()
    query = """
        SELECT f.* FROM fundamentals_snapshot_quarterly f
        INNER JOIN (
            SELECT ticker, MAX(as_of_date) AS max_date
            FROM fundamentals_snapshot_quarterly
            GROUP BY ticker
        ) latest ON f.ticker = latest.ticker AND f.as_of_date = latest.max_date
    """
    params = []
    if tickers:
        placeholders = ",".join("?" * len(tickers))
        query += f" WHERE f.ticker IN ({placeholders})"
        params.extend(tickers)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df


def is_stale(ticker: str, max_days: int = 90) -> bool:
    """Return True if the fundamental snapshot for a ticker is older than max_days."""
    conn = get_connection()
    row = conn.execute(
        "SELECT MAX(as_of_date) FROM fundamentals_snapshot_quarterly WHERE ticker = ?",
        (ticker,),
    ).fetchone()
    conn.close()
    if not row or not row[0]:
        return True
    last_date = datetime.fromisoformat(row[0])
    return datetime.utcnow() - last_date > timedelta(days=max_days)


def get_last_updated() -> datetime | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT last_updated FROM refresh_log WHERE dataset = 'fundamentals_snapshot'"
    ).fetchone()
    conn.close()
    return datetime.fromisoformat(row[0]) if row else None
