"""
yahoo_prices.py
---------------
Fetches daily OHLCV price bars from Yahoo Finance.
Update frequency: daily (after market close).
"""

import yfinance as yf
import pandas as pd
from typing import List


def fetch_daily_bars(tickers: List[str], period: str = "1y") -> pd.DataFrame:
    """
    Download daily OHLCV bars for a list of tickers.

    Returns a DataFrame with columns:
        ticker, date, open, high, low, close, adj_close, volume
    """
    raise NotImplementedError("fetch_daily_bars not implemented yet")


def fetch_index_prices(symbols: List[str] = None) -> pd.DataFrame:
    """
    Download daily prices for market context indices (e.g. SPY, QQQ, IWM).

    Returns a DataFrame with columns:
        ticker, date, close, adj_close
    """
    if symbols is None:
        symbols = ["SPY", "QQQ", "IWM"]
    raise NotImplementedError("fetch_index_prices not implemented yet")
