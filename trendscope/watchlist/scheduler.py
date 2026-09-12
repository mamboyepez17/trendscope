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
        """Run pipeline for a single watch item, save history and evaluate alerts."""
        try:
            # Re-fetch por id: el snapshot del job puede estar desactualizado
            fresh = self.store.get(item.id) if item.id is not None else item
            if fresh is None:
                fresh = item
            item = fresh

            query = TrendQuery(
                mode="category" if item.category else "free",
                category=item.category,
                free_topic=item.topic,
                geo=item.geo,
                sentiment_engine=item.sentiment_engine,
            )
            payload, _ = run_pipeline(query)
            record = self.store.save_history(payload)
            logger.info(f"Scheduled analysis done: {item.topic}")

            self._maybe_alert(item, record)
        except Exception as e:
            logger.error(f"Scheduled analysis failed for {item.topic}: {e}")

    def _maybe_alert(self, item, record) -> None:
        """Evalúa reglas de alerta y envía webhook si corresponde."""
        if not item.alert_webhook:
            return

        from trendscope.watchlist.alerts import (
            build_alert_payload,
            evaluate_triggers,
            send_webhook,
        )

        history = self.store.get_history(topic=item.topic, days=30, limit=2)
        previous = None
        if len(history) >= 2:
            prev = history[1]
            previous = {
                "top_score": prev.top_score,
                "positive": prev.positive,
                "negative": prev.negative,
                "neutral": prev.neutral,
                "total_signals": prev.total_signals,
            }

        current = {
            "top_score": record.top_score,
            "positive": record.positive,
            "negative": record.negative,
            "neutral": record.neutral,
            "total_signals": record.total_signals,
            "analyzed_at": record.analyzed_at.isoformat(),
        }

        triggered = evaluate_triggers(
            current,
            previous,
            min_score=item.alert_min_score,
            sentiment_flip=item.alert_sentiment_flip,
        )
        if not triggered:
            return

        payload = build_alert_payload(
            item.topic, item.geo, current, previous, triggered
        )
        ok = send_webhook(item.alert_webhook, payload)
        if ok:
            logger.info(f"Alert sent for {item.topic}: {triggered}")

    def send_digests(self) -> int:
        """Envía digests a items con digest_webhook. Retorna nº enviados."""
        from trendscope.watchlist.digest import send_digest

        sent = 0
        for item in self.store.list_active():
            if not item.digest_webhook:
                continue
            try:
                if send_digest(self.store, item):
                    sent += 1
            except Exception as e:
                logger.error("Digest failed for {}: {}", item.topic, e)
        return sent

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
