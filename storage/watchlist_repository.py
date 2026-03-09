"""
watchlist_repository.py
-----------------------
Persist and retrieve weekly watchlist / universe scores (universe_watchlist_weekly table).
"""

import pandas as pd


def save_watchlist(df: pd.DataFrame) -> None:
    """
    Persist weekly watchlist scores to storage.

    Expected columns:
        ticker, week_of, liquidity_ok, size_ok,
        quality_ok, valuation_ok, score, included
    """
    raise NotImplementedError("save_watchlist not implemented yet")


def load_watchlist(week_of: str = None) -> pd.DataFrame:
    """
    Load the watchlist for a given week (defaults to current week).
    """
    raise NotImplementedError("load_watchlist not implemented yet")


def current_week_exists() -> bool:
    """Return True if a watchlist has already been computed for the current week."""
    raise NotImplementedError("current_week_exists not implemented yet")
