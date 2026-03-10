"""
sell_engine.py
--------------
SELL block: manages open positions in the portfolio.

Sequence:
    1. Load portfolio_positions (manual CSV)
    2. Enrich with technical_snapshot_daily
    3. Enrich with news_events_daily
    4. Check fundamentals_snapshot_quarterly for material changes
    5. Emit explicit action plan (hold / raise_stop / partial_sell / close)

No automatic execution — user decides and trades manually.
"""

import pandas as pd
import numpy as np
from datetime import date
from config import ATR_STOP_MULTIPLIER, MIN_R_MULTIPLE_TARGET


def _r_multiple(entry: float, current: float, stop: float) -> float | None:
    """Compute current R multiple."""
    risk = entry - stop
    if risk <= 0:
        return None
    return round((current - entry) / risk, 2)


def _compute_new_trailing_stop(
    entry: float,
    current_stop: float,
    atr: float,
    close: float,
) -> float:
    """
    Compute a new trailing stop using ATR.
    Never lower the stop — only raise it.
    """
    new_stop = round(close - ATR_STOP_MULTIPLIER * atr, 2)
    return max(new_stop, current_stop)  # never lower the stop


def _negative_news_signal(ticker: str, news_df: pd.DataFrame) -> bool:
    """Return True if there's high-impact negative news for the ticker."""
    if news_df is None or news_df.empty:
        return False
    ticker_news = news_df[news_df["ticker"] == ticker]
    if ticker_news.empty:
        return False
    return bool(
        ticker_news[
            (ticker_news["impact_level"] == "high") &
            (ticker_news["sentiment_proxy"] < -0.3)
        ].shape[0] > 0
    )


def _fundamental_deterioration(ticker: str, fund_df: pd.DataFrame) -> bool:
    """Return True if fundamental score is critically low (< 0.3)."""
    if fund_df is None or fund_df.empty:
        return False
    rows = fund_df[fund_df["ticker"] == ticker]
    if rows.empty:
        return False
    score = rows.iloc[0].get("fundamental_score", 0.5) or 0.5
    return score < 0.3


def run(
    portfolio: pd.DataFrame,
    technicals: pd.DataFrame,
    news: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Execute the sell engine and return a DataFrame of action recommendations.

    Returns columns:
        ticker, date, action (hold | raise_stop | partial_sell | close),
        new_stop, sell_pct, current_r, rationale
    """
    today = date.today().isoformat()

    if portfolio is None or portfolio.empty:
        print("[sell] No open positions found.")
        return pd.DataFrame()

    actions = []

    for _, pos in portfolio.iterrows():
        ticker = pos["ticker"]
        entry_price = float(pos.get("entry_price", 0))
        initial_stop = float(pos.get("initial_stop", 0))
        current_stop = float(pos.get("current_stop") or pos.get("initial_stop", 0))

        # Get technicals
        tech_rows = technicals[technicals["ticker"] == ticker] if technicals is not None and not technicals.empty else pd.DataFrame()
        has_tech = not tech_rows.empty
        tech = tech_rows.iloc[0] if has_tech else pd.Series()

        atr = float(tech.get("atr14", 0) or 0) if has_tech else 0
        trend = tech.get("trend_state", "unknown") if has_tech else "unknown"
        rsi = float(tech.get("rsi14", 50) or 50) if has_tech else 50
        ma50 = float(tech.get("ma50", 0) or 0) if has_tech else 0

        # Use actual close price from technicals snapshot
        current_price = float(tech.get("close") or tech.get("ma20", entry_price) or entry_price) if has_tech else entry_price

        current_r = _r_multiple(entry_price, current_price, current_stop)
        new_stop = current_stop
        action = "hold"
        sell_pct = 0.0
        rationale_parts = [f"trend={trend}", f"rsi={round(rsi,1)}", f"r={current_r}"]

        # --- Decision logic ---

        # 1. Stop hit — close immediately
        if current_price <= current_stop:
            action = "close"
            sell_pct = 100.0
            rationale_parts.append("STOP HIT")

        # 2. High-impact negative news — close or partial sell
        elif _negative_news_signal(ticker, news):
            action = "partial_sell"
            sell_pct = 50.0
            rationale_parts.append("high-impact negative news")

        # 3. Fundamental deterioration — partial sell
        elif _fundamental_deterioration(ticker, fundamentals):
            action = "partial_sell"
            sell_pct = 50.0
            rationale_parts.append("fundamental deterioration")

        # 4. Trend broken (price below MA50) — close or partial
        elif trend == "downtrend" or (ma50 > 0 and current_price < ma50):
            action = "partial_sell"
            sell_pct = 50.0
            rationale_parts.append("trend broken / below MA50")

        # 5. Strong R multiple reached — take partial profits
        elif current_r is not None and current_r >= MIN_R_MULTIPLE_TARGET * 2:
            action = "partial_sell"
            sell_pct = 33.0
            rationale_parts.append(f"target R={current_r} reached — partial profit")

        # 6. Good trend — raise trailing stop
        elif trend == "uptrend" and atr > 0:
            new_stop = _compute_new_trailing_stop(entry_price, current_stop, atr, current_price)
            if new_stop > current_stop:
                action = "raise_stop"
                rationale_parts.append(f"trail stop: {current_stop} -> {new_stop}")
            else:
                action = "hold"
                rationale_parts.append("uptrend intact, stop already optimal")

        # 7. Default hold
        else:
            action = "hold"
            rationale_parts.append("no actionable signal")

        actions.append({
            "ticker": ticker,
            "date": today,
            "action": action,
            "current_price": round(current_price, 2),
            "entry_price": round(entry_price, 2),
            "current_stop": round(current_stop, 2),
            "new_stop": round(new_stop, 2),
            "sell_pct": sell_pct,
            "current_r": current_r,
            "rationale": " | ".join(rationale_parts),
        })

    if not actions:
        return pd.DataFrame()

    return pd.DataFrame(actions).sort_values("ticker").reset_index(drop=True)
