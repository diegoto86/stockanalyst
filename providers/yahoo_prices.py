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
    if not tickers:
        return pd.DataFrame()

    raw = yf.download(
        tickers,
        period=period,
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    records = []

    if len(tickers) == 1:
        ticker = tickers[0]
        df = raw.copy()
        df.columns = [c[0].lower() for c in df.columns]
        df = df.reset_index()
        df["ticker"] = ticker
        df = df.rename(columns={"Date": "date", "Adj Close": "adj_close"})
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        records.append(df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]])
    else:
        for ticker in tickers:
            try:
                df = raw[ticker].copy().dropna(how="all")
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                df = df.reset_index()
                df["ticker"] = ticker
                df = df.rename(columns={"date": "date", "adj_close": "adj_close"})
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                records.append(df[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]])
            except Exception:
                continue

    if not records:
        return pd.DataFrame()

    result = pd.concat(records, ignore_index=True)
    result = result.dropna(subset=["close"])
    return result


def fetch_index_prices(symbols: List[str] = None) -> pd.DataFrame:
    """
    Download recent daily prices for market context indices.

    Returns a DataFrame with columns: ticker, date, close, adj_close, change_pct
    """
    if symbols is None:
        symbols = ["SPY", "QQQ", "IWM", "^VIX"]

    raw = yf.download(
        symbols,
        period="5d",
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        group_by="ticker",
        threads=True,
    )

    records = []
    for sym in symbols:
        try:
            if len(symbols) == 1:
                df = raw.copy()
            else:
                df = raw[sym].copy()
            df = df.dropna(how="all").reset_index()
            df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
            df = df.rename(columns={"adj close": "adj_close"})
            df["ticker"] = sym
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["change_pct"] = df["close"].pct_change() * 100
            records.append(df[["ticker", "date", "close", "adj_close", "change_pct"]].tail(1))
        except Exception:
            continue

    if not records:
        return pd.DataFrame()
    return pd.concat(records, ignore_index=True)
