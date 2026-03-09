"""
portfolio_repository.py
-----------------------
Read and write the manual portfolio CSV (portfolio_positions).
"""

import pandas as pd
from pathlib import Path
from config import PORTFOLIO_CSV_PATH

COLUMNS = ["ticker", "entry_date", "entry_price", "shares", "initial_stop", "current_stop", "notes"]


def load_portfolio() -> pd.DataFrame:
    """
    Load current open positions from the manual CSV file.
    Returns an empty DataFrame if the file doesn't exist.
    """
    path = Path(PORTFOLIO_CSV_PATH)
    if not path.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path)
    # Ensure all expected columns are present
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = None
    return df[COLUMNS]


def save_portfolio(df: pd.DataFrame) -> None:
    """Write updated portfolio positions back to the CSV file."""
    path = Path(PORTFOLIO_CSV_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
