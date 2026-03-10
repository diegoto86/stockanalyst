"""
Dashboard sections: market context, signals, portfolio, watchlist,
earnings, sectors, price charts, signal history, performance.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

from dashboard_sections.helpers import (
    load_csv, empty_state, color_action,
    DATA_DIR, BUY_FILE, SELL_FILE, PORTFOLIO_FILE, MARKET_CTX_FILE, EARNINGS_FILE,
)


# ---------------------------------------------------------------------------
# Market Context
# ---------------------------------------------------------------------------

def render_market_context():
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
# Buy / Sell Signals
# ---------------------------------------------------------------------------

def render_signals(min_score: float, selected_date=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Render buy candidates and sell actions. Returns (buy_df, sell_df).

    If selected_date is today (or None), loads from CSV.
    If selected_date is a past date, loads from DB.
    """
    from datetime import date as date_type

    is_today = (selected_date is None or selected_date == date_type.today())
    date_label = selected_date.isoformat() if selected_date else date_type.today().isoformat()

    col_buy, col_sell = st.columns(2)

    # --- Load data ---
    if is_today:
        buy_df = load_csv(BUY_FILE, "buy candidates")
        sell_df = load_csv(SELL_FILE, "sell actions")
    else:
        try:
            from storage.db import init_db
            from storage.signal_repository import load_buy_candidates_for_date, load_sell_actions_for_date
            init_db()
            buy_df = load_buy_candidates_for_date(date_label)
            sell_df = load_sell_actions_for_date(date_label)
        except Exception:
            buy_df = pd.DataFrame()
            sell_df = pd.DataFrame()

    with col_buy:
        st.subheader("Buy Candidates")
        if not buy_df.empty:
            if "score" in buy_df.columns:
                buy_df = buy_df[buy_df["score"] >= min_score]

            display_cols = [c for c in ["ticker", "entry_price", "stop_price", "target_price",
                                         "shares", "r_multiple_target", "score", "rationale"]
                            if c in buy_df.columns]
            st.dataframe(buy_df[display_cols], width="stretch", hide_index=True)
            st.caption(f"{len(buy_df)} candidate(s) · {date_label}")
        else:
            if is_today:
                empty_state("No buy candidates yet.\nRun the daily pipeline to generate signals.")
            else:
                empty_state(f"No buy candidates for {date_label}.")

    with col_sell:
        st.subheader("Sell / Hold Actions")
        if not sell_df.empty:
            display_cols = [c for c in ["ticker", "action", "current_price", "current_stop",
                                         "new_stop", "sell_pct", "current_r", "rationale"]
                            if c in sell_df.columns]
            if "action" in sell_df.columns:
                styled = sell_df[display_cols].style.map(color_action, subset=["action"])
                st.dataframe(styled, width="stretch", hide_index=True)
            else:
                st.dataframe(sell_df[display_cols], width="stretch", hide_index=True)
            st.caption(f"{len(sell_df)} position(s) reviewed · {date_label}")
        else:
            if is_today:
                empty_state("No sell actions yet.\nAdd positions to portfolio.csv and run daily pipeline.")
            else:
                empty_state(f"No sell actions for {date_label}.")

    st.divider()
    return buy_df, sell_df


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

def render_portfolio() -> pd.DataFrame:
    """Render portfolio positions. Returns portfolio_df."""
    st.subheader("Portfolio Positions")
    portfolio_df = load_csv(PORTFOLIO_FILE, "portfolio")

    if not portfolio_df.empty:
        col_table, col_chart = st.columns([2, 1])

        with col_table:
            st.dataframe(portfolio_df, width="stretch", hide_index=True)
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
                st.plotly_chart(fig, width="stretch")
    else:
        empty_state(
            "No open positions found.\n\n"
            "Copy `data/portfolio/portfolio_template.csv` -> `data/portfolio/portfolio.csv` "
            "and add your positions."
        )

    st.divider()
    return portfolio_df


# ---------------------------------------------------------------------------
# Watchlist + Earnings
# ---------------------------------------------------------------------------

