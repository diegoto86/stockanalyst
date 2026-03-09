"""
news_repository.py
------------------
Persist and retrieve news and events (news_events_daily table).
"""

import pandas as pd


def save_news(df: pd.DataFrame) -> None:
    """
    Persist news records to storage.

    Expected columns:
        ticker, date, headline, source,
        category, sentiment_proxy, impact_level,
        event_type, event_date
    """
    raise NotImplementedError("save_news not implemented yet")


def load_news(tickers: list = None, days_back: int = 7) -> pd.DataFrame:
    """
    Load recent news records, optionally filtered by ticker and recency.
    """
    raise NotImplementedError("load_news not implemented yet")
