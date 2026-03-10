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
import plotly.express as px
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
    run_universe = st.button("🔍 Build Universe", use_container_width=True, help="Fetch all NYSE/NASDAQ stocks and filter by market cap + volume")
    run_quarterly = st.button("Run Quarterly Pipeline", use_container_width=True)
    run_weekly = st.button("Run Weekly Pipeline", use_container_width=True)
    run_daily = st.button("Run Daily Pipeline", use_container_width=True)

    if run_universe:
        with st.spinner("Fetching stock universe from NASDAQ screener (this may take ~30s)..."):
            try:
                from jobs.build_universe import run as universe_run
                result = universe_run()
                if result is not None and not result.empty:
                    st.success(f"Universe built: {len(result)} stocks saved. Re-run Quarterly pipeline to fetch fundamentals.")
                    st.rerun()
                else:
                    st.error("Universe build failed — check logs.")
            except Exception as e:
                st.error(f"Error: {e}")

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
# Row 6: Sector Exposure (from today's buy candidates)
# ---------------------------------------------------------------------------

st.subheader("🏭 Sector Exposure")

buy_with_sector = load_csv(BUY_FILE, "buy candidates (sector)")

if not buy_with_sector.empty and "sector" in buy_with_sector.columns:
    col_sec_chart, col_sec_table = st.columns([1, 1])

    sector_counts = buy_with_sector["sector"].value_counts().reset_index()
    sector_counts.columns = ["sector", "candidates"]

    with col_sec_chart:
        fig_sec = go.Figure(go.Pie(
            labels=sector_counts["sector"],
            values=sector_counts["candidates"],
            hole=0.4,
            textinfo="label+percent",
        ))
        fig_sec.update_layout(
            title="Buy candidates by sector",
            showlegend=False,
            margin=dict(t=40, b=0, l=0, r=0),
            height=300,
        )
        st.plotly_chart(fig_sec, use_container_width=True)

    with col_sec_table:
        # Also show portfolio sector exposure if available
        if not portfolio_df.empty and "ticker" in portfolio_df.columns:
            universe_csv = DATA_DIR / "universe_tickers.csv"
            if universe_csv.exists():
                try:
                    uni_df = pd.read_csv(universe_csv, usecols=["ticker", "sector"])
                    port_sectors = portfolio_df.merge(uni_df, on="ticker", how="left")
                    if "sector" in port_sectors.columns and "shares" in port_sectors.columns and "entry_price" in port_sectors.columns:
                        port_sectors["value"] = port_sectors["shares"] * port_sectors["entry_price"]
                        sector_value = port_sectors.groupby("sector")["value"].sum().reset_index()
                        sector_value["pct"] = (sector_value["value"] / sector_value["value"].sum() * 100).round(1)
                        sector_value.columns = ["Sector", "Value ($)", "Exposure (%)"]
                        st.markdown("**Portfolio sector exposure**")
                        st.dataframe(sector_value, use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(sector_counts, use_container_width=True, hide_index=True)
                except Exception:
                    st.dataframe(sector_counts, use_container_width=True, hide_index=True)
            else:
                st.dataframe(sector_counts, use_container_width=True, hide_index=True)
        else:
            st.dataframe(sector_counts, use_container_width=True, hide_index=True)
else:
    empty_state("No sector data yet. Run the daily pipeline (sector requires universe_tickers.csv).")

st.divider()

# ---------------------------------------------------------------------------
# Row 7: Price chart (select a ticker)
# ---------------------------------------------------------------------------

st.subheader("📊 Price Chart")

try:
    from storage.db import init_db
    from storage.price_repository import load_price_bars
    init_db()

    # Build ticker list from buy candidates + portfolio
    chart_tickers = []
    if not buy_df.empty and "ticker" in buy_df.columns:
        chart_tickers.extend(buy_df["ticker"].tolist())
    if not portfolio_df.empty and "ticker" in portfolio_df.columns:
        chart_tickers.extend(portfolio_df["ticker"].tolist())
    # Add index tickers
    chart_tickers.extend(["SPY", "QQQ", "IWM"])
    chart_tickers = sorted(set(chart_tickers))

    if chart_tickers:
        selected_ticker = st.selectbox("Select ticker", chart_tickers, index=0)

        price_history = load_price_bars(tickers=[selected_ticker])
        if not price_history.empty:
            price_history = price_history.sort_values("date")
            # Keep last 6 months
            price_history = price_history.tail(130)

            fig_price = go.Figure()

            # Candlestick chart
            fig_price.add_trace(go.Candlestick(
                x=price_history["date"],
                open=price_history["open"],
                high=price_history["high"],
                low=price_history["low"],
                close=price_history["close"],
                name=selected_ticker,
            ))

            # Add MA20 and MA50 if we can compute them from the data
            if len(price_history) >= 20:
                price_history["ma20"] = price_history["close"].rolling(20).mean()
                fig_price.add_trace(go.Scatter(
                    x=price_history["date"], y=price_history["ma20"],
                    mode="lines", name="MA20",
                    line=dict(color="orange", width=1),
                ))
            if len(price_history) >= 50:
                price_history["ma50"] = price_history["close"].rolling(50).mean()
                fig_price.add_trace(go.Scatter(
                    x=price_history["date"], y=price_history["ma50"],
                    mode="lines", name="MA50",
                    line=dict(color="blue", width=1),
                ))

            # Mark entry price if in portfolio
            if not portfolio_df.empty and selected_ticker in portfolio_df["ticker"].values:
                pos = portfolio_df[portfolio_df["ticker"] == selected_ticker].iloc[0]
                entry_px = pos.get("entry_price")
                stop_px = pos.get("current_stop") or pos.get("initial_stop")
                if entry_px:
                    fig_price.add_hline(y=float(entry_px), line_dash="dash", line_color="green",
                                        annotation_text=f"Entry ${entry_px}")
                if stop_px:
                    fig_price.add_hline(y=float(stop_px), line_dash="dash", line_color="red",
                                        annotation_text=f"Stop ${stop_px}")

            # Mark buy candidate entry/stop/target if applicable
            if not buy_df.empty and selected_ticker in buy_df["ticker"].values:
                cand = buy_df[buy_df["ticker"] == selected_ticker].iloc[0]
                for field, color, label in [
                    ("entry_price", "green", "Entry"),
                    ("stop_price", "red", "Stop"),
                    ("target_price", "blue", "Target"),
                ]:
                    val = cand.get(field)
                    if val:
                        fig_price.add_hline(y=float(val), line_dash="dot", line_color=color,
                                            annotation_text=f"{label} ${val:.2f}")

            fig_price.update_layout(
                title=f"{selected_ticker} — 6 Month Price",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                xaxis_rangeslider_visible=False,
                height=450,
                margin=dict(t=40, b=40, l=60, r=20),
            )
            st.plotly_chart(fig_price, use_container_width=True)
        else:
            empty_state(f"No price data for {selected_ticker}. Run the daily pipeline.")
    else:
        empty_state("No tickers available for charting. Run the daily pipeline.")
except Exception as e:
    empty_state(f"Price chart unavailable: {e}")

st.divider()

# ---------------------------------------------------------------------------
# Row 8: Signal History
# ---------------------------------------------------------------------------

st.subheader("📜 Signal History")

try:
    from storage.db import init_db
    from storage.signal_repository import (
        get_signal_dates,
        load_buy_candidates_for_date,
        load_sell_actions_for_date,
        load_buy_history,
    )
    init_db()

    signal_dates = get_signal_dates(limit=60)

    if signal_dates:
        col_hist_ctrl, col_hist_stats = st.columns([1, 2])

        with col_hist_ctrl:
            history_date = st.selectbox("Signal date", signal_dates, index=0)

        with col_hist_stats:
            # Quick stats for last 30 days
            recent_buys = load_buy_history(days_back=30)
            if not recent_buys.empty:
                n_days = recent_buys["date"].nunique()
                n_signals = len(recent_buys)
                top_tickers = recent_buys["ticker"].value_counts().head(5)
                st.caption(f"Last 30 days: {n_signals} buy signals across {n_days} trading days")
                st.caption(f"Most frequent: {', '.join(top_tickers.index.tolist())}")

        # Show signals for selected date
        col_hist_buy, col_hist_sell = st.columns(2)

        with col_hist_buy:
            st.markdown(f"**Buy candidates — {history_date}**")
            hist_buy = load_buy_candidates_for_date(history_date)
            if not hist_buy.empty:
                display_cols = [c for c in ["ticker", "entry_price", "stop_price", "target_price",
                                             "score", "rationale"] if c in hist_buy.columns]
                st.dataframe(hist_buy[display_cols], use_container_width=True, hide_index=True)
            else:
                st.caption("No buy candidates on this date.")

        with col_hist_sell:
            st.markdown(f"**Sell actions — {history_date}**")
            hist_sell = load_sell_actions_for_date(history_date)
            if not hist_sell.empty:
                display_cols = [c for c in ["ticker", "action", "current_price", "current_stop",
                                             "new_stop", "sell_pct", "current_r", "rationale"]
                                if c in hist_sell.columns]
                st.dataframe(hist_sell[display_cols], use_container_width=True, hide_index=True)
            else:
                st.caption("No sell actions on this date.")
    else:
        empty_state("No signal history yet. Run the daily pipeline to start accumulating history.")

except Exception as e:
    empty_state(f"Signal history unavailable: {e}")

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(
    "StockAnalyst v1.1 · Data via Yahoo Finance · "
    "No automatic execution — all trades are manual."
)
