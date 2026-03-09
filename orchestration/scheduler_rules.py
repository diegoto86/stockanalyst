"""
scheduler_rules.py
------------------
Defines which pipelines should run based on the current date.
"""

from datetime import date


def should_run_daily() -> bool:
    """Return True on any business day (Mon-Fri)."""
    return date.today().weekday() < 5


def should_run_weekly() -> bool:
    """Return True on Monday."""
    return date.today().weekday() == 0


def should_run_monthly() -> bool:
    """Return True on the first business day of the month."""
    today = date.today()
    return today.day == 1 or (today.weekday() == 0 and today.day <= 3)


def should_run_quarterly() -> bool:
    """Return True during earnings season: January, April, July, October."""
    return date.today().month in (1, 4, 7, 10)


def print_schedule_status() -> None:
    print(f"Daily pipeline:     {'YES' if should_run_daily() else 'no'}")
    print(f"Weekly pipeline:    {'YES' if should_run_weekly() else 'no'}")
    print(f"Monthly pipeline:   {'YES' if should_run_monthly() else 'no'}")
    print(f"Quarterly pipeline: {'YES' if should_run_quarterly() else 'no'}")