def render_watchlist():
    st.subheader("Weekly Watchlist")
    try:
        from storage.db import init_db
        from storage.watchlist_repository import load_watchlist
        init_db()
        watchlist_df = load_watchlist()
        if not watchlist_df.empty:
            display_cols = [c for c in ["ticker", "score", "liquidity_ok", "size_ok",
                                         "quality_ok", "valuation_ok"] if c in watchlist_df.columns]
            st.dataframe(watchlist_df[display_cols].sort_values("score", ascending=False),
                         width="stretch", hide_index=True)
            st.caption(f"{len(watchlist_df)} tickers in this week's universe")
        else:
            empty_state("No watchlist yet. Run the weekly pipeline.")
    except Exception:
        empty_state("No watchlist yet. Run the weekly pipeline.")
    st.divider()


def render_earnings():
    st.subheader("Upcoming Earnings")
    earnings_df = load_csv(EARNINGS_FILE, "earnings calendar")
    if not earnings_df.empty:
        st.dataframe(earnings_df.sort_values("earnings_date"), width="stretch", hide_index=True)
    else:
        empty_state("No earnings data yet. Run the daily pipeline.")
    st.divider()


# ---------------------------------------------------------------------------
# Sector Exposure
# ---------------------------------------------------------------------------

def render_sector_exposure(portfolio_df: pd.DataFrame):
    st.subheader("Sector Exposure")
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
            st.plotly_chart(fig_sec, width="stretch")

        with col_sec_table:
            if not portfolio_df.empty and "ticker" in portfolio_df.columns:
                universe_csv = DATA_DIR / "universe_tickers.csv"
                if universe_csv.exists():
                    try:
                        uni_df = pd.read_csv(universe_csv, usecols=["ticker", "sector"])
                        port_sectors = portfolio_df.merge(uni_df, on="ticker", how="left")
                        if all(c in port_sectors.columns for c in ["sector", "shares", "entry_price"]):
                            port_sectors["value"] = port_sectors["shares"] * port_sectors["entry_price"]
                            sector_value = port_sectors.groupby("sector")["value"].sum().reset_index()
                            sector_value["pct"] = (sector_value["value"] / sector_value["value"].sum() * 100).round(1)
                            sector_value.columns = ["Sector", "Value ($)", "Exposure (%)"]
                            st.markdown("**Portfolio sector exposure**")
                            st.dataframe(sector_value, width="stretch", hide_index=True)
                        else:
                            st.dataframe(sector_counts, width="stretch", hide_index=True)
                    except Exception:
                        st.dataframe(sector_counts, width="stretch", hide_index=True)
                else:
                    st.dataframe(sector_counts, width="stretch", hide_index=True)
            else:
                st.dataframe(sector_counts, width="stretch", hide_index=True)
    else:
        empty_state("No sector data yet. Run the daily pipeline (sector requires universe_tickers.csv).")

    st.divider()


# ---------------------------------------------------------------------------
# Price Chart
# ---------------------------------------------------------------------------

def render_price_chart(buy_df: pd.DataFrame, portfolio_df: pd.DataFrame):
    st.subheader("Price Chart")
    try:
        from storage.db import init_db
        from storage.price_repository import load_price_bars
        init_db()

        chart_tickers = []
        if not buy_df.empty and "ticker" in buy_df.columns:
            chart_tickers.extend(buy_df["ticker"].tolist())
        if not portfolio_df.empty and "ticker" in portfolio_df.columns:
            chart_tickers.extend(portfolio_df["ticker"].tolist())
        chart_tickers.extend(["SPY", "QQQ", "IWM"])
        chart_tickers = sorted(set(chart_tickers))

        if chart_tickers:
            selected_ticker = st.selectbox("Select ticker", chart_tickers, index=0)

            price_history = load_price_bars(tickers=[selected_ticker])
            if not price_history.empty:
                price_history = price_history.sort_values("date").tail(130)

                fig_price = go.Figure()
                fig_price.add_trace(go.Candlestick(
                    x=price_history["date"],
                    open=price_history["open"],
                    high=price_history["high"],
                    low=price_history["low"],
                    close=price_history["close"],
                    name=selected_ticker,
                ))

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
                st.plotly_chart(fig_price, width="stretch")
            else:
                empty_state(f"No price data for {selected_ticker}. Run the daily pipeline.")
        else:
            empty_state("No tickers available for charting. Run the daily pipeline.")
    except Exception as e:
        empty_state(f"Price chart unavailable: {e}")

    st.divider()


