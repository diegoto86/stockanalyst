"""
signal_evaluator.py
-------------------
Evaluates historical buy signals against subsequent price action.
Tracks: return at N days, whether target/stop was hit, max gain, max drawdown.
"""

import pandas as pd
import numpy as np
from datetime import date
from storage.db import get_connection


def evaluate_signals(lookback_days: int = 30) -> pd.DataFrame:
    """
    Evaluate buy signals from the last N days against actual price data.

    For each signal, checks price action from signal_date to today:
    - return_pct: (current_price - entry_price) / entry_price
    - hit_target: did price reach target_price at any point?
    - hit_stop: did price reach stop_price at any point?
    - max_gain_pct: best intraday return during holding period
    - max_drawdown_pct: worst intraday drawdown during holding period

    Returns DataFrame of outcomes and saves to signal_outcomes table.
    """
    conn = get_connection()

    # Load buy signals from last N days
    signals = pd.read_sql_query("""
        SELECT ticker, date as signal_date, entry_price, stop_price, target_price
        FROM buy_candidates_daily
        WHERE date >= date('now', ?)
    """, conn, params=[f"-{lookback_days} days"])

    if signals.empty:
        conn.close()
        return pd.DataFrame()

    today = date.today().isoformat()
    outcomes = []

    for _, sig in signals.iterrows():
        ticker = sig["ticker"]
        signal_date = sig["signal_date"]
        entry = sig["entry_price"]
        target = sig["target_price"]
        stop = sig["stop_price"]

        if not entry or entry <= 0:
            continue

        # Load price bars from signal_date to today
        prices = pd.read_sql_query("""
            SELECT date, high, low, close
            FROM price_bars_daily
            WHERE ticker = ? AND date > ? AND date <= ?
            ORDER BY date ASC
        """, conn, params=[ticker, signal_date, today])

        if prices.empty:
            continue

        days_held = len(prices)
        current_price = prices.iloc[-1]["close"]
        return_pct = round((current_price - entry) / entry * 100, 2)

        # Track max gain and max drawdown using intraday highs/lows
        max_high = prices["high"].max()
        min_low = prices["low"].min()
        max_gain_pct = round((max_high - entry) / entry * 100, 2)
        max_drawdown_pct = round((min_low - entry) / entry * 100, 2)

        # Did price hit target or stop?
        hit_target = int(max_high >= target) if target else 0
        hit_stop = int(min_low <= stop) if stop else 0

        outcomes.append({
            "ticker": ticker,
            "signal_date": signal_date,
            "entry_price": entry,
            "eval_date": today,
            "days_held": days_held,
            "price_at_eval": round(current_price, 2),
            "return_pct": return_pct,
            "hit_target": hit_target,
            "hit_stop": hit_stop,
            "max_gain_pct": max_gain_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "target_price": target,
            "stop_price": stop,
        })

    if not outcomes:
        conn.close()
        return pd.DataFrame()

    result = pd.DataFrame(outcomes)

    # Save to DB (upsert)
    with conn:
        for _, row in result.iterrows():
            conn.execute("""
                INSERT INTO signal_outcomes
                    (ticker, signal_date, entry_price, eval_date, days_held,
                     price_at_eval, return_pct, hit_target, hit_stop,
                     max_gain_pct, max_drawdown_pct, target_price, stop_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticker, signal_date, eval_date) DO UPDATE SET
                    days_held=excluded.days_held,
                    price_at_eval=excluded.price_at_eval,
                    return_pct=excluded.return_pct,
                    hit_target=excluded.hit_target,
                    hit_stop=excluded.hit_stop,
                    max_gain_pct=excluded.max_gain_pct,
                    max_drawdown_pct=excluded.max_drawdown_pct
            """, (
                row["ticker"], row["signal_date"], row["entry_price"],
                row["eval_date"], row["days_held"], row["price_at_eval"],
                row["return_pct"], row["hit_target"], row["hit_stop"],
                row["max_gain_pct"], row["max_drawdown_pct"],
                row["target_price"], row["stop_price"],
            ))
    conn.close()

    return result


def get_performance_summary() -> dict:
    """
    Compute aggregate performance metrics from signal_outcomes.

    Returns dict with:
        total_signals, win_rate, avg_return, avg_winner, avg_loser,
        hit_target_rate, hit_stop_rate, expectancy, max_drawdown
    """
    conn = get_connection()

    # Get the latest evaluation per signal (most recent eval_date)
    df = pd.read_sql_query("""
        SELECT o.* FROM signal_outcomes o
        INNER JOIN (
            SELECT ticker, signal_date, MAX(eval_date) AS max_eval
            FROM signal_outcomes
            GROUP BY ticker, signal_date
        ) latest
        ON o.ticker = latest.ticker
        AND o.signal_date = latest.signal_date
        AND o.eval_date = latest.max_eval
    """, conn)
    conn.close()

    if df.empty:
        return {}

    total = len(df)
    winners = df[df["return_pct"] > 0]
    losers = df[df["return_pct"] <= 0]

    return {
        "total_signals": total,
        "win_rate": round(len(winners) / total * 100, 1) if total else 0,
        "avg_return": round(df["return_pct"].mean(), 2),
        "avg_winner": round(winners["return_pct"].mean(), 2) if not winners.empty else 0,
        "avg_loser": round(losers["return_pct"].mean(), 2) if not losers.empty else 0,
        "hit_target_rate": round(df["hit_target"].mean() * 100, 1),
        "hit_stop_rate": round(df["hit_stop"].mean() * 100, 1),
        "expectancy": round(
            (len(winners) / total * winners["return_pct"].mean() if not winners.empty else 0)
            + (len(losers) / total * losers["return_pct"].mean() if not losers.empty else 0),
            2
        ) if total else 0,
        "max_drawdown": round(df["max_drawdown_pct"].min(), 2),
        "avg_days_held": round(df["days_held"].mean(), 1),
    }


def load_outcomes(days_back: int = 30) -> pd.DataFrame:
    """Load signal outcomes for the last N days."""
    conn = get_connection()
    df = pd.read_sql_query("""
        SELECT o.* FROM signal_outcomes o
        INNER JOIN (
            SELECT ticker, signal_date, MAX(eval_date) AS max_eval
            FROM signal_outcomes
            GROUP BY ticker, signal_date
        ) latest
        ON o.ticker = latest.ticker
        AND o.signal_date = latest.signal_date
        AND o.eval_date = latest.max_eval
        WHERE o.signal_date >= date('now', ?)
        ORDER BY o.signal_date DESC, o.return_pct DESC
    """, conn, params=[f"-{days_back} days"])
    conn.close()
    return df
