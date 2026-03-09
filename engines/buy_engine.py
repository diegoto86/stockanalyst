"""
buy_engine.py
-------------
BUY block: scans for new trade opportunities.

Sequence:
    1. Load universe_watchlist_weekly (pre-filtered universe)
    2. Cross with technical_snapshot_daily (trend + pullback + trigger)
    3. Cross with news_events_daily (exclude or reduce aggression)
    4. Calculate entry, stop, targets and position size
    5. Output buy_candidates_daily
"""

import pandas as pd


def run(
    watchlist: pd.DataFrame,
    technicals: pd.DataFrame,
    news: pd.DataFrame,
    fundamentals: pd.DataFrame,
    market_context: dict,
    portfolio: pd.DataFrame,
    max_positions: int = 10,
    max_risk_per_trade: float = 0.01,
) -> pd.DataFrame:
    """
    Execute the buy engine and return a DataFrame of buy candidates.

    Returns columns:
        ticker, entry_price, stop_price, target_price,
        shares, risk_pct, r_multiple_target, rationale
    """
    raise NotImplementedError("buy_engine.run not implemented yet")
