"""
yahoo_fundamentals.py
---------------------
Fetches fundamental / financial data from Yahoo Finance.
Update frequency: quarterly (on new earnings releases).
"""

import yfinance as yf
import pandas as pd
from typing import List


def fetch_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch key fundamental metrics for a list of tickers.

    Returns a DataFrame with columns:
        ticker, as_of_date, fiscal_period,
        revenue_growth_ttm, eps_growth_ttm,
        gross_margin, operating_margin,
        net_debt_to_ebitda, pe_ttm, ev_to_ebitda,
        fcf_yield, fundamental_score
    """
    raise NotImplementedError("fetch_fundamentals not implemented yet")
