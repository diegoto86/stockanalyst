"""
dashboard.py
------------
StockAnalyst - Streamlit dashboard.

Run with:
    streamlit run dashboard.py
"""

import os
import sys
from pathlib import Path

# Ensure working directory and sys.path are set to project root
# (needed for Streamlit Cloud where cwd may differ)
PROJECT_ROOT = Path(__file__).parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="StockAnalyst",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Sidebar (returns user config: selected_date, min_score)
# ---------------------------------------------------------------------------

from dashboard_sections.sidebar import render_sidebar

config = render_sidebar()

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------

from dashboard_sections.sections import (
    render_earnings,
    render_market_context,
    render_performance,
    render_portfolio,
    render_price_chart,
    render_sector_exposure,
    render_signal_history,
    render_signals,
    render_watchlist,
)

st.title("StockAnalyst Dashboard")
st.caption(f"End-of-day analysis | {config['selected_date'].strftime('%A, %d %B %Y')}")
st.divider()

render_market_context()
buy_df, sell_df = render_signals(config["min_score"], config["selected_date"])
portfolio_df = render_portfolio()
render_watchlist()
render_earnings()
render_sector_exposure(portfolio_df)
render_price_chart(buy_df, portfolio_df)
render_signal_history()
render_performance()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(
    "StockAnalyst v1.2 | Data via Yahoo Finance | "
    "No automatic execution - all trades are manual."
)
