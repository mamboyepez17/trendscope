"""Digest webhook summaries."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from trendscope.watchlist.digest import build_digest_payload, send_digest
from trendscope.watchlist.models import WatchItem
from trendscope.watchlist.scheduler import WatchlistScheduler
from trendscope.watchlist.store import WatchlistStore


def test_build_digest_empty():
    p = build_digest_payload("ai", "CO", [])
    assert p["type"] == "digest"
    assert p["points"] == 0


def test_build_digest_with_history(tmp_path):
    store = WatchlistStore(db_path=Path(tmp_path) / "d.db")
    for score in (40, 60, 80):
        store.save_history(
            {
                "meta": {
                    "query": {"topic": "ai", "geo": "CO"},
                    "total_analyzed": 5,
                    "sentiment_summary": {"positive": 3, "negative": 1, "neutral": 1},
                },
                "top_trends": [{"trend_score": score, "title": "t"}],
            }
        )
    records = store.get_history(topic="ai")
    payload = build_digest_payload("ai", "CO", records, forecast={"trend": "rising"})
    assert payload["points"] == 3
    assert payload["latest"]["top_score"] == 80
    assert payload["forecast"]["trend"] == "rising"


def test_send_digest_calls_webhook(tmp_path):
    store = WatchlistStore(db_path=Path(tmp_path) / "d2.db")
    store.save_history(
        {
            "meta": {
                "query": {"topic": "x", "geo": "CO"},
                "total_analyzed": 1,
                "sentiment_summary": {"positive": 1},
            },
            "top_trends": [{"trend_score": 70, "title": "t"}],
        }
    )
    item = store.add(
        WatchItem(
            id=None,
            topic="x",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            alert_webhook="https://hooks.example.com/digest",
        )
    )
    with patch("trendscope.watchlist.alerts.httpx.post", return_value=MagicMock(status_code=200)) as mock_post:
        with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
            ok = send_digest(store, item)
    assert ok
    assert mock_post.called


def test_scheduler_send_digests(tmp_path):
    store = WatchlistStore(db_path=Path(tmp_path) / "d3.db")
    store.add(
        WatchItem(
            id=None,
            topic="y",
            category=None,
            geo="CO",
            sentiment_engine="local",
            interval_minutes=60,
            digest_webhook="https://hooks.example.com/d",
        )
    )
    sched = WatchlistScheduler(store)
    with patch("trendscope.watchlist.alerts.httpx.post", return_value=MagicMock(status_code=200)):
        with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
            n = sched.send_digests()
    assert n == 1
