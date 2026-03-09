# StockAnalyst — Project Context

## What This Is
Swing trading multifactor analysis system for US equities. End-of-day signals only.
No automatic execution — user trades manually. Data from Yahoo Finance (free).

Architecture doc: `c:\Users\diego\Downloads\estrategia_swing_trading_arquitectura.txt`

## GitHub
- Repo: https://github.com/diegoto86/stockanalyst
- Branch: `master`
- Deployed on **Streamlit Community Cloud** (free tier)

## Tech Stack
- Python 3.12, no Docker, virtual environment at `.venv/`
- Storage: **SQLite** (`data/stockanalyst.db`) + CSV outputs
- Frontend: **Streamlit** + Plotly
- Data provider: `yfinance`
- No pandas-ta, no SQLAlchemy, no pyarrow (removed — caused Streamlit Cloud deploy failures)
- Technicals computed manually in `engines/technicals.py` (MA, RSI, ATR)

## Project Structure
```
config.py               Central config: universe, risk params, refresh policies
dashboard.py            Streamlit dashboard (entry point)
providers/              Yahoo Finance fetchers (prices, fundamentals, news, events)
storage/                SQLite repositories + portfolio CSV reader
  db.py                 DB init with all table schemas
orchestration/          Freshness checks, scheduler rules, dependency graph
engines/                BUY engine, SELL engine, technicals computation
jobs/                   Pipeline entry points (daily, weekly, quarterly)
data/                   Local data (gitignored except portfolio template)
```

## Current Status (as of 2026-03-09)

### Fully implemented and working:
- All 4 providers (prices, fundamentals, news, events)
- All storage repositories with SQLite
- Technical indicators (MA20/50/200, RSI14, ATR14, pullback%, trend state, setup flags)
- BUY engine: watchlist + technical + news + earnings filter, position sizing, R-multiple
- SELL engine: stop hit, trailing stop, news signal, fundamental deterioration, partial profit
- Daily, weekly, quarterly pipelines wired end-to-end
- Dashboard with pipeline trigger buttons, data freshness indicators, all sections

### Key bug fix applied:
- yfinance returns **MultiIndex columns** `(Price, Ticker)` — `providers/yahoo_prices.py` now handles this correctly
- Weekly pipeline accepts `force=True` to allow re-running (dashboard always passes force=True)
- `dashboard.py` sets `os.chdir(PROJECT_ROOT)` for Streamlit Cloud compatibility

### Pipeline run order (IMPORTANT):
1. **Quarterly** — fetches fundamentals (run first, takes ~5 min)
2. **Weekly** — builds watchlist using fundamentals
3. **Daily** — prices, technicals, news, buy/sell signals (needs watchlist to exist)

## What's NOT Implemented Yet
- `jobs/run_monthly.py` — universe cleanup (still a stub, prints only)
- No backtesting
- No historical buy/sell signal log (daily CSVs overwrite each day)
- No price charts per ticker in dashboard
- No sector exposure tracking in dashboard
- No email/notification alerts
- No automatic scheduling (user clicks buttons or runs scripts manually)

## Important Design Decisions
- Portfolio is a **manual CSV** (`data/portfolio/portfolio.csv`) — user edits by hand
- Buy engine skips tickers with **earnings within 7 days**
- Buy engine skips when **market context (SPY) is in downtrend**
- Sell engine **never lowers stops** — only raises them (trailing stop logic)
- Fundamental score is a **weighted composite** (revenue growth, EPS, margins, debt, FCF)
- Weekly watchlist has hard filters (liquidity + market cap) and soft filters (quality + valuation)

## Config Defaults (in config.py)
- Universe: 20 tickers (AAPL, MSFT, NVDA, AMZN, GOOGL, META, TSM, AVGO, ASML, AMD, JPM, V, MA, UNH, LLY, XOM, CVX, HD, PG, KO)
- Account size: $100,000
- Max risk per trade: 1%
- Max positions: 10
- ATR stop multiplier: 1.5x
- Min R-multiple target: 2.0

## User Preferences
- Language: Spanish (understands English too, but speaks Spanish)
- Prefers clear explanations of what each feature does
- Wants to be able to run everything from the Streamlit dashboard UI
- No Docker for now — local venv + Streamlit Cloud deployment
