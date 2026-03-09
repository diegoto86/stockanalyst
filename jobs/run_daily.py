"""
run_daily.py
------------
Daily pipeline — runs every market day after close.

Tasks:
    1. Init DB
    2. Fetch and save daily price bars
    3. Compute and save technical indicators
    4. Fetch and save recent news
    5. Fetch upcoming earnings calendar
    6. Load manual portfolio
    7. Run BUY engine -> save buy_candidates_daily
    8. Run SELL engine -> save sell_actions_daily
    9. Export CSV reports for dashboard
"""

from datetime import date
from pathlib import Path

from storage.db import init_db
from orchestration.freshness import needs_refresh
from providers import yahoo_prices, yahoo_news, yahoo_events
from storage import (
    price_repository,
    technical_repository,
    news_repository,
    watchlist_repository,
    portfolio_repository,
)
from engines.technicals import compute_technicals
from engines import buy_engine, sell_engine
from config import UNIVERSE_TICKERS, INDEX_TICKERS, DATA_DIR


def _market_context(index_df) -> dict:
    """Build a simple market context dict from index prices."""
    if index_df is None or index_df.empty:
        return {"spy_trend": "unknown"}
    spy_rows = index_df[index_df["ticker"] == "SPY"]
    if spy_rows.empty:
        return {"spy_trend": "unknown"}
    chg = spy_rows.iloc[0].get("change_pct", 0) or 0
    trend = "uptrend" if chg > 0 else "downtrend" if chg < -1 else "mixed"
    result = {"spy_trend": trend}
    for _, row in index_df.iterrows():
        result[row["ticker"]] = {
            "close": round(float(row.get("close", 0)), 2),
            "change_pct": round(float(row.get("change_pct", 0)), 2),
        }
    return result


def run():
    today = date.today().isoformat()
    print(f"\n{'='*60}")
    print(f"[daily] Starting daily pipeline — {today}")
    print(f"{'='*60}")

    # 0. Init DB
    init_db()

    # 1. Prices
    print("[daily] Fetching price bars...")
    price_df = yahoo_prices.fetch_daily_bars(UNIVERSE_TICKERS, period="1y")
    if not price_df.empty:
        price_repository.save_price_bars(price_df)
        print(f"[daily] Saved {len(price_df)} price records.")
    else:
        print("[daily] WARNING: No price data received.")

    # 1b. Index prices for market context
    print("[daily] Fetching index prices...")
    index_df = yahoo_prices.fetch_index_prices(INDEX_TICKERS + ["^VIX"])
    market_ctx = _market_context(index_df)
    print(f"[daily] Market context: SPY trend = {market_ctx.get('spy_trend')}")

    # Save index prices to CSV for dashboard
    if not index_df.empty:
        Path(DATA_DIR).mkdir(exist_ok=True)
        index_df.to_csv(f"{DATA_DIR}/market_context.csv", index=False)

    # 2. Technicals
    print("[daily] Computing technical indicators...")
    all_prices = price_repository.load_price_bars(tickers=UNIVERSE_TICKERS)
    if not all_prices.empty:
        technicals_df = compute_technicals(all_prices)
        if not technicals_df.empty:
            technical_repository.save_technical_snapshot(technicals_df)
            print(f"[daily] Saved technicals for {len(technicals_df)} tickers.")
    else:
        technicals_df = technical_repository.load_technical_snapshot()

    # 3. News
    print("[daily] Fetching news...")
    news_df = yahoo_news.fetch_news(UNIVERSE_TICKERS, days_back=5)
    if not news_df.empty:
        news_repository.save_news(news_df)
        print(f"[daily] Saved {len(news_df)} news items.")

    # 4. Earnings calendar
    print("[daily] Fetching earnings calendar...")
    earnings_df = yahoo_events.fetch_earnings_calendar(UNIVERSE_TICKERS)
    if not earnings_df.empty:
        earnings_df.to_csv(f"{DATA_DIR}/earnings_calendar.csv", index=False)
        print(f"[daily] Saved {len(earnings_df)} earnings events.")

    # 5. Portfolio
    print("[daily] Loading portfolio...")
    portfolio = portfolio_repository.load_portfolio()
    print(f"[daily] {len(portfolio)} open positions.")

    # 6. Watchlist
    watchlist = watchlist_repository.load_watchlist()
    if watchlist.empty:
        print("[daily] WARNING: No weekly watchlist found. Run weekly pipeline first.")

    # 7. Fundamentals
    from storage import fundamentals_repository
    fundamentals = fundamentals_repository.load_fundamentals(tickers=UNIVERSE_TICKERS)

    # 8. BUY engine
    print("[daily] Running BUY engine...")
    technicals_latest = technical_repository.load_technical_snapshot()
    candidates = buy_engine.run(
        watchlist=watchlist,
        technicals=technicals_latest,
        news=news_repository.load_news(days_back=3),
        fundamentals=fundamentals,
        market_context=market_ctx,
        portfolio=portfolio,
        earnings_calendar=earnings_df if not earnings_df.empty else None,
    )
    if not candidates.empty:
        candidates.to_csv(f"{DATA_DIR}/buy_candidates_daily.csv", index=False)
        print(f"[daily] {len(candidates)} buy candidate(s) found.")
    else:
        print("[daily] No buy candidates today.")

    # 9. SELL engine
    print("[daily] Running SELL engine...")
    actions = sell_engine.run(
        portfolio=portfolio,
        technicals=technicals_latest,
        news=news_repository.load_news(days_back=3),
        fundamentals=fundamentals,
    )
    if not actions.empty:
        actions.to_csv(f"{DATA_DIR}/sell_actions_daily.csv", index=False)
        print(f"[daily] {len(actions)} sell action(s) generated.")
    else:
        print("[daily] No sell actions today.")

    print(f"[daily] Pipeline complete — {today}\n")


if __name__ == "__main__":
    run()
