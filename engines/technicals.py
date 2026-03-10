"""
technicals.py
-------------
Computes technical indicators from daily price bars.
Produces the technical_snapshot_daily dataset.
"""

import pandas as pd
import numpy as np
from config import (
    PULLBACK_MAX_PCT,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ATR_STOP_MULTIPLIER,
)


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def _trend_state(row: pd.Series) -> str:
    """
    Classify trend state based on moving average alignment.
    uptrend:   close > ma50 > ma200
    downtrend: close < ma50 < ma200
    mixed:     anything else
    """
    try:
        close = row["close"]
        ma50 = row["ma50"]
        ma200 = row["ma200"]
        if pd.isna(ma50) or pd.isna(ma200):
            return "unknown"
        if close > ma50 > ma200:
            return "uptrend"
        if close < ma50 < ma200:
            return "downtrend"
        return "mixed"
    except Exception:
        return "unknown"


def _setup_flags(row: pd.Series) -> str:
    """
    Detect setup conditions and return a comma-separated flag string.
    Flags:
        pullback_ok   — price pulled back from recent high within threshold
        rsi_reset     — RSI has reset toward oversold (not overbought)
        above_ma50    — price above 50-day MA
        above_ma200   — price above 200-day MA
    """
    flags = []
    try:
        if not pd.isna(row.get("pullback_pct")) and 0 < row["pullback_pct"] <= PULLBACK_MAX_PCT:
            flags.append("pullback_ok")
        if not pd.isna(row.get("rsi14")) and row["rsi14"] <= RSI_OVERSOLD + 15:
            flags.append("rsi_reset")
        if not pd.isna(row.get("ma50")) and row["close"] > row["ma50"]:
            flags.append("above_ma50")
        if not pd.isna(row.get("ma200")) and row["close"] > row["ma200"]:
            flags.append("above_ma200")
    except Exception:
        pass
    return ",".join(flags)


def compute_technicals(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily technical snapshot for all tickers in price_df.

    Input: price_df with columns ticker, date, open, high, low, close, adj_close, volume
    Returns: DataFrame matching technical_snapshot_daily schema
    """
    if price_df.empty:
        return pd.DataFrame()

    records = []
    price_df = price_df.copy()
    price_df["date"] = pd.to_datetime(price_df["date"])
    price_df = price_df.sort_values(["ticker", "date"])

    for ticker, group in price_df.groupby("ticker"):
        group = group.set_index("date").sort_index()
        close = group["close"]
        high = group["high"]
        low = group["low"]

        if len(close) < 20:
            continue

        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()
        rsi14 = _rsi(close, 14)
        atr14 = _atr(high, low, close, 14)

        # Pullback from 20-day high
        high_20 = close.rolling(20).max()
        pullback_pct = (high_20 - close) / high_20.replace(0, np.nan)

        snapshot = pd.DataFrame({
            "ticker": ticker,
            "date": group.index.strftime("%Y-%m-%d"),
            "close": close.values,
            "ma20": ma20.values,
            "ma50": ma50.values,
            "ma200": ma200.values,
            "rsi14": rsi14.values,
            "atr14": atr14.values,
            "pullback_pct": pullback_pct.values,
        })

        snapshot["trend_state"] = snapshot.apply(_trend_state, axis=1)
        snapshot["setup_flags"] = snapshot.apply(_setup_flags, axis=1)

        # Keep only the last row (latest day) — preserve close for engines
        latest = snapshot.iloc[[-1]]
        records.append(latest)

    if not records:
        return pd.DataFrame()

    result = pd.concat(records, ignore_index=True)
    cols = ["ticker", "date", "close", "ma20", "ma50", "ma200", "rsi14", "atr14", "pullback_pct", "trend_state", "setup_flags"]
    return result[cols]


def compute_technicals_full_history(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Same as compute_technicals but returns ALL historical rows, not just latest.
    Useful for backtesting or initial DB population.
    """
    if price_df.empty:
        return pd.DataFrame()

    records = []
    price_df = price_df.copy()
    price_df["date"] = pd.to_datetime(price_df["date"])
    price_df = price_df.sort_values(["ticker", "date"])

    for ticker, group in price_df.groupby("ticker"):
        group = group.set_index("date").sort_index()
        close = group["close"]
        high = group["high"]
        low = group["low"]

        if len(close) < 20:
            continue

        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()
        rsi14 = _rsi(close, 14)
        atr14 = _atr(high, low, close, 14)
        high_20 = close.rolling(20).max()
        pullback_pct = (high_20 - close) / high_20.replace(0, np.nan)

        snapshot = pd.DataFrame({
            "ticker": ticker,
            "date": group.index.strftime("%Y-%m-%d"),
            "close": close.values,
            "ma20": ma20.values,
            "ma50": ma50.values,
            "ma200": ma200.values,
            "rsi14": rsi14.values,
            "atr14": atr14.values,
            "pullback_pct": pullback_pct.values,
        })

        snapshot["trend_state"] = snapshot.apply(_trend_state, axis=1)
        snapshot["setup_flags"] = snapshot.apply(_setup_flags, axis=1)
        snapshot = snapshot.dropna(subset=["ma20"])
        records.append(snapshot)

    if not records:
        return pd.DataFrame()

    result = pd.concat(records, ignore_index=True)
    cols = ["ticker", "date", "close", "ma20", "ma50", "ma200", "rsi14", "atr14", "pullback_pct", "trend_state", "setup_flags"]
    return result[cols]
