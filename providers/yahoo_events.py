"""
yahoo_events.py
---------------
Fetches upcoming corporate events (earnings dates) from Yahoo Finance.
Update frequency: daily.
"""

import yfinance as yf
import pandas as pd
from datetime import date
from typing import List


def fetch_earnings_calendar(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch upcoming earnings dates for a list of tickers.

    Returns a DataFrame with columns:
        ticker, earnings_date, eps_estimate, revenue_estimate
    """
    records = []
    today = date.today().isoformat()

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar

            if cal is None:
                continue

            # calendar is a dict with keys like 'Earnings Date', 'EPS Estimate', etc.
            earnings_dates = cal.get("Earnings Date", [])
            eps_estimate = cal.get("EPS Estimate", None)
            revenue_estimate = cal.get("Revenue Estimate", None)

            if not earnings_dates:
                continue

            # earnings_dates can be a list of dates
            if not isinstance(earnings_dates, list):
                earnings_dates = [earnings_dates]

            for ed in earnings_dates:
                try:
                    ed_str = pd.Timestamp(ed).strftime("%Y-%m-%d")
                    if ed_str >= today:
                        records.append({
                            "ticker": ticker,
                            "earnings_date": ed_str,
                            "eps_estimate": eps_estimate,
                            "revenue_estimate": revenue_estimate,
                        })
                except Exception:
                    continue

        except Exception as e:
            print(f"[events] Error fetching {ticker}: {e}")
            continue

    if not records:
        return pd.DataFrame(columns=["ticker", "earnings_date", "eps_estimate", "revenue_estimate"])

    return pd.DataFrame(records).drop_duplicates(subset=["ticker", "earnings_date"])
