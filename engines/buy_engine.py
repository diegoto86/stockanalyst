"""
buy_engine.py
-------------
BUY block: scans for new trade opportunities.

Sequence:
    1. Use universe_watchlist_weekly (pre-filtered universe)
    2. Cross with technical_snapshot_daily (trend + pullback + trigger)
    3. Cross with news_events_daily (exclude or reduce aggression on bad news)
    4. Calculate entry, stop, targets and position size
    5. Output buy_candidates_daily
"""

import pandas as pd
import numpy as np
from datetime import date
from config import (
    ACCOUNT_SIZE,
    MAX_POSITIONS,
    MAX_RISK_PER_TRADE,
    MAX_SECTOR_EXPOSURE,
    ATR_STOP_MULTIPLIER,
    MIN_R_MULTIPLE_TARGET,
    RSI_OVERBOUGHT,
    PULLBACK_MAX_PCT,
)


def _score_setup(tech_row: pd.Series, fund_row: pd.Series | None) -> dict:
    """
    Compute a 0-1 setup score with explicit subscores for transparency.

    Returns dict with 'total' and individual subscores.

    Subscores (continuous, not binary):
        pullback  (0-0.15): sweet spot 3-8% pullback scores highest
        rsi       (0-0.15): lower RSI (more reset) scores higher
        ma_align  (0-0.20): above MA50 + above MA200, bonus for proximity
        trend     (0-0.10): uptrend > mixed > other
        fundament (0-0.30): fundamental_score scaled
        news      (0-0.10): applied externally via news_penalty
    """
    subscores = {}

    # --- Pullback quality (0-0.15) ---
    # Sweet spot: 3-8% pullback. Too shallow = chasing, too deep = broken.
    pullback = tech_row.get("pullback_pct")
    if pullback is not None and not np.isnan(pullback):
        if 0.03 <= pullback <= 0.08:
            subscores["pullback"] = 0.15  # ideal zone
        elif 0 < pullback < 0.03:
            subscores["pullback"] = round(0.15 * (pullback / 0.03), 3)  # shallow
        elif 0.08 < pullback <= PULLBACK_MAX_PCT:
            # Linear decay from 0.15 to 0.05
            ratio = (pullback - 0.08) / (PULLBACK_MAX_PCT - 0.08)
            subscores["pullback"] = round(0.15 - ratio * 0.10, 3)
        else:
            subscores["pullback"] = 0.0
    else:
        subscores["pullback"] = 0.0

    # --- RSI quality (0-0.15) ---
    # Lower RSI = more reset = better entry. Scale: 30->0.15, 55->0.05, 70->0.0
    rsi = tech_row.get("rsi14")
    if rsi is not None and not np.isnan(rsi):
        if rsi <= 30:
            subscores["rsi"] = 0.15
        elif rsi < 55:
            subscores["rsi"] = round(0.15 * (55 - rsi) / 25, 3)
        else:
            subscores["rsi"] = 0.0
    else:
        subscores["rsi"] = 0.0

    # --- MA alignment (0-0.20) ---
    close = tech_row.get("close")
    ma50 = tech_row.get("ma50")
    ma200 = tech_row.get("ma200")

    ma_score = 0.0
    if close and ma50 and not np.isnan(ma50) and ma50 > 0:
        if close > ma50:
            # Base 0.08, bonus up to 0.02 for being close to MA50 (support nearby)
            dist_pct = (close - ma50) / ma50
            proximity_bonus = max(0, 0.02 - dist_pct * 0.1)
            ma_score += 0.08 + round(proximity_bonus, 3)
    if close and ma200 and not np.isnan(ma200) and ma200 > 0:
        if close > ma200:
            ma_score += 0.10
    subscores["ma_align"] = round(min(ma_score, 0.20), 3)

    # --- Trend (0-0.10) ---
    trend = tech_row.get("trend_state", "")
    if trend == "uptrend":
        subscores["trend"] = 0.10
    elif trend == "mixed":
        subscores["trend"] = 0.05
    else:
        subscores["trend"] = 0.0

    # --- Fundamental (0-0.30) ---
    if fund_row is not None and not fund_row.empty:
        fs = fund_row.get("fundamental_score", 0) or 0
        subscores["fundament"] = round(float(fs) * 0.30, 3)
    else:
        subscores["fundament"] = 0.0

    # News subscore (0-0.10) is applied externally
    subscores["news"] = 0.10  # full value; reduced by news_penalty multiplier later

    total = sum(subscores.values())
    subscores["total"] = round(min(total, 1.0), 3)
    return subscores


