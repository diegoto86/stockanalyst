"""
dashboard.py
------------
StockAnalyst — Streamlit dashboard.

Run with:
    streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from datetime import date

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="StockAnalyst",
    page_icon="📈",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
BUY_FILE = DATA_DIR / "buy_candidates_daily.csv"
SELL_FILE = DATA_DIR / "sell_actions_daily.csv"
PORTFOLIO_FILE = DATA_DIR / "portfolio" / "portfolio.csv"


def load_csv(path: Path, label: str) -> pd.DataFrame | None:
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            st.warning(f"Could not read {label}: {e}")
    return None


def empty_state(message: str):
    st.info(message)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("StockAnalyst")
    st.caption("Swing Trading Multifactor System")
    st.divider()

    st.subheader("Session")
    selected_date = st.date_input("Analysis date", value=date.today())
    st.divider()

    st.subheader("Filters")
    min_score = st.slider("Min buy score", 0.0, 1.0, 0.5, step=0.05)
    max_risk = st.slider("Max risk %", 0.5, 3.0, 1.0, step=0.25)
    st.divider()

    st.subheader("Pipelines")
    if st.button("Run Daily Pipeline", use_container_width=True):
        st.toast("Daily pipeline triggered — check terminal.", icon="⚙️")
    if st.button("Run Weekly Pipeline", use_container_width=True):
        st.toast("Weekly pipeline triggered — check terminal.", icon="⚙️")

    st.divider()
    st.caption(f"v1.0 baseline — {date.today()}")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📈 StockAnalyst Dashboard")
st.caption(f"End-of-day analysis · {selected_date.strftime('%A, %d %B %Y')}")
st.divider()

# ---------------------------------------------------------------------------
# Row 1: Market context KPIs
# ---------------------------------------------------------------------------

st.subheader("Market Context")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("SPY", "—", help="S&P 500 ETF — updated by daily pipeline")
with col2:
    st.metric("QQQ", "—", help="Nasdaq 100 ETF — updated by daily pipeline")
with col3:
    st.metric("IWM", "—", help="Russell 2000 ETF — updated by daily pipeline")
with col4:
    st.metric("VIX", "—", help="Volatility index — updated by daily pipeline")

st.divider()

# ---------------------------------------------------------------------------
# Row 2: Buy candidates + Sell actions
# ---------------------------------------------------------------------------

col_buy, col_sell = st.columns(2)

# --- Buy candidates ---
with col_buy:
    st.subheader("🟢 Buy Candidates")
    buy_df = load_csv(BUY_FILE, "buy candidates")

    if buy_df is not None and not buy_df.empty:
        # Apply score filter if column exists
        if "score" in buy_df.columns:
            buy_df = buy_df[buy_df["score"] >= min_score]

        st.dataframe(
            buy_df,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(buy_df)} candidate(s) for {selected_date}")
    else:
        empty_state(
            "No buy candidates available yet.\n\n"
            "Run the daily pipeline to generate signals."
        )

# --- Sell actions ---
with col_sell:
    st.subheader("🔴 Sell / Hold Actions")
    sell_df = load_csv(SELL_FILE, "sell actions")

    if sell_df is not None and not sell_df.empty:
        # Color-code action column if present
        if "action" in sell_df.columns:
            action_colors = {
                "close": "🔴",
                "partial_sell": "🟠",
                "raise_stop": "🟡",
                "hold": "🟢",
            }
            sell_df["action"] = sell_df["action"].map(
                lambda x: f"{action_colors.get(x, '')} {x}"
            )
        st.dataframe(
            sell_df,
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{len(sell_df)} position(s) reviewed")
    else:
        empty_state(
            "No sell actions available yet.\n\n"
            "Add positions to portfolio.csv and run the daily pipeline."
        )

st.divider()

# ---------------------------------------------------------------------------
# Row 3: Portfolio positions
# ---------------------------------------------------------------------------

st.subheader("💼 Portfolio Positions")
portfolio_df = load_csv(PORTFOLIO_FILE, "portfolio")

if portfolio_df is not None and not portfolio_df.empty:
    # Compute unrealized P&L columns if we have the needed data
    display_df = portfolio_df.copy()

    col_table, col_chart = st.columns([2, 1])

    with col_table:
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(display_df)} open position(s)")

    with col_chart:
        if "ticker" in display_df.columns and "shares" in display_df.columns and "entry_price" in display_df.columns:
            display_df["position_value"] = display_df["shares"] * display_df["entry_price"]
            fig = go.Figure(go.Pie(
                labels=display_df["ticker"],
                values=display_df["position_value"],
                hole=0.4,
                textinfo="label+percent",
            ))
            fig.update_layout(
                title="Position sizing",
                showlegend=False,
                margin=dict(t=40, b=0, l=0, r=0),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Add entry_price and shares to portfolio.csv to see the chart.")
else:
    empty_state(
        "No portfolio positions found.\n\n"
        "Copy `data/portfolio/portfolio_template.csv` to "
        "`data/portfolio/portfolio.csv` and fill in your positions."
    )

st.divider()

# ---------------------------------------------------------------------------
# Row 4: Watchlist preview
# ---------------------------------------------------------------------------

st.subheader("📋 Watchlist (Weekly Universe)")

watchlist_file = DATA_DIR / "watchlist" / "watchlist_current.csv"
watchlist_df = load_csv(watchlist_file, "watchlist")

if watchlist_df is not None and not watchlist_df.empty:
    st.dataframe(watchlist_df, use_container_width=True, hide_index=True)
else:
    empty_state(
        "No watchlist available yet.\n\n"
        "Run the weekly pipeline to generate the universe."
    )

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(
    "StockAnalyst v1.0 · Data via Yahoo Finance · "
    "No automatic execution — all trades are manual."
)
