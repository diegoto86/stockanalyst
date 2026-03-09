"""
price_repository.py
-------------------
Persist and retrieve daily price bars (price_bars_daily table).
"""

import pandas as pd


def save_price_bars(df: pd.DataFrame) -> None:
    """
    Persist daily OHLCV bars to storage.

    Expected columns:
        ticker, date, open, high, low, close, adj_close, volume
    """
    raise NotImplementedError("save_price_bars not implemented yet")


def load_price_bars(tickers: list = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
    """
    Load daily price bars from storage, optionally filtered by ticker and date range.
    """
    raise NotImplementedError("load_price_bars not implemented yet")


def get_latest_date(ticker: str) -> str | None:
    """Return the most recent date stored for a given ticker, or None if not found."""
    raise NotImplementedError("get_latest_date not implemented yet")
