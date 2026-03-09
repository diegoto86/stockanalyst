"""
fundamentals_repository.py
--------------------------
Persist and retrieve quarterly fundamental snapshots (fundamentals_snapshot_quarterly table).
"""

import pandas as pd


def save_fundamentals(df: pd.DataFrame) -> None:
    """
    Persist quarterly fundamental data to storage.

    Expected columns:
        ticker, as_of_date, fiscal_period,
        revenue_growth_ttm, eps_growth_ttm,
        gross_margin, operating_margin,
        net_debt_to_ebitda, pe_ttm, ev_to_ebitda,
        fcf_yield, fundamental_score
    """
    raise NotImplementedError("save_fundamentals not implemented yet")


def load_fundamentals(tickers: list = None) -> pd.DataFrame:
    """
    Load the most recent fundamental snapshot per ticker.
    """
    raise NotImplementedError("load_fundamentals not implemented yet")


def is_stale(ticker: str, max_days: int = 90) -> bool:
    """Return True if the fundamental snapshot for a ticker is older than max_days."""
    raise NotImplementedError("is_stale not implemented yet")
