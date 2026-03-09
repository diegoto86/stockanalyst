"""
sell_engine.py
--------------
SELL block: manages open positions in the portfolio.

Sequence:
    1. Load portfolio_positions (manual CSV)
    2. Enrich with technical_snapshot_daily
    3. Enrich with news_events_daily
    4. Check fundamentals_snapshot_quarterly for material changes
    5. Emit explicit action plan (hold/raise stop, partial sell, full close)

No automatic execution — user decides and trades manually.
"""

import pandas as pd


def run(
    portfolio: pd.DataFrame,
    technicals: pd.DataFrame,
    news: pd.DataFrame,
    fundamentals: pd.DataFrame,
) -> pd.DataFrame:
    """
    Execute the sell engine and return a DataFrame of action recommendations.

    Returns columns:
        ticker, action (hold | raise_stop | partial_sell | close),
        new_stop, sell_pct, rationale
    """
    raise NotImplementedError("sell_engine.run not implemented yet")
