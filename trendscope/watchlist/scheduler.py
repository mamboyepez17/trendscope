"""Scheduler for recurrent watchlist analysis."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from trendscope.core.pipeline import run as run_pipeline
from trendscope.core.query import TrendQuery
from trendscope.watchlist.store import get_store


class WatchlistScheduler:
    """Runs periodic analysis for active watchlist items."""

    def __init__(self, store=None):
        self.store = store or get_store()
        self.scheduler: BackgroundScheduler | None = None

    def _analyze_item(self, item):
        """Run pipeline for a single watch item and save history."""
        try:
            query = TrendQuery(
                mode="category" if item.category else "free",
                category=item.category,
                free_topic=item.topic,
                geo=item.geo,
                sentiment_engine=item.sentiment_engine,
            )
            payload, _ = run_pipeline(query)
            self.store.save_history(payload)
            logger.info(f"Scheduled analysis done: {item.topic}")
        except Exception as e:
            logger.error(f"Scheduled analysis failed for {item.topic}: {e}")

    def tick(self):
        """Immediate tick: analyze all active items now."""
        for item in self.store.list_active():
            self._analyze_item(item)

    def start(self) -> BackgroundScheduler:
        """Start the background scheduler with per-item intervals."""
        if self.scheduler and self.scheduler.running:
            return self.scheduler

        self.scheduler = BackgroundScheduler()
        for item in self.store.list_active():
            self.scheduler.add_job(
                self._analyze_item,
                trigger=IntervalTrigger(minutes=item.interval_minutes),
                id=f"watchlist-{item.id}",
                replace_existing=True,
                args=[item],
            )
        self.scheduler.start()
        logger.info("Watchlist scheduler started")
        return self.scheduler

    def stop(self) -> None:
        """Stop the scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Watchlist scheduler stopped")

    def refresh(self) -> None:
        """Reload jobs from the database."""
        self.stop()
        self.start()


def get_scheduler() -> WatchlistScheduler:
    """Factory for the default scheduler."""
    return WatchlistScheduler()
