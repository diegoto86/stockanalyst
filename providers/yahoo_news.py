"""
yahoo_news.py
-------------
Fetches recent news headlines from Yahoo Finance.
Update frequency: daily (rolling window of last 3-7 days).
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List


def _classify_sentiment(headline: str) -> float:
    """
    Simple keyword-based sentiment proxy.
    Returns a score between -1 (negative) and +1 (positive).
    """
    headline_lower = headline.lower()

    positive_words = [
        "beat", "beats", "record", "growth", "upgrade", "strong", "rally",
        "profit", "surge", "gain", "outperform", "buy", "bullish", "raises",
        "exceeds", "above", "positive", "boost", "momentum"
    ]
    negative_words = [
        "miss", "misses", "downgrade", "loss", "decline", "cut", "weak",
        "sell", "bearish", "below", "warning", "risk", "concern", "drop",
        "fall", "lawsuit", "investigation", "fraud", "negative", "reduces"
    ]

    pos = sum(1 for w in positive_words if w in headline_lower)
    neg = sum(1 for w in negative_words if w in headline_lower)

    if pos + neg == 0:
        return 0.0
    return round((pos - neg) / (pos + neg), 2)


def _classify_impact(headline: str) -> str:
    """Classify headline impact level: high / medium / low."""
    high_keywords = ["earnings", "fda", "merger", "acquisition", "bankruptcy",
                     "guidance", "dividend", "buyback", "split", "sec", "investigation"]
    medium_keywords = ["upgrade", "downgrade", "price target", "analyst", "forecast", "outlook"]

    headline_lower = headline.lower()
    if any(k in headline_lower for k in high_keywords):
        return "high"
    if any(k in headline_lower for k in medium_keywords):
        return "medium"
    return "low"


def _classify_event_type(headline: str) -> str:
    """Detect event type from headline."""
    headline_lower = headline.lower()
    if any(k in headline_lower for k in ["earnings", "results", "quarterly", "eps", "revenue"]):
        return "earnings"
    if any(k in headline_lower for k in ["merger", "acquisition", "deal", "buyout"]):
        return "m&a"
    if any(k in headline_lower for k in ["fda", "approval", "trial", "drug"]):
        return "regulatory"
    if any(k in headline_lower for k in ["upgrade", "downgrade", "price target"]):
        return "analyst"
    if any(k in headline_lower for k in ["dividend", "buyback", "split"]):
        return "corporate_action"
    return "general"


def fetch_news(tickers: List[str], days_back: int = 5) -> pd.DataFrame:
    """
    Fetch recent news headlines for a list of tickers via yfinance.

    Returns a DataFrame with columns:
        ticker, date, headline, source, category,
        sentiment_proxy, impact_level, event_type, event_date
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    records = []

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            news_items = t.news or []

            for item in news_items:
                # yfinance returns providerPublishTime as unix timestamp
                pub_ts = item.get("providerPublishTime") or item.get("published") or 0
                if isinstance(pub_ts, (int, float)):
                    pub_dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                else:
                    try:
                        pub_dt = datetime.fromisoformat(str(pub_ts))
                    except Exception:
                        continue

                if pub_dt < cutoff:
                    continue

                headline = item.get("title", "")
                if not headline:
                    continue

                records.append({
                    "ticker": ticker,
                    "date": pub_dt.strftime("%Y-%m-%d"),
                    "headline": headline,
                    "source": item.get("publisher", ""),
                    "category": item.get("type", "STORY"),
                    "sentiment_proxy": _classify_sentiment(headline),
                    "impact_level": _classify_impact(headline),
                    "event_type": _classify_event_type(headline),
                    "event_date": pub_dt.strftime("%Y-%m-%d"),
                })
        except Exception as e:
            print(f"[news] Error fetching {ticker}: {e}")
            continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records).drop_duplicates(subset=["ticker", "headline"])
