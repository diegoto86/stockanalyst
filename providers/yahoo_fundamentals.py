"""
yahoo_fundamentals.py
---------------------
Fetches fundamental / financial data from Yahoo Finance.
Update frequency: quarterly (on new earnings releases).
"""

import yfinance as yf
import pandas as pd
from datetime import date
from typing import List


def _safe_get(info: dict, key: str, default=None):
    val = info.get(key, default)
    return val if val is not None else default


def _compute_fundamental_score(row: dict) -> float:
    """
    Compute a 0-1 composite fundamental score.
    Higher = better quality / value combination.
    """
    score = 0.0
    weights = 0.0

    # Revenue growth (positive = good)
    rev = row.get("revenue_growth_ttm")
    if rev is not None:
        score += min(max(rev / 0.3, 0), 1) * 0.20
        weights += 0.20

    # EPS growth (positive = good)
    eps = row.get("eps_growth_ttm")
    if eps is not None:
        score += min(max(eps / 0.3, 0), 1) * 0.20
        weights += 0.20

    # Gross margin (higher = better, benchmark 40%)
    gm = row.get("gross_margin")
    if gm is not None:
        score += min(max(gm / 0.4, 0), 1) * 0.15
        weights += 0.15

    # Operating margin (higher = better, benchmark 20%)
    om = row.get("operating_margin")
    if om is not None:
        score += min(max(om / 0.2, 0), 1) * 0.15
        weights += 0.15

    # Debt (lower = better, invert)
    debt = row.get("net_debt_to_ebitda")
    if debt is not None:
        score += min(max(1 - debt / 4, 0), 1) * 0.15
        weights += 0.15

    # FCF yield (higher = better, benchmark 5%)
    fcf = row.get("fcf_yield")
    if fcf is not None:
        score += min(max(fcf / 0.05, 0), 1) * 0.15
        weights += 0.15

    return round(score / weights, 4) if weights > 0 else 0.0


def fetch_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch key fundamental metrics for a list of tickers via yfinance.

    Returns a DataFrame with columns:
        ticker, as_of_date, fiscal_period,
        revenue_growth_ttm, eps_growth_ttm, gross_margin, operating_margin,
        net_debt_to_ebitda, pe_ttm, ev_to_ebitda, fcf_yield, fundamental_score
    """
    records = []
    today = date.today().isoformat()

    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            # Revenue growth (yfinance provides revenueGrowth as TTM YoY)
            revenue_growth = _safe_get(info, "revenueGrowth")
            eps_growth = _safe_get(info, "earningsGrowth")
            gross_margin = _safe_get(info, "grossMargins")
            operating_margin = _safe_get(info, "operatingMargins")
            pe_ttm = _safe_get(info, "trailingPE")
            ev_to_ebitda = _safe_get(info, "enterpriseToEbitda")
            market_cap = _safe_get(info, "marketCap", 0)
            total_debt = _safe_get(info, "totalDebt", 0)
            cash = _safe_get(info, "totalCash", 0)
            ebitda = _safe_get(info, "ebitda", 0)
            free_cashflow = _safe_get(info, "freeCashflow")

            # Net debt / EBITDA
            if ebitda and ebitda != 0:
                net_debt_to_ebitda = ((total_debt or 0) - (cash or 0)) / ebitda
            else:
                net_debt_to_ebitda = None

            # FCF yield
            if free_cashflow and market_cap and market_cap > 0:
                fcf_yield = free_cashflow / market_cap
            else:
                fcf_yield = None

            row = {
                "ticker": ticker,
                "as_of_date": today,
                "fiscal_period": _safe_get(info, "mostRecentQuarter", today),
                "revenue_growth_ttm": revenue_growth,
                "eps_growth_ttm": eps_growth,
                "gross_margin": gross_margin,
                "operating_margin": operating_margin,
                "net_debt_to_ebitda": net_debt_to_ebitda,
                "pe_ttm": pe_ttm,
                "ev_to_ebitda": ev_to_ebitda,
                "fcf_yield": fcf_yield,
                "fundamental_score": None,
            }
            row["fundamental_score"] = _compute_fundamental_score(row)
            records.append(row)

        except Exception as e:
            print(f"[fundamentals] Error fetching {ticker}: {e}")
            continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)
