"""
Tests for sell_engine.py
"""

import pandas as pd
import pytest
from engines.sell_engine import run, _r_multiple, _compute_new_trailing_stop


# ---------------------------------------------------------------------------
# Helper: build minimal DataFrames for testing
# ---------------------------------------------------------------------------

def _portfolio(rows: list[dict]) -> pd.DataFrame:
    """Build a portfolio DataFrame from a list of dicts."""
    defaults = {"initial_stop": 90.0, "current_stop": 90.0, "shares": 100}
    return pd.DataFrame([{**defaults, **r} for r in rows])


def _technicals(rows: list[dict]) -> pd.DataFrame:
    """Build a technicals DataFrame from a list of dicts."""
    defaults = {
        "date": "2026-03-10",
        "close": 100.0,
        "ma20": 99.0,
        "ma50": 95.0,
        "ma200": 85.0,
        "rsi14": 55.0,
        "atr14": 3.0,
        "pullback_pct": 0.05,
        "trend_state": "uptrend",
        "setup_flags": "pullback_ok,rsi_reset,above_ma50,above_ma200",
    }
    return pd.DataFrame([{**defaults, **r} for r in rows])


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------

class TestRMultiple:
    def test_positive_r(self):
        assert _r_multiple(100, 110, 95) == 2.0

    def test_negative_r(self):
        assert _r_multiple(100, 95, 90) == -0.5

    def test_zero_risk(self):
        assert _r_multiple(100, 110, 100) is None

    def test_negative_risk(self):
        assert _r_multiple(100, 110, 105) is None


class TestTrailingStop:
    def test_raises_stop(self):
        # close=110, ATR=3, multiplier=1.5 -> new_stop = 110 - 4.5 = 105.5
        result = _compute_new_trailing_stop(100, 95, 3.0, 110)
        assert result == 105.5

    def test_never_lowers(self):
        # close=100, ATR=3, multiplier=1.5 -> new_stop = 100 - 4.5 = 95.5
        # current_stop is 97 which is higher -> should keep 97
        result = _compute_new_trailing_stop(100, 97, 3.0, 100)
        assert result == 97.0


# ---------------------------------------------------------------------------
# Integration tests for sell engine run()
# ---------------------------------------------------------------------------

class TestSellEngineStopHit:
    def test_close_on_stop_hit(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 95}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 94.0}  # below stop
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert len(result) == 1
        assert result.iloc[0]["action"] == "close"
        assert result.iloc[0]["sell_pct"] == 100.0
        assert result.iloc[0]["current_price"] == 94.0

    def test_close_on_stop_equal(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 95}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 95.0}  # exactly at stop
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert result.iloc[0]["action"] == "close"


class TestSellEngineNegativeNews:
    def test_partial_sell_on_bad_news(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 90}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 105.0}
        ])
        news = pd.DataFrame([{
            "ticker": "AAPL",
            "impact_level": "high",
            "sentiment_proxy": -0.5,
        }])
        result = run(portfolio, technicals, news=news, fundamentals=None)

        assert result.iloc[0]["action"] == "partial_sell"
        assert result.iloc[0]["sell_pct"] == 50.0


class TestSellEngineFundamentalDeterioration:
    def test_partial_sell_on_bad_fundamentals(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 90}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 105.0}
        ])
        fundamentals = pd.DataFrame([{
            "ticker": "AAPL",
            "fundamental_score": 0.2,  # below 0.3 threshold
        }])
        result = run(portfolio, technicals, news=None, fundamentals=fundamentals)

        assert result.iloc[0]["action"] == "partial_sell"


class TestSellEngineTrendBreak:
    def test_partial_sell_below_ma50(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 85}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 94.0, "ma50": 95.0, "trend_state": "mixed"}
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert result.iloc[0]["action"] == "partial_sell"
        assert "below MA50" in result.iloc[0]["rationale"]


class TestSellEngineRaiseStop:
    def test_raise_stop_in_uptrend(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 95}
        ])
        # close=115 -> new trailing stop = 115 - 1.5*3 = 110.5 > 95
        technicals = _technicals([
            {"ticker": "AAPL", "close": 115.0, "atr14": 3.0, "trend_state": "uptrend"}
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert result.iloc[0]["action"] == "raise_stop"
        assert result.iloc[0]["new_stop"] == 110.5


class TestSellEngineHold:
    def test_hold_when_no_signal(self):
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 95}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 101.0, "trend_state": "mixed", "ma50": 99.0}
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert result.iloc[0]["action"] == "hold"

    def test_empty_portfolio(self):
        result = run(pd.DataFrame(), None, None, None)
        assert result.empty


class TestSellEngineUsesCloseNotMA20:
    def test_current_price_is_close(self):
        """Verify the engine uses close price, not MA20."""
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 90}
        ])
        technicals = _technicals([
            {"ticker": "AAPL", "close": 112.0, "ma20": 105.0}
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        # current_price should be 112 (close), not 105 (ma20)
        assert result.iloc[0]["current_price"] == 112.0


class TestSellEngineProfitTarget:
    def test_partial_sell_at_high_r(self):
        """At >= 4R (MIN_R_MULTIPLE_TARGET * 2), take partial profits."""
        portfolio = _portfolio([
            {"ticker": "AAPL", "entry_price": 100, "current_stop": 95}
        ])
        # R = (entry - stop) = 5, so 4R target = 100 + 20 = 120
        technicals = _technicals([
            {"ticker": "AAPL", "close": 120.0, "trend_state": "mixed",
             "ma50": 110.0, "atr14": 3.0}
        ])
        result = run(portfolio, technicals, news=None, fundamentals=None)

        assert result.iloc[0]["action"] == "partial_sell"
        assert result.iloc[0]["sell_pct"] == 33.0
