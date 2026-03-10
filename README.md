# StockAnalyst - Swing Trading Multifactor System

End-of-day swing trading analysis tool for US equities.
Uses free Yahoo Finance data. No automatic execution - all trades are manual.

## Architecture

```text
providers/            Yahoo Finance data fetchers
jobs/                 Pipeline entry points (daily / weekly / monthly / quarterly)
storage/              Data repositories (SQLite + CSV)
orchestration/        Freshness checks, scheduling rules, dependency graph
engines/              Buy, sell, technicals, and signal evaluation logic
dashboard_sections/   Modular Streamlit UI sections
tests/                Pytest coverage for trading engines
data/                 Local data storage
config.py             Universe, risk params, refresh policies
```

## Current capabilities

- Daily pipeline for prices, technicals, news, earnings, buy signals, sell actions, and signal evaluation
- Weekly watchlist scoring with liquidity, size, quality, and valuation filters
- Historical persistence of buy/sell signals in SQLite plus CSV archives
- Dashboard with market context, signals, portfolio, sectors, charts, history, and performance
- Monthly maintenance pipeline for local universe cleanup and master watchlist export

## Data refresh policy

| Dataset | Frequency |
|---|---|
| Prices / technicals | Daily |
| News / earnings | Daily |
| Signal evaluation | Daily |
| Watchlist base | Weekly |
| Universe cleanup | Monthly |
| Fundamentals | Quarterly |

## Quickstart

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run pipelines
python jobs/run_quarterly.py
python jobs/run_weekly.py
python jobs/run_daily.py
python jobs/run_monthly.py

# Launch dashboard
streamlit run dashboard.py

# Run tests
pytest
```

## Portfolio

Edit `data/portfolio/portfolio.csv` manually before each daily run.
Use `data/portfolio/portfolio_template.csv` as a starting point.

## Configuration

Main parameters live in `config.py`:

- `UNIVERSE_TICKERS`
- `ACCOUNT_SIZE`
- `MAX_RISK_PER_TRADE`
- `MAX_POSITIONS`
- `MAX_SECTOR_EXPOSURE`
- `STALE_THRESHOLDS`

## Status

This is a functional local trading analysis application, not a stub.
The current focus is improving ranking quality, operational robustness, and dashboard decision support.
