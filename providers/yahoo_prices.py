"""
yahoo_prices.py
---------------
Fetches daily OHLCV price bars from Yahoo Finance.
Update frequency: daily (after market close).
"""

import yfinance as yf
import pandas as pd
from typing import List


def _flatten_columns(raw: pd.DataFrame, ticker: str = None) -> pd.DataFrame:
    """
    Flatten yfinance MultiIndex columns (Price, Ticker) to lowercase flat columns.
    Works with both single-ticker and multi-ticker downloads.
    """
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        if ticker:
            # Filter to this ticker's columns
            df = df.xs(ticker, level=1, axis=1) if ticker in df.columns.get_level_values(1) else df
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
            else:
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        else:
            df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
    else:
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
    return df


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
        threads=True,
    )

    if raw.empty:
        return pd.DataFrame()

    records = []

    if len(tickers) == 1:
        ticker = tickers[0]
        df = _flatten_columns(raw)
        df = df.reset_index()
        df.columns = [c.lower().replace(" ", "_") for c in df.columns]
        df["ticker"] = ticker
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        records.append(df)
    else:
        for ticker in tickers:
            try:
                # MultiIndex: level 0 = Price, level 1 = Ticker
                if isinstance(raw.columns, pd.MultiIndex):
                    ticker_cols = [col for col in raw.columns if col[1] == ticker]
                    if not ticker_cols:
                        continue
                    df = raw[ticker_cols].copy()
                    df.columns = [c[0].lower().replace(" ", "_") for c in df.columns]
                else:
                    df = raw.copy()
                    df.columns = [c.lower().replace(" ", "_") for c in df.columns]

                df = df.dropna(how="all").reset_index()
                df.columns = [c.lower().replace(" ", "_") for c in df.columns]
                df["ticker"] = ticker
                df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
                records.append(df)
            except Exception as e:
                print(f"[prices] Error processing {ticker}: {e}")
                continue

    if not records:
        return pd.DataFrame()

    result = pd.concat(records, ignore_index=True)

    # Normalize column names
    col_map = {"adj_close": "adj_close", "adjclose": "adj_close"}
    result = result.rename(columns=col_map)

    # Ensure all expected columns exist
    expected = ["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]
    for col in expected:
        if col not in result.columns:
            result[col] = None

    result = result[expected].dropna(subset=["close"])
    return result


def fetch_index_prices(symbols: List[str] = None) -> pd.DataFrame:
    """
    Download recent daily prices for market context indices.

    Returns a DataFrame with columns: ticker, date, close, adj_close, change_pct
    """
    if symbols is None:
        symbols = ["SPY", "QQQ", "IWM", "^VIX"]

    records = []
    for sym in symbols:
        try:
            raw = yf.download(
                sym,
                period="5d",
                interval="1d",
                auto_adjust=False,
                actions=False,
                progress=False,
            )
            if raw.empty:
                continue

            df = _flatten_columns(raw)
            df = df.reset_index()
            df.columns = [c.lower().replace(" ", "_") for c in df.columns]
            df["ticker"] = sym
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df["change_pct"] = df["close"].pct_change() * 100
            records.append(df[["ticker", "date", "close", "adj_close", "change_pct"]].tail(1))
        except Exception as e:
            print(f"[prices] Error fetching index {sym}: {e}")
            continue

    if not records:
        return pd.DataFrame()
    return pd.concat(records, ignore_index=True)
