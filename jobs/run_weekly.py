"""
run_weekly.py
-------------
Weekly pipeline — runs once per week (Monday recommended).

Tasks:
    1. Init DB
    2. Fetch price history for liquidity / volume metrics
    3. Score each ticker (liquidity, size, quality, valuation)
    4. Build and save weekly watchlist
"""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from storage.db import init_db
from storage import watchlist_repository, fundamentals_repository
from storage import price_repository
from config import (
    UNIVERSE_TICKERS,
    MIN_MARKET_CAP,
    MIN_AVG_DAILY_VOLUME,
    MAX_PE_TTM,
    MAX_NET_DEBT_TO_EBITDA,
    MIN_GROSS_MARGIN,
)


def _liquidity_ok(avg_volume: float) -> bool:
    return avg_volume >= MIN_AVG_DAILY_VOLUME


def _size_ok(market_cap: float | None) -> bool:
    if market_cap is None:
        return False
    return market_cap >= MIN_MARKET_CAP


def _quality_ok(fund_row: pd.Series) -> bool:
    if fund_row is None or fund_row.empty:
        return True  # no data — allow through, will be filtered later
    gm = fund_row.get("gross_margin")
    debt = fund_row.get("net_debt_to_ebitda")
    gm_ok = gm is None or gm >= MIN_GROSS_MARGIN
    debt_ok = debt is None or debt <= MAX_NET_DEBT_TO_EBITDA
    return gm_ok and debt_ok


def _valuation_ok(fund_row: pd.Series) -> bool:
    if fund_row is None or fund_row.empty:
        return True
    pe = fund_row.get("pe_ttm")
    return pe is None or pe <= MAX_PE_TTM


def _compute_score(liquidity: bool, size: bool, quality: bool, valuation: bool, fund_score: float) -> float:
    base = sum([liquidity, size, quality, valuation]) / 4
    return round(base * 0.5 + fund_score * 0.5, 3)


def run():
    today = date.today().isoformat()
    week_of = (date.today() - timedelta(days=date.today().weekday())).isoformat()

    print(f"\n{'='*60}")
    print(f"[weekly] Starting weekly pipeline — week of {week_of}")
    print(f"{'='*60}")

    init_db()

    # Check if already done this week
    if watchlist_repository.current_week_exists():
        print("[weekly] Watchlist already up to date for this week. Skipping.")
        return

    # Load fundamentals for scoring
    fundamentals = fundamentals_repository.load_fundamentals(tickers=UNIVERSE_TICKERS)
    fund_lookup = {}
    if not fundamentals.empty:
        for _, row in fundamentals.iterrows():
            fund_lookup[row["ticker"]] = row

    records = []
    print(f"[weekly] Scoring {len(UNIVERSE_TICKERS)} tickers...")

    for ticker in UNIVERSE_TICKERS:
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception:
            info = {}

        market_cap = info.get("marketCap")
        avg_volume = info.get("averageVolume", 0) or 0

        fund_row = fund_lookup.get(ticker, pd.Series())
        fund_score = float(fund_row.get("fundamental_score", 0.5) or 0.5) if isinstance(fund_row, pd.Series) and not fund_row.empty else 0.5
        if isinstance(fund_row, dict):
            fund_score = fund_row.get("fundamental_score", 0.5) or 0.5

        liq = _liquidity_ok(avg_volume)
        sz = _size_ok(market_cap)
        qual = _quality_ok(fund_row if isinstance(fund_row, pd.Series) else pd.Series(fund_row))
        val = _valuation_ok(fund_row if isinstance(fund_row, pd.Series) else pd.Series(fund_row))
        score = _compute_score(liq, sz, qual, val, fund_score)
        included = liq and sz  # hard filters; quality/valuation are soft

        records.append({
            "ticker": ticker,
            "week_of": week_of,
            "liquidity_ok": int(liq),
            "size_ok": int(sz),
            "quality_ok": int(qual),
            "valuation_ok": int(val),
            "score": score,
            "included": int(included),
        })
        status = "IN" if included else "OUT"
        print(f"  {ticker:<8} score={score:.3f}  liq={int(liq)} sz={int(sz)} qual={int(qual)} val={int(val)}  [{status}]")

    watchlist_df = pd.DataFrame(records)
    watchlist_repository.save_watchlist(watchlist_df)

    included_count = watchlist_df["included"].sum()
    print(f"[weekly] Watchlist saved: {included_count} tickers included out of {len(records)}.")
    print(f"[weekly] Pipeline complete — {today}\n")


if __name__ == "__main__":
    run()
