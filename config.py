"""
config.py
---------
Central configuration for the StockAnalyst swing trading system.
Edit this file to adjust universe, risk parameters, and refresh policies.
"""

import csv
from pathlib import Path

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

# Fallback seed list (used when data/universe_tickers.csv does not exist).
# Run jobs/build_universe.py to generate a broader universe automatically.
_SEED_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
    "META", "TSM", "AVGO", "ASML", "AMD",
    "JPM", "V", "MA", "UNH", "LLY",
    "XOM", "CVX", "HD", "PG", "KO",
]

_UNIVERSE_CSV = Path(__file__).parent / "data" / "universe_tickers.csv"


def _load_universe() -> list:
    if _UNIVERSE_CSV.exists():
        try:
            with open(_UNIVERSE_CSV, newline="") as f:
                reader = csv.DictReader(f)
                tickers = [row["ticker"].strip() for row in reader if row.get("ticker", "").strip()]
            if tickers:
                return tickers
        except Exception:
            pass
    return _SEED_TICKERS


UNIVERSE_TICKERS = _load_universe()

# Market context indices
INDEX_TICKERS = ["SPY", "QQQ", "IWM"]

# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------

DATA_DIR = "data"
PORTFOLIO_CSV_PATH = f"{DATA_DIR}/portfolio/portfolio.csv"
DB_PATH = f"{DATA_DIR}/stockanalyst.db"

# ---------------------------------------------------------------------------
# Risk parameters
# ---------------------------------------------------------------------------

MAX_POSITIONS = 10
MAX_RISK_PER_TRADE = 0.01       # 1% of account per trade
MAX_SECTOR_EXPOSURE = 0.30      # max 30% in any single sector
ACCOUNT_SIZE = 100_000          # USD — update to your actual account size

# ---------------------------------------------------------------------------
# Data refresh policy
# ---------------------------------------------------------------------------

DATA_REFRESH_POLICY = {
    "prices_daily": "daily",
    "technical_snapshot": "daily",
    "news_events": "daily",
    "earnings_calendar": "daily",
    "portfolio_positions": "daily",
    "watchlist_base": "weekly",
    "liquidity_metrics": "weekly",
    "universe_cleanup": "monthly",
    "fundamentals_snapshot": "quarterly",
}

# ---------------------------------------------------------------------------
# Staleness thresholds (in days)
# ---------------------------------------------------------------------------

STALE_THRESHOLDS = {
    "prices_daily_days": 1,
    "technical_snapshot_days": 1,
    "news_events_days": 1,
    "watchlist_base_days": 7,
    "universe_cleanup_days": 30,
    "fundamentals_snapshot_days": 90,
}

# ---------------------------------------------------------------------------
# Fundamental filter thresholds (used in weekly universe scoring)
# ---------------------------------------------------------------------------

MIN_MARKET_CAP = 2_000_000_000      # $2B minimum
MIN_AVG_DAILY_VOLUME = 500_000      # shares
MAX_PE_TTM = 60
MAX_NET_DEBT_TO_EBITDA = 4.0
MIN_GROSS_MARGIN = 0.20

# ---------------------------------------------------------------------------
# Technical setup parameters
# ---------------------------------------------------------------------------

PULLBACK_MAX_PCT = 0.15             # max 15% pullback from recent high
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 70
ATR_STOP_MULTIPLIER = 1.5          # stop = entry - 1.5 * ATR
MIN_R_MULTIPLE_TARGET = 2.0        # minimum reward/risk ratio
