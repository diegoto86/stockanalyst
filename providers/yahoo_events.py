"""
yahoo_events.py
---------------
Fetches upcoming corporate events (earnings dates, dividends) from Yahoo Finance.
Update frequency: daily.
"""

import yfinance as yf
import pandas as pd
from typing import List


def fetch_earnings_calendar(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch upcoming earnings dates for a list of tickers.

    Returns a DataFrame with columns:
        ticker, earnings_date, eps_estimate, revenue_estimate
    """
    raise NotImplementedError("fetch_earnings_calendar not implemented yet")
