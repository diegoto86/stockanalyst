"""
portfolio_repository.py
-----------------------
Read and write the manual portfolio CSV (portfolio_positions).
"""

import pandas as pd
from config import PORTFOLIO_CSV_PATH


def load_portfolio() -> pd.DataFrame:
    """
    Load current open positions from the manual CSV file.

    Expected columns:
        ticker, entry_date, entry_price, shares,
        initial_stop, current_stop, notes
    """
    raise NotImplementedError("load_portfolio not implemented yet")


def save_portfolio(df: pd.DataFrame) -> None:
    """
    Write updated portfolio positions back to the CSV file.
    """
    raise NotImplementedError("save_portfolio not implemented yet")
