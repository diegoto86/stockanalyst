# StockAnalyst — Swing Trading Multifactor System

End-of-day swing trading analysis tool for US equities.
Uses free Yahoo Finance data. No automatic execution — all trades are manual.

## Architecture

```
providers/       Yahoo Finance data fetchers
jobs/            Pipeline entry points (daily / weekly / monthly / quarterly)
storage/         Data repositories (SQLite + CSV/parquet)
orchestration/   Freshness checks, scheduling rules, dependency graph
engines/         BUY engine and SELL engine
data/            Local data storage (gitignored except portfolio template)
config.py        Universe, risk params, refresh policies
```

## Data refresh policy

| Dataset              | Frequency   |
|----------------------|-------------|
| Prices / technicals  | Daily       |
| News / earnings      | Daily       |
| Watchlist base       | Weekly      |
| Universe cleanup     | Monthly     |
| Fundamentals         | Quarterly   |

## Quickstart

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run daily pipeline
python jobs/run_daily.py

# Run weekly pipeline (Mondays)
python jobs/run_weekly.py

# Run quarterly pipeline (earnings season)
python jobs/run_quarterly.py
```

## Portfolio

Edit `data/portfolio/portfolio.csv` manually before each daily run.
Use `data/portfolio/portfolio_template.csv` as a starting point.

## Configuration

All parameters live in `config.py`:
- `UNIVERSE_TICKERS` — list of tickers to track
- `ACCOUNT_SIZE` — your account size in USD
- `MAX_RISK_PER_TRADE` — fraction of account risked per trade (default 1%)
- `MAX_POSITIONS` — maximum concurrent open positions
- `STALE_THRESHOLDS` — staleness limits per dataset

## Status

This is **V1 baseline** — module stubs only.
Engines and providers are scaffolded but not yet implemented.
