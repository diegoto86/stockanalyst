"""
Tests for run_monthly.py
"""

import pandas as pd

from jobs import run_monthly


class TestBuildReview:
    def test_flags_stale_and_missing_fundamentals(self, monkeypatch):
        universe_df = pd.DataFrame(
            [
                {
                    "ticker": "AAPL",
                    "name": "Apple",
                    "sector": "Technology",
                    "market_cap": 3_000_000_000,
                    "avg_volume": 2_000_000,
                    "exchange": "NASDAQ",
                },
                {
                    "ticker": "OLDX",
                    "name": "Old Co",
                    "sector": "Industrial",
                    "market_cap": 3_000_000_000,
                    "avg_volume": 2_000_000,
                    "exchange": "NYSE",
                },
            ]
        )

        monkeypatch.setattr(
            run_monthly,
            "_latest_price_dates",
            lambda: pd.DataFrame(
                [
                    {"ticker": "AAPL", "latest_price_date": "2026-03-10"},
                    {"ticker": "OLDX", "latest_price_date": "2026-01-01"},
                ]
            ),
        )
        monkeypatch.setattr(
            run_monthly.fundamentals_repository,
            "load_fundamentals",
            lambda tickers: pd.DataFrame(
                [{"ticker": "AAPL", "as_of_date": "2026-03-01", "fundamental_score": 0.8}]
            ),
        )

        review_df = run_monthly._build_review(universe_df)

        aapl = review_df.loc[review_df["ticker"] == "AAPL"].iloc[0]
        oldx = review_df.loc[review_df["ticker"] == "OLDX"].iloc[0]

        assert bool(aapl["keep"]) is True
        assert aapl["status"] == "ok"
        assert bool(oldx["keep"]) is False
        assert "stale_or_missing_prices" in oldx["status"]
        assert "missing_fundamentals" in oldx["status"]
