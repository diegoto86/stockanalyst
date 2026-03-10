"""
Tests for technical indicators.
"""

import pandas as pd

from engines.technicals import _rsi


class TestRSI:
    def test_wilder_rsi_reaches_extremes(self):
        up_series = pd.Series(range(1, 40))
        down_series = pd.Series(range(40, 1, -1))

        up_rsi = _rsi(up_series, 14).iloc[-1]
        down_rsi = _rsi(down_series, 14).iloc[-1]

        assert up_rsi > 99
        assert down_rsi < 1
