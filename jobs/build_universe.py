"""
build_universe.py
-----------------
Fetches all NYSE and NASDAQ listed stocks from NASDAQ's free screener API,
filters by market cap and average volume, and saves the result to
data/universe_tickers.csv so config.py can load them dynamically.

Run this once (or whenever you want to refresh the universe):
    python -m jobs.build_universe
"""

import time
import requests
import pandas as pd
from pathlib import Path

from config import MIN_MARKET_CAP, MIN_AVG_DAILY_VOLUME, DATA_DIR

OUTPUT_PATH = Path(DATA_DIR) / "universe_tickers.csv"

# NASDAQ screener supports exchange filter: nasdaq, nyse, amex
EXCHANGES = ["nasdaq", "nyse", "amex"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}


def _fetch_exchange(exchange: str) -> pd.DataFrame:
    """Fetch all stocks for a given exchange from NASDAQ screener."""
    url = (
        f"https://api.nasdaq.com/api/screener/stocks"
        f"?tableonly=true&limit=10000&offset=0&exchange={exchange}&download=true"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("data", {}).get("rows", [])
        if not rows:
            print(f"  [universe] No rows returned for {exchange.upper()}")
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["exchange"] = exchange.upper()
        return df
    except Exception as e:
        print(f"  [universe] Error fetching {exchange.upper()}: {e}")
        return pd.DataFrame()


def _parse_market_cap(val) -> float:
    """Convert NASDAQ market cap string like '$1.5B', '$200M' to float."""
    if not val or val in ("", "N/A"):
        return 0.0
    try:
        val = str(val).strip().replace("$", "").replace(",", "")
        if val.endswith("T"):
            return float(val[:-1]) * 1_000_000_000_000
        if val.endswith("B"):
            return float(val[:-1]) * 1_000_000_000
        if val.endswith("M"):
            return float(val[:-1]) * 1_000_000
        return float(val)
    except Exception:
        return 0.0


def _parse_volume(val) -> float:
    """Convert volume string to float."""
    if not val or val in ("", "N/A"):
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except Exception:
        return 0.0


def run() -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("[universe] Building stock universe from NASDAQ screener")
    print("=" * 60)

    all_frames = []
    for exchange in EXCHANGES:
        print(f"  [universe] Fetching {exchange.upper()}...")
        df = _fetch_exchange(exchange)
        if not df.empty:
            print(f"  [universe]   -> {len(df)} stocks found")
            all_frames.append(df)
        time.sleep(1)  # be polite to the API

    if not all_frames:
        print("[universe] ERROR: Could not fetch any stock data. Check your internet connection.")
        return pd.DataFrame()

    raw = pd.concat(all_frames, ignore_index=True)
    print(f"\n[universe] Total raw stocks: {len(raw)}")

    # Normalize columns
    raw.columns = [c.lower().strip() for c in raw.columns]

    # Keep only relevant columns (NASDAQ screener column names)
    ticker_col = next((c for c in raw.columns if c in ("symbol", "ticker")), None)
    name_col = next((c for c in raw.columns if "name" in c), None)
    cap_col = next((c for c in raw.columns if "marketcap" in c or "market cap" in c), None)
    vol_col = next((c for c in raw.columns if "volume" in c), None)
    sector_col = next((c for c in raw.columns if "sector" in c), None)
    country_col = next((c for c in raw.columns if "country" in c), None)

    if not ticker_col:
        print("[universe] ERROR: Could not find ticker column in response.")
        return pd.DataFrame()

    # Parse numeric fields
    raw["market_cap"] = raw[cap_col].apply(_parse_market_cap) if cap_col else 0.0
    raw["avg_volume"] = raw[vol_col].apply(_parse_volume) if vol_col else 0.0

    # Filter: US-only (exclude foreign listings / ADRs by country if available)
    if country_col:
        raw = raw[raw[country_col].str.upper().isin(["UNITED STATES", "US", "USA", ""])]
        print(f"[universe] After US-only filter: {len(raw)}")

    # Filter out invalid tickers (e.g. those with special chars except dot)
    raw["ticker"] = raw[ticker_col].str.strip()
    raw = raw[raw["ticker"].str.match(r"^[A-Z]{1,5}$")]
    print(f"[universe] After ticker format filter: {len(raw)}")

    # Hard filters: market cap and volume
    filtered = raw[
        (raw["market_cap"] >= MIN_MARKET_CAP) &
        (raw["avg_volume"] >= MIN_AVG_DAILY_VOLUME)
    ].copy()
    print(f"[universe] After market cap (${MIN_MARKET_CAP/1e9:.1f}B+) + volume ({MIN_AVG_DAILY_VOLUME:,}+) filter: {len(filtered)}")

    # Build output
    output_cols = {"ticker": "ticker"}
    if name_col:
        output_cols[name_col] = "name"
    if sector_col:
        output_cols[sector_col] = "sector"
    output_cols["market_cap"] = "market_cap"
    output_cols["avg_volume"] = "avg_volume"
    output_cols["exchange"] = "exchange"

    result = filtered.rename(columns=output_cols)[[c for c in output_cols.values() if c in filtered.rename(columns=output_cols).columns]]
    result = result.sort_values("market_cap", ascending=False).reset_index(drop=True)

    # Save
    Path(DATA_DIR).mkdir(exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"[universe] Saved {len(result)} tickers to {OUTPUT_PATH}")
    print(f"[universe] Top 10 by market cap: {result['ticker'].head(10).tolist()}")
    print("[universe] Done.\n")

    return result


if __name__ == "__main__":
    run()