def _compute_position_size(
    entry: float,
    stop: float,
    account_size: float,
    risk_pct: float,
) -> int:
    """Return number of shares to buy given a risk budget."""
    risk_per_share = entry - stop
    if risk_per_share <= 0:
        return 0
    dollar_risk = account_size * risk_pct
    shares = int(dollar_risk / risk_per_share)
    return max(shares, 0)


def _news_penalty(ticker: str, news_df: pd.DataFrame) -> float:
    """
    Return a penalty multiplier [0-1] based on recent negative news.
    1.0 = no penalty, 0.0 = skip entirely.
    """
    if news_df is None or news_df.empty:
        return 1.0

    ticker_news = news_df[news_df["ticker"] == ticker]
    if ticker_news.empty:
        return 1.0

    high_impact_neg = ticker_news[
        (ticker_news["impact_level"] == "high") &
        (ticker_news["sentiment_proxy"] < -0.3)
    ]
    if not high_impact_neg.empty:
        return 0.0  # skip this ticker

    avg_sentiment = ticker_news["sentiment_proxy"].mean()
    if avg_sentiment < -0.2:
        return 0.5  # reduce confidence

    return 1.0


def _has_earnings_soon(ticker: str, earnings_df: pd.DataFrame, days: int = 7) -> bool:
    """Return True if ticker has earnings within next `days` days."""
    if earnings_df is None or earnings_df.empty:
        return False
    today = date.today().isoformat()
    upcoming = earnings_df[
        (earnings_df["ticker"] == ticker) &
        (earnings_df["earnings_date"] >= today)
    ]
    if upcoming.empty:
        return False
    nearest = upcoming["earnings_date"].min()
    delta = (pd.Timestamp(nearest) - pd.Timestamp(today)).days
    return delta <= days


def _enforce_sector_exposure(
    candidates: pd.DataFrame,
    portfolio: pd.DataFrame,
    sector_map: dict,
    max_exposure: float,
    max_positions: int,
) -> pd.DataFrame:
    """
    Filter candidates so no single sector exceeds max_exposure of total slots.
    Considers both existing portfolio positions and new candidates.
    """
    if candidates.empty or not sector_map:
        return candidates

    max_per_sector = max(1, int(max_positions * max_exposure))

    # Count existing portfolio positions per sector
    sector_counts = {}
    if portfolio is not None and not portfolio.empty:
        for _, pos in portfolio.iterrows():
            sec = sector_map.get(pos["ticker"], "Unknown")
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

    # Filter candidates respecting sector limits
    kept = []
    for _, row in candidates.iterrows():
        sec = sector_map.get(row["ticker"], "Unknown")
        current = sector_counts.get(sec, 0)
        if current < max_per_sector:
            kept.append(row)
            sector_counts[sec] = current + 1

    if not kept:
        return pd.DataFrame()
    return pd.DataFrame(kept).reset_index(drop=True)


