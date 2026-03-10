"""
Dashboard helpers: CSV loader, path constants, styling utilities.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
BUY_FILE = DATA_DIR / "buy_candidates_daily.csv"
SELL_FILE = DATA_DIR / "sell_actions_daily.csv"
PORTFOLIO_FILE = DATA_DIR / "portfolio" / "portfolio.csv"
MARKET_CTX_FILE = DATA_DIR / "market_context.csv"
EARNINGS_FILE = DATA_DIR / "earnings_calendar.csv"


def load_csv(path: Path, label: str) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.warning(f"Could not read {label}: {e}")
    return pd.DataFrame()


def empty_state(message: str):
    st.info(message)


def color_action(val):
    colors = {
        "close": "background-color: #ff4b4b; color: white",
        "partial_sell": "background-color: #ffa500; color: white",
        "raise_stop": "background-color: #ffd700; color: black",
        "hold": "background-color: #21c354; color: white",
    }
    return colors.get(val, "")
