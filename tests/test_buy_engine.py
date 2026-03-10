"""
Tests for buy_engine.py
"""

import pandas as pd
import pytest
from engines.buy_engine import (
    run,
    _score_setup,
    _compute_position_size,
    _news_penalty,
    _has_earnings_soon,
    _enforce_sector_exposure,
)


# ---------------------------------------------------------------------------
# Helper: build minimal DataFrames for testing
# ---------------------------------------------------------------------------

def _watchlist(tickers: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"ticker": tickers, "score": [0.8] * len(tickers)})


def _technicals(rows: list[dict]) -> pd.DataFrame:
    defaults = {
        "date": "2026-03-10",
        "close": 100.0,
        "ma20": 99.0,
        "ma50": 95.0,
        "ma200": 85.0,
        "rsi14": 50.0,
        "atr14": 3.0,
        "pullback_pct": 0.05,
        "trend_state": "uptrend",
        "setup_flags": "pullback_ok,rsi_reset,above_ma50,above_ma200",
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _market_context(spy_trend: str = "uptrend") -> dict:
    return {"spy_trend": spy_trend}


# ---------------------------------------------------------------------------
# Unit tests for scoring
# ---------------------------------------------------------------------------

class TestScoreSetup:
    def test_returns_dict_with_subscores(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 95.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 50.0,
            "trend_state": "uptrend",
            "setup_flags": "pullback_ok,rsi_reset,above_ma50,above_ma200",
        })
        result = _score_setup(tech, None)
        assert isinstance(result, dict)
        assert "total" in result
        assert "pullback" in result
        assert "rsi" in result
        assert "ma_align" in result
        assert "trend" in result
        assert "fundament" in result
        assert "news" in result

    def test_ideal_pullback_scores_max(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 95.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 30.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        result = _score_setup(tech, None)
        assert result["pullback"] == 0.15  # 5% is in sweet spot
        assert result["rsi"] == 0.15  # RSI 30 is max

    def test_shallow_pullback_scores_less(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 95.0, "ma200": 85.0,
            "pullback_pct": 0.01, "rsi14": 50.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        result = _score_setup(tech, None)
        assert 0 < result["pullback"] < 0.15  # partial score

    def test_high_rsi_scores_zero(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 95.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 60.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        result = _score_setup(tech, None)
        assert result["rsi"] == 0.0

    def test_fundamentals_add_score(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 95.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 40.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        no_fund = _score_setup(tech, None)
        with_fund = _score_setup(tech, pd.Series({"fundamental_score": 0.8}))
        assert with_fund["fundament"] > no_fund["fundament"]
        assert with_fund["total"] > no_fund["total"]

    def test_different_setups_produce_different_scores(self):
        """Key test: verify the new scoring differentiates candidates."""
        strong = pd.Series({
            "close": 100.0, "ma50": 98.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 35.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        weak = pd.Series({
            "close": 100.0, "ma50": 80.0, "ma200": 85.0,
            "pullback_pct": 0.12, "rsi14": 55.0,
            "trend_state": "mixed",
            "setup_flags": "",
        })
        strong_score = _score_setup(strong, None)["total"]
        weak_score = _score_setup(weak, None)["total"]
        assert strong_score > weak_score
        assert strong_score != weak_score  # they must differ

    def test_total_capped_at_1(self):
        tech = pd.Series({
            "close": 100.0, "ma50": 99.0, "ma200": 85.0,
            "pullback_pct": 0.05, "rsi14": 25.0,
            "trend_state": "uptrend",
            "setup_flags": "",
        })
        fund = pd.Series({"fundamental_score": 1.0})
        result = _score_setup(tech, fund)
        assert result["total"] <= 1.0


# ---------------------------------------------------------------------------
# Unit tests for position sizing
# ---------------------------------------------------------------------------

class TestPositionSize:
    def test_basic_sizing(self):
        # entry=100, stop=95, risk_per_share=5, dollar_risk=100000*0.01=1000
        # shares = 1000/5 = 200
        assert _compute_position_size(100, 95, 100_000, 0.01) == 200

    def test_zero_risk(self):
        assert _compute_position_size(100, 100, 100_000, 0.01) == 0

    def test_negative_risk(self):
        assert _compute_position_size(100, 105, 100_000, 0.01) == 0


# ---------------------------------------------------------------------------
# Unit tests for news penalty
# ---------------------------------------------------------------------------

class TestNewsPenalty:
    def test_no_news(self):
        assert _news_penalty("AAPL", None) == 1.0
        assert _news_penalty("AAPL", pd.DataFrame()) == 1.0

    def test_high_impact_negative(self):
        news = pd.DataFrame([{
            "ticker": "AAPL",
            "impact_level": "high",
            "sentiment_proxy": -0.5,
        }])
        assert _news_penalty("AAPL", news) == 0.0

    def test_moderate_negative(self):
        news = pd.DataFrame([{
            "ticker": "AAPL",
            "impact_level": "low",
            "sentiment_proxy": -0.3,
        }])
        assert _news_penalty("AAPL", news) == 0.5

    def test_positive_news(self):
        news = pd.DataFrame([{
            "ticker": "AAPL",
            "impact_level": "low",
            "sentiment_proxy": 0.5,
        }])
        assert _news_penalty("AAPL", news) == 1.0

    def test_different_ticker(self):
        news = pd.DataFrame([{
            "ticker": "MSFT",
            "impact_level": "high",
            "sentiment_proxy": -0.5,
        }])
        assert _news_penalty("AAPL", news) == 1.0


# ---------------------------------------------------------------------------
# Unit tests for earnings filter
# ---------------------------------------------------------------------------

class TestEarningsFilter:
    def test_no_earnings(self):
        assert _has_earnings_soon("AAPL", None) is False
        assert _has_earnings_soon("AAPL", pd.DataFrame()) is False

    def test_earnings_far_away(self):
        earnings = pd.DataFrame([{
            "ticker": "AAPL",
            "earnings_date": "2099-12-31",
        }])
        # Far future, > 7 days
        assert _has_earnings_soon("AAPL", earnings, days=7) is False


# ---------------------------------------------------------------------------
# Unit tests for sector exposure enforcement
# ---------------------------------------------------------------------------

class TestSectorExposure:
    def test_limits_sector_concentration(self):
        candidates = pd.DataFrame({
            "ticker": ["A", "B", "C", "D"],
            "score": [0.9, 0.8, 0.7, 0.6],
        })
        sector_map = {"A": "Tech", "B": "Tech", "C": "Tech", "D": "Finance"}
        # max_positions=10, max_exposure=0.30 -> max_per_sector=3
        result = _enforce_sector_exposure(
            candidates, pd.DataFrame(), sector_map, 0.30, 10
        )
        # All 3 Tech + 1 Finance = 4 should pass (max 3 per sector)
        assert len(result) == 4

    def test_rejects_over_limit(self):
        candidates = pd.DataFrame({
            "ticker": ["A", "B", "C", "D"],
            "score": [0.9, 0.8, 0.7, 0.6],
        })
        sector_map = {"A": "Tech", "B": "Tech", "C": "Tech", "D": "Tech"}
        # max_positions=10, max_exposure=0.20 -> max_per_sector=2
        result = _enforce_sector_exposure(
            candidates, pd.DataFrame(), sector_map, 0.20, 10
        )
        assert len(result) == 2
        assert list(result["ticker"]) == ["A", "B"]

    def test_considers_portfolio_positions(self):
        candidates = pd.DataFrame({
            "ticker": ["A", "B"],
            "score": [0.9, 0.8],
        })
        portfolio = pd.DataFrame({"ticker": ["X", "Y"]})
        sector_map = {"X": "Tech", "Y": "Tech", "A": "Tech", "B": "Finance"}
        # max_positions=10, max_exposure=0.30 -> max_per_sector=3
        # Portfolio already has 2 Tech, so only 1 more Tech allowed
        result = _enforce_sector_exposure(
            candidates, portfolio, sector_map, 0.30, 10
        )
        assert len(result) == 2  # A (fills last Tech slot) + B (Finance)

    def test_empty_sector_map(self):
        candidates = pd.DataFrame({"ticker": ["A"], "score": [0.9]})
        result = _enforce_sector_exposure(
            candidates, pd.DataFrame(), {}, 0.30, 10
        )
        assert len(result) == 1  # passes through unchanged


# ---------------------------------------------------------------------------
# Integration tests for buy engine run()
# ---------------------------------------------------------------------------

class TestBuyEngineRun:
    def test_basic_candidate_generation(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL", "close": 100.0}])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert len(result) == 1
        assert result.iloc[0]["ticker"] == "AAPL"
        assert result.iloc[0]["entry_price"] == 100.0

    def test_uses_close_not_ma20(self):
        """Verify entry_price is close, not MA20 approximation."""
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 105.0, "ma20": 99.0}
        ])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.iloc[0]["entry_price"] == 105.0

    def test_skips_downtrend_market(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL"}])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("downtrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.empty

    def test_skips_overbought(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL", "rsi14": 75.0}])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.empty

    def test_skips_downtrend_ticker(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([
            {"ticker": "AAPL", "trend_state": "downtrend"}
        ])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.empty

    def test_skips_existing_position(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL"}])
        portfolio = pd.DataFrame({"ticker": ["AAPL"]})
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=portfolio,
        )
        assert result.empty

    def test_skips_high_impact_negative_news(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL"}])
        news = pd.DataFrame([{
            "ticker": "AAPL",
            "impact_level": "high",
            "sentiment_proxy": -0.5,
        }])
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=news,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.empty

    def test_portfolio_full(self):
        watchlist = _watchlist(["AAPL"])
        technicals = _technicals([{"ticker": "AAPL"}])
        portfolio = pd.DataFrame({
            "ticker": [f"T{i}" for i in range(10)]
        })
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=portfolio,
            max_positions=10,
        )
        assert result.empty

    def test_empty_watchlist(self):
        result = run(
            watchlist=pd.DataFrame(),
            technicals=_technicals([{"ticker": "AAPL"}]),
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
        )
        assert result.empty

    def test_sector_enforcement(self):
        """Verify sector limits are applied when sector_map is provided."""
        tickers = ["A", "B", "C", "D"]
        watchlist = _watchlist(tickers)
        technicals = _technicals([{"ticker": t, "close": 100.0} for t in tickers])
        sector_map = {"A": "Tech", "B": "Tech", "C": "Tech", "D": "Tech"}
        result = run(
            watchlist=watchlist,
            technicals=technicals,
            news=None,
            fundamentals=None,
            market_context=_market_context("uptrend"),
            portfolio=pd.DataFrame(),
            sector_map=sector_map,
            max_positions=10,
        )
        # max_per_sector = int(10 * 0.30) = 3
        assert len(result) <= 3