def run(
    watchlist: pd.DataFrame,
    technicals: pd.DataFrame,
    news: pd.DataFrame,
    fundamentals: pd.DataFrame,
    market_context: dict,
    portfolio: pd.DataFrame,
    earnings_calendar: pd.DataFrame = None,
    sector_map: dict = None,
    account_size: float = ACCOUNT_SIZE,
    max_positions: int = MAX_POSITIONS,
    max_risk_per_trade: float = MAX_RISK_PER_TRADE,
) -> pd.DataFrame:
    """
    Execute the buy engine and return a DataFrame of buy candidates.

    Returns columns:
        ticker, date, entry_price, stop_price, target_price,
        shares, risk_pct, r_multiple_target, score, rationale
    """
    today = date.today().isoformat()
    candidates = []

    if watchlist is None or watchlist.empty:
        print("[buy] No watchlist available — skipping.")
        return pd.DataFrame()

    if technicals is None or technicals.empty:
        print("[buy] No technicals available — skipping.")
        return pd.DataFrame()

    # Count current open positions
    current_positions = set(portfolio["ticker"].tolist()) if portfolio is not None and not portfolio.empty else set()
    available_slots = max_positions - len(current_positions)

    if available_slots <= 0:
        print(f"[buy] Portfolio full ({max_positions} positions). No new entries.")
        return pd.DataFrame()

    # Context filter: skip if market is in downtrend (SPY context)
    spy_trend = market_context.get("spy_trend", "unknown")
    if spy_trend == "downtrend":
        print("[buy] Market context is downtrend — skipping buy scan.")
        return pd.DataFrame()

    # Build fundamental lookup
    fund_lookup = {}
    if fundamentals is not None and not fundamentals.empty:
        for _, row in fundamentals.iterrows():
            fund_lookup[row["ticker"]] = row

    # Iterate over watchlist
    for _, w_row in watchlist.iterrows():
        ticker = w_row["ticker"]

        # Skip tickers already in portfolio
        if ticker in current_positions:
            continue

        # Get technicals for this ticker
        tech_rows = technicals[technicals["ticker"] == ticker]
        if tech_rows.empty:
            continue
        tech = tech_rows.iloc[0]

        # Minimum technical requirements
        trend = tech.get("trend_state", "")
        if trend not in ("uptrend", "mixed"):
            continue

        rsi = tech.get("rsi14")
        if rsi is not None and rsi > RSI_OVERBOUGHT:
            continue  # overbought — wait for reset

        pullback = tech.get("pullback_pct")
        if pullback is None or pullback > PULLBACK_MAX_PCT:
            continue  # too extended or no pullback

        # News filter
        news_penalty = _news_penalty(ticker, news)
        if news_penalty == 0.0:
            continue  # skip on high-impact negative news

        # Earnings filter — avoid entering within 7 days of earnings
        if _has_earnings_soon(ticker, earnings_calendar, days=7):
            continue

        # Entry, stop, target
        atr = tech.get("atr14")
        if atr is None or atr <= 0:
            continue

        # Use last close as entry proxy (user confirms entry)
        close = tech.get("close")
        ma50 = tech.get("ma50")
        if close is None or ma50 is None:
            continue

        entry_price = round(float(close), 2)
        stop_price = round(entry_price - ATR_STOP_MULTIPLIER * atr, 2)
        target_price = round(entry_price + MIN_R_MULTIPLE_TARGET * ATR_STOP_MULTIPLIER * atr, 2)

        if stop_price >= entry_price:
            continue

        r_multiple = round((target_price - entry_price) / (entry_price - stop_price), 2)
        if r_multiple < MIN_R_MULTIPLE_TARGET:
            continue

        shares = _compute_position_size(entry_price, stop_price, account_size, max_risk_per_trade)
        if shares == 0:
            continue

        # Score (returns dict with subscores)
        fund_row = fund_lookup.get(ticker)
        subscores = _score_setup(tech, pd.Series(fund_row) if isinstance(fund_row, dict) else fund_row)

        # Apply news penalty to the news subscore
        subscores["news"] = round(subscores["news"] * news_penalty, 3)
        setup_score = round(min(sum(v for k, v in subscores.items() if k != "total"), 1.0), 3)

        # Build rationale with subscore breakdown
        flags = tech.get("setup_flags", "")
        subscore_str = " ".join(f"{k}={v}" for k, v in subscores.items() if k != "total")
        rationale_parts = [
            f"trend={trend}",
            f"rsi={round(rsi, 1) if rsi else 'n/a'}",
            f"pullback={round(pullback*100,1)}%",
            f"score=[{subscore_str}]",
        ]

        candidates.append({
            "ticker": ticker,
            "date": today,
            "entry_price": entry_price,
            "stop_price": stop_price,
            "target_price": target_price,
            "shares": shares,
            "risk_pct": round(max_risk_per_trade * 100, 2),
            "r_multiple_target": r_multiple,
            "score": setup_score,
            "rationale": " | ".join(rationale_parts),
        })

    if not candidates:
        return pd.DataFrame()

    result = pd.DataFrame(candidates)
    result = result.sort_values("score", ascending=False).head(available_slots)
    result = result.reset_index(drop=True)

    # Enforce sector exposure limits
    if sector_map:
        result = _enforce_sector_exposure(
            result, portfolio, sector_map, MAX_SECTOR_EXPOSURE, max_positions,
        )

    return result
