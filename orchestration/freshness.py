"""
freshness.py
------------
Checks whether a dataset is stale and needs to be refreshed,
based on the policies defined in config.py.
"""

from datetime import datetime, timedelta
from config import STALE_THRESHOLDS


def is_stale(dataset: str, last_updated: datetime) -> bool:
    """
    Return True if the dataset has exceeded its allowed staleness threshold.

    Args:
        dataset: key matching one of the STALE_THRESHOLDS entries
        last_updated: datetime of the last successful update
    """
    threshold_days = STALE_THRESHOLDS.get(f"{dataset}_days")
    if threshold_days is None:
        raise ValueError(f"No stale threshold configured for dataset: {dataset}")
    age = datetime.utcnow() - last_updated
    return age > timedelta(days=threshold_days)


def needs_refresh(dataset: str, last_updated: datetime | None) -> bool:
    """
    Return True if the dataset has never been updated or is stale.
    """
    if last_updated is None:
        return True
    return is_stale(dataset, last_updated)
