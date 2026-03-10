"""
Dashboard sidebar: session controls, pipeline buttons, data status.
"""

import streamlit as st
from datetime import date


def render_sidebar() -> dict:
    """
    Render the sidebar and return a config dict with user selections.

    Returns:
        dict with keys: selected_date, min_score
    """
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
        run_universe = st.button("Build Universe", use_container_width=True,
                                 help="Fetch all NYSE/NASDAQ stocks and filter by market cap + volume")
        run_quarterly = st.button("Run Quarterly Pipeline", use_container_width=True)
        run_weekly = st.button("Run Weekly Pipeline", use_container_width=True)
        run_daily = st.button("Run Daily Pipeline", use_container_width=True)

        if run_universe:
            with st.spinner("Fetching stock universe from NASDAQ screener..."):
                try:
                    from jobs.build_universe import run as universe_run
                    result = universe_run()
                    if result is not None and not result.empty:
                        st.success(f"Universe built: {len(result)} stocks saved.")
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
        st.caption(f"v1.2 · {date.today()}")

    return {
        "selected_date": selected_date,
        "min_score": min_score,
    }
