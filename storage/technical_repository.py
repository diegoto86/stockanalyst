"""
technical_repository.py
-----------------------
Persist and retrieve daily technical snapshots (technical_snapshot_daily table).
"""

import pandas as pd


def save_technical_snapshot(df: pd.DataFrame) -> None:
    """
    Persist daily technical indicators to storage.

    Expected columns:
        ticker, date, ma20, ma50, ma200,
        rsi14, atr14, pullback_pct, trend_state, setup_flags
    """
    raise NotImplementedError("save_technical_snapshot not implemented yet")


def load_technical_snapshot(tickers: list = None, date: str = None) -> pd.DataFrame:
    """
    Load the latest technical snapshot, optionally filtered by ticker or date.
    """
    raise NotImplementedError("load_technical_snapshot not implemented yet")
