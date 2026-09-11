"""Watchlist alerts: thresholds, webhook, SSRF protection."""

from unittest.mock import MagicMock, patch

from trendscope.watchlist.alerts import (
    _is_ssrf_blocked,
    build_alert_payload,
    evaluate_triggers,
    send_webhook,
)


class TestEvaluateTriggers:
    def test_min_score_hit(self):
        cur = {"top_score": 90, "total_signals": 10, "positive": 5, "negative": 1}
        assert "min_score" in evaluate_triggers(cur, None, min_score=80)

    def test_min_score_miss(self):
        cur = {"top_score": 40, "total_signals": 10, "positive": 5, "negative": 1}
        assert evaluate_triggers(cur, None, min_score=80) == []

    def test_sentiment_flip(self):
        prev = {"top_score": 50, "positive": 10, "negative": 1}
        cur = {"top_score": 50, "positive": 1, "negative": 10}
        assert "sentiment_flip" in evaluate_triggers(cur, prev, sentiment_flip=True)

    def test_no_flip_same_direction(self):
        prev = {"top_score": 50, "positive": 10, "negative": 1}
        cur = {"top_score": 50, "positive": 8, "negative": 2}
        assert evaluate_triggers(cur, prev, sentiment_flip=True) == []

    def test_min_volume(self):
        cur = {"top_score": 10, "total_signals": 100, "positive": 1, "negative": 0}
        assert "min_volume" in evaluate_triggers(cur, None, min_volume=50)


class TestSsrf:
    def test_blocks_localhost(self):
        assert _is_ssrf_blocked("http://localhost/hook")
        assert _is_ssrf_blocked("http://127.0.0.1/hook")

    def test_blocks_metadata(self):
        assert _is_ssrf_blocked("http://169.254.169.254/latest/meta-data")
        assert _is_ssrf_blocked("http://metadata.google.internal/")

    def test_blocks_private_ip(self):
        assert _is_ssrf_blocked("http://10.0.0.5/hook")
        assert _is_ssrf_blocked("http://192.168.1.1/hook")

    def test_blocks_bad_scheme(self):
        assert _is_ssrf_blocked("file:///etc/passwd")
        assert _is_ssrf_blocked("ftp://example.com/x")

    def test_allows_public_https(self):
        assert not _is_ssrf_blocked("https://hooks.example.com/trendscope")


class TestSendWebhook:
    def test_calls_httpx_post(self):
        with patch("trendscope.watchlist.alerts.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
                ok = send_webhook("https://hooks.example.com/x", {"a": 1})
        assert ok
        mock_post.assert_called_once()

    def test_blocked_ssrf_not_called(self):
        with patch("trendscope.watchlist.alerts.httpx.post") as mock_post:
            with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
                ok = send_webhook("http://169.254.169.254/x", {"a": 1})
        assert not ok
        mock_post.assert_not_called()

    def test_disabled_alerts(self):
        with patch("trendscope.watchlist.alerts.httpx.post") as mock_post:
            with patch("trendscope.watchlist.alerts.settings.alerts_enabled", False):
                ok = send_webhook("https://hooks.example.com/x", {"a": 1})
        assert not ok
        mock_post.assert_not_called()

    def test_http_error_returns_false(self):
        with patch("trendscope.watchlist.alerts.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=500)
            with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
                ok = send_webhook("https://hooks.example.com/x", {"a": 1})
        assert not ok


class TestSchedulerAlert:
    def test_scheduler_sends_webhook_on_threshold(self):
        from datetime import datetime, timezone

        from trendscope.watchlist.models import WatchItem
        from trendscope.watchlist.scheduler import WatchlistScheduler
        from trendscope.watchlist.store import WatchlistStore
        import tempfile
        from pathlib import Path

        tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        store = WatchlistStore(db_path=Path(tmp.name) / "w.db")
        item = store.add(
            WatchItem(
                id=None,
                topic="crypto",
                category=None,
                geo="CO",
                sentiment_engine="local",
                interval_minutes=60,
                alert_webhook="https://hooks.example.com/alert",
                alert_min_score=80,
            )
        )
        sched = WatchlistScheduler(store)

        payload = {
            "meta": {
                "query": {"topic": "crypto", "geo": "CO"},
                "total_analyzed": 10,
                "sentiment_summary": {
                    "positive": 8,
                    "negative": 1,
                    "neutral": 1,
                    "overall": "positive",
                    "engine": "local",
                },
            },
            "top_trends": [{"trend_score": 95, "title": "btc"}],
        }

        with patch("trendscope.watchlist.scheduler.run_pipeline", return_value=(payload, "r")):
            with patch(
                "trendscope.watchlist.alerts.httpx.post", return_value=MagicMock(status_code=200)
            ) as mock_post:
                with patch("trendscope.watchlist.alerts.settings.alerts_enabled", True):
                    sched._analyze_item(item)

        assert mock_post.called
        tmp.cleanup()


class TestBuildPayload:
    def test_payload_shape(self):
        cur = {
            "top_score": 90,
            "total_signals": 5,
            "positive": 3,
            "negative": 1,
            "neutral": 1,
            "analyzed_at": "2026-01-01T00:00:00",
        }
        p = build_alert_payload("ai", "CO", cur, None, ["min_score"])
        assert p["topic"] == "ai"
        assert p["triggered_by"] == ["min_score"]
        assert p["top_score"] == 90
