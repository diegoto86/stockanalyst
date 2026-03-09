"""
scheduler_rules.py
------------------
Defines which pipelines should run based on the current date and
the DATA_REFRESH_POLICY from config.py.
"""

from datetime import date
from config import DATA_REFRESH_POLICY


def should_run_daily() -> bool:
    """Return True on any business day."""
    return date.today().weekday() < 5  # Mon–Fri


def should_run_weekly() -> bool:
    """Return True on Monday (start of the trading week)."""
    return date.today().weekday() == 0


def should_run_monthly() -> bool:
    """Return True on the first business day of the month."""
    today = date.today()
    return today.day == 1 or (today.weekday() == 0 and today.day <= 3)


def should_run_quarterly() -> bool:
    """
    Return True during earnings season windows:
    January, April, July, October.
    """
    return date.today().month in (1, 4, 7, 10)
