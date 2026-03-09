"""
freshness.py
------------
Checks whether a dataset is stale and needs to be refreshed,
based on the policies defined in config.py.
"""

from datetime import datetime, timedelta
from config import STALE_THRESHOLDS
import storage.price_repository as price_repo
import storage.technical_repository as tech_repo
import storage.fundamentals_repository as fund_repo
import storage.news_repository as news_repo
import storage.watchlist_repository as watch_repo


def is_stale(dataset: str, last_updated: datetime) -> bool:
    """
    Return True if the dataset has exceeded its allowed staleness threshold.
    """
    threshold_days = STALE_THRESHOLDS.get(f"{dataset}_days")
    if threshold_days is None:
        raise ValueError(f"No stale threshold configured for dataset: {dataset}")
    age = datetime.utcnow() - last_updated
    return age > timedelta(days=threshold_days)


def needs_refresh(dataset: str, last_updated: datetime | None) -> bool:
    """Return True if the dataset has never been updated or is stale."""
    if last_updated is None:
        return True
    return is_stale(dataset, last_updated)


def dataset_status() -> dict:
    """
    Return a dict of {dataset: needs_refresh (bool)} for all tracked datasets.
    Useful for dashboard display and pipeline decisions.
    """
    return {
        "prices_daily": needs_refresh("prices_daily", price_repo.get_last_updated()),
        "technical_snapshot": needs_refresh("technical_snapshot", tech_repo.get_last_updated()),
        "news_events": needs_refresh("news_events", news_repo.get_last_updated()),
        "watchlist_base": needs_refresh("watchlist_base", watch_repo.get_last_updated()),
        "fundamentals_snapshot": needs_refresh("fundamentals_snapshot", fund_repo.get_last_updated()),
    }