# ---------------------------------------------------------------------------
# Signal History
# ---------------------------------------------------------------------------

def render_signal_history():
    st.subheader("Signal History")
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
                recent_buys = load_buy_history(days_back=30)
                if not recent_buys.empty:
                    n_days = recent_buys["date"].nunique()
                    n_signals = len(recent_buys)
                    top_tickers = recent_buys["ticker"].value_counts().head(5)
                    st.caption(f"Last 30 days: {n_signals} buy signals across {n_days} trading days")
                    st.caption(f"Most frequent: {', '.join(top_tickers.index.tolist())}")

            col_hist_buy, col_hist_sell = st.columns(2)

            with col_hist_buy:
                st.markdown(f"**Buy candidates — {history_date}**")
                hist_buy = load_buy_candidates_for_date(history_date)
                if not hist_buy.empty:
                    display_cols = [c for c in ["ticker", "entry_price", "stop_price", "target_price",
                                                 "score", "rationale"] if c in hist_buy.columns]
                    st.dataframe(hist_buy[display_cols], width="stretch", hide_index=True)
                else:
                    st.caption("No buy candidates on this date.")

            with col_hist_sell:
                st.markdown(f"**Sell actions — {history_date}**")
                hist_sell = load_sell_actions_for_date(history_date)
                if not hist_sell.empty:
                    display_cols = [c for c in ["ticker", "action", "current_price", "current_stop",
                                                 "new_stop", "sell_pct", "current_r", "rationale"]
                                    if c in hist_sell.columns]
                    st.dataframe(hist_sell[display_cols], width="stretch", hide_index=True)
                else:
                    st.caption("No sell actions on this date.")
        else:
            empty_state("No signal history yet. Run the daily pipeline to start accumulating history.")

    except Exception as e:
        empty_state(f"Signal history unavailable: {e}")

    st.divider()


# ---------------------------------------------------------------------------
# Signal Performance (NEW)
# ---------------------------------------------------------------------------

def render_performance():
    st.subheader("Signal Performance")
    try:
        from storage.db import init_db
        from engines.signal_evaluator import get_performance_summary, load_outcomes
        init_db()

        summary = get_performance_summary()
        if summary:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Signals Evaluated", summary["total_signals"])
            col2.metric("Win Rate", f"{summary['win_rate']}%")
            col3.metric("Avg Return", f"{summary['avg_return']}%")
            col4.metric("Expectancy", f"{summary['expectancy']}%")
            col5.metric("Max Drawdown", f"{summary['max_drawdown']}%")

            col_a, col_b = st.columns(2)
            with col_a:
                st.caption(f"Avg winner: {summary['avg_winner']}% | Avg loser: {summary['avg_loser']}%")
                st.caption(f"Hit target: {summary['hit_target_rate']}% | Hit stop: {summary['hit_stop_rate']}%")
            with col_b:
                st.caption(f"Avg days held: {summary['avg_days_held']}")

            outcomes_df = load_outcomes(days_back=30)
            if not outcomes_df.empty:
                display_cols = [c for c in ["ticker", "signal_date", "entry_price", "price_at_eval",
                                             "return_pct", "hit_target", "hit_stop", "max_gain_pct",
                                             "max_drawdown_pct", "days_held"]
                                if c in outcomes_df.columns]
                st.dataframe(outcomes_df[display_cols], width="stretch", hide_index=True)
        else:
            empty_state("No performance data yet. Run the daily pipeline to evaluate past signals.")
    except Exception as e:
        empty_state(f"Performance data unavailable: {e}")

    st.divider()
