"""
yahoo_news.py
-------------
Fetches recent news headlines from Yahoo Finance.
Update frequency: daily (rolling window of last 3-7 days).
"""

import yfinance as yf
import pandas as pd
from typing import List


def fetch_news(tickers: List[str], days_back: int = 5) -> pd.DataFrame:
    """
    Fetch recent news headlines for a list of tickers.

    Returns a DataFrame with columns:
        ticker, date, headline, source,
        category, sentiment_proxy, impact_level,
        event_type, event_date
    """
    raise NotImplementedError("fetch_news not implemented yet")
