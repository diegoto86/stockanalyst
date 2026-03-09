"""
dashboard.py
------------
StockAnalyst — Streamlit dashboard.

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
import pandas as pd
import plotly.graph_objects as go
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
    min_score = st.slider("Min buy score", 0.0, 1.0, 0.3, step=0.05)
    st.divider()

    st.subheader("Run Pipelines")
    run_quarterly = st.button("Run Quarterly Pipeline", use_container_width=True)
    run_weekly = st.button("Run Weekly Pipeline", use_container_width=True)
    run_daily = st.button("Run Daily Pipeline", use_container_width=True)

    if run_quarterly:
        with st.spinner("Running quarterly pipeline..."):
            try:
                from jobs.run_quarterly import run as quarterly_run
                quarterly_run()
                st.success("Quarterly pipeline complete.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if run_weekly:
        with st.spinner("Running weekly pipeline..."):
            try:
                from jobs.run_weekly import run as weekly_run
                weekly_run(force=True)
                st.success("Weekly pipeline complete.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if run_daily:
        with st.spinner("Running daily pipeline (this may take a few minutes)..."):
            try:
                from jobs.run_daily import run as daily_run
                daily_run()
                st.success("Daily pipeline complete.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    st.divider()

    # Data freshness status
    st.subheader("Data Status")
    try:
        from orchestration.freshness import dataset_status
        from storage.db import init_db
        init_db()
        status = dataset_status()
        for ds, stale in status.items():
            icon = "🔴" if stale else "🟢"
            st.caption(f"{icon} {ds.replace('_', ' ')}")
    except Exception:
        st.caption("Run a pipeline to see data status.")

    st.divider()
    st.caption(f"v1.0 · {date.today()}")

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

market_df = load_csv(MARKET_CTX_FILE, "market context")

if not market_df.empty:
    col1, col2, col3, col4 = st.columns(4)
    index_map = {"SPY": col1, "QQQ": col2, "IWM": col3, "^VIX": col4}

    for sym, col in index_map.items():
        rows = market_df[market_df["ticker"] == sym]
        if not rows.empty:
            row = rows.iloc[0]
            close = round(float(row.get("close", 0)), 2)
            chg = round(float(row.get("change_pct", 0)), 2)
            label = sym.replace("^", "")
            col.metric(label, f"${close:,.2f}" if sym != "^VIX" else f"{close:.2f}", f"{chg:+.2f}%")
        else:
            index_map[sym].metric(sym.replace("^", ""), "—")
else:
    col1, col2, col3, col4 = st.columns(4)
    for col, label in zip([col1, col2, col3, col4], ["SPY", "QQQ", "IWM", "VIX"]):
        col.metric(label, "—", help="Run daily pipeline to populate")

st.divider()

# ---------------------------------------------------------------------------
# Row 2: Buy candidates + Sell actions
# ---------------------------------------------------------------------------

col_buy, col_sell = st.columns(2)

# --- Buy candidates ---
with col_buy:
    st.subheader("🟢 Buy Candidates")
    buy_df = load_csv(BUY_FILE, "buy candidates")

    if not buy_df.empty:
        if "score" in buy_df.columns:
            buy_df = buy_df[buy_df["score"] >= min_score]

        display_cols = [c for c in ["ticker", "entry_price", "stop_price", "target_price",
                                     "shares", "r_multiple_target", "score", "rationale"]
                        if c in buy_df.columns]
        st.dataframe(buy_df[display_cols], use_container_width=True, hide_index=True)
        st.caption(f"{len(buy_df)} candidate(s) · {selected_date}")
    else:
        empty_state("No buy candidates yet.\nRun the daily pipeline to generate signals.")

# --- Sell actions ---
with col_sell:
    st.subheader("🔴 Sell / Hold Actions")
    sell_df = load_csv(SELL_FILE, "sell actions")

    if not sell_df.empty:
        display_cols = [c for c in ["ticker", "action", "current_price", "current_stop",
                                     "new_stop", "sell_pct", "current_r", "rationale"]
                        if c in sell_df.columns]
        if "action" in sell_df.columns:
            styled = sell_df[display_cols].style.map(color_action, subset=["action"])
            st.dataframe(styled, use_container_width=True, hide_index=True)
        else:
            st.dataframe(sell_df[display_cols], use_container_width=True, hide_index=True)
        st.caption(f"{len(sell_df)} position(s) reviewed")
    else:
        empty_state("No sell actions yet.\nAdd positions to portfolio.csv and run daily pipeline.")

st.divider()

# ---------------------------------------------------------------------------
# Row 3: Portfolio positions
# ---------------------------------------------------------------------------

st.subheader("💼 Portfolio Positions")
portfolio_df = load_csv(PORTFOLIO_FILE, "portfolio")

if not portfolio_df.empty:
    col_table, col_chart = st.columns([2, 1])

    with col_table:
        st.dataframe(portfolio_df, use_container_width=True, hide_index=True)
        st.caption(f"{len(portfolio_df)} open position(s)")

    with col_chart:
        if all(c in portfolio_df.columns for c in ["ticker", "shares", "entry_price"]):
            portfolio_df["position_value"] = portfolio_df["shares"] * portfolio_df["entry_price"]
            fig = go.Figure(go.Pie(
                labels=portfolio_df["ticker"],
                values=portfolio_df["position_value"],
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
    empty_state(
        "No open positions found.\n\n"
        "Copy `data/portfolio/portfolio_template.csv` → `data/portfolio/portfolio.csv` "
        "and add your positions."
    )

st.divider()

# ---------------------------------------------------------------------------
# Row 4: Watchlist
# ---------------------------------------------------------------------------

st.subheader("📋 Weekly Watchlist")

try:
    from storage.db import init_db
    from storage.watchlist_repository import load_watchlist
    init_db()
    watchlist_df = load_watchlist()
    if not watchlist_df.empty:
        display_cols = [c for c in ["ticker", "score", "liquidity_ok", "size_ok",
                                     "quality_ok", "valuation_ok"] if c in watchlist_df.columns]
        st.dataframe(watchlist_df[display_cols].sort_values("score", ascending=False),
                     use_container_width=True, hide_index=True)
        st.caption(f"{len(watchlist_df)} tickers in this week's universe")
    else:
        empty_state("No watchlist yet. Run the weekly pipeline.")
except Exception:
    empty_state("No watchlist yet. Run the weekly pipeline.")

st.divider()

# ---------------------------------------------------------------------------
# Row 5: Upcoming earnings
# ---------------------------------------------------------------------------

st.subheader("📅 Upcoming Earnings")
earnings_df = load_csv(EARNINGS_FILE, "earnings calendar")

if not earnings_df.empty:
    st.dataframe(earnings_df.sort_values("earnings_date"), use_container_width=True, hide_index=True)
else:
    empty_state("No earnings data yet. Run the daily pipeline.")

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(
    "StockAnalyst v1.0 · Data via Yahoo Finance · "
    "No automatic execution — all trades are manual."
)
