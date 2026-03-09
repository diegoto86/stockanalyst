"""
dependency_graph.py
-------------------
Documents the logical dependencies between datasets and engines.
Used as reference and for future automated orchestration.
"""

DEPENDENCIES = {
    "buy_engine": [
        "market_context_daily",
        "universe_watchlist_weekly",
        "technical_snapshot_daily",
        "news_events_daily",
        "fundamentals_snapshot_quarterly",
    ],
    "sell_engine": [
        "portfolio_positions",
        "technical_snapshot_daily",
        "news_events_daily",
        "fundamentals_snapshot_quarterly",
    ],
    "technical_snapshot_daily": ["price_bars_daily"],
    "universe_watchlist_weekly": ["fundamentals_snapshot_quarterly", "price_bars_daily"],
    "market_context_daily": ["price_bars_daily"],
}


def get_dependencies(component: str) -> list:
    """Return the list of datasets that a given component depends on."""
    return DEPENDENCIES.get(component, [])
