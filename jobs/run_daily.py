"""
run_daily.py
------------
Daily pipeline — runs every market day after close.

Tasks:
    1. Update daily price bars
    2. Compute technical indicators
    3. Fetch recent news
    4. Fetch upcoming earnings calendar
    5. Load manual portfolio
    6. Run BUY engine -> export buy_candidates_daily
    7. Run SELL engine -> export sell_actions_daily
"""

from orchestration.freshness import needs_refresh
from providers import yahoo_prices, yahoo_news, yahoo_events
from storage import (
    price_repository,
    technical_repository,
    news_repository,
    watchlist_repository,
    portfolio_repository,
)
from engines import buy_engine, sell_engine
from config import UNIVERSE_TICKERS


def run():
    print("[daily] Starting daily pipeline...")

    # 1. Prices
    print("[daily] Fetching price bars...")
    # price_df = yahoo_prices.fetch_daily_bars(UNIVERSE_TICKERS)
    # price_repository.save_price_bars(price_df)

    # 2. Technicals
    print("[daily] Computing technical indicators...")
    # technical_snapshot = compute_technicals(price_df)
    # technical_repository.save_technical_snapshot(technical_snapshot)

    # 3. News
    print("[daily] Fetching news...")
    # news_df = yahoo_news.fetch_news(UNIVERSE_TICKERS)
    # news_repository.save_news(news_df)

    # 4. Earnings calendar
    print("[daily] Fetching earnings calendar...")
    # events_df = yahoo_events.fetch_earnings_calendar(UNIVERSE_TICKERS)

    # 5. Portfolio
    print("[daily] Loading portfolio...")
    # portfolio = portfolio_repository.load_portfolio()

    # 6. BUY engine
    print("[daily] Running BUY engine...")
    # watchlist = watchlist_repository.load_watchlist()
    # technicals = technical_repository.load_technical_snapshot()
    # candidates = buy_engine.run(watchlist, technicals, news_df, ...)
    # candidates.to_csv("data/buy_candidates_daily.csv", index=False)

    # 7. SELL engine
    print("[daily] Running SELL engine...")
    # actions = sell_engine.run(portfolio, technicals, news_df, ...)
    # actions.to_csv("data/sell_actions_daily.csv", index=False)

    print("[daily] Pipeline complete.")


if __name__ == "__main__":
    run()
