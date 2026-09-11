"""Observability: metrics, source_errors, history retention."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_metrics_endpoint_text():
    from trendscope.core import metrics
    from trendscope.server_api import app

    metrics.reset_for_tests()
    metrics.incr("pipeline_runs", 2)
    client = TestClient(app)
    with patch("trendscope.server_api.settings.api_key_required", False):
        resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "trendscope_pipeline_runs" in resp.text
    assert "trendscope_uptime_seconds" in resp.text


def test_metrics_json():
    from trendscope.core import metrics
    from trendscope.server_api import app

    metrics.reset_for_tests()
    metrics.incr("foo", 3)
    metrics.observe("bar", 0.5)
    client = TestClient(app)
    with patch("trendscope.server_api.settings.api_key_required", False):
        resp = client.get("/metrics.json")
    data = resp.json()
    assert data["counters"]["foo"] == 3
    assert "bar" in data["timings"]


def test_prune_history(tmp_path):
    from trendscope.watchlist.store import WatchlistStore

    store = WatchlistStore(db_path=Path(tmp_path) / "h.db")
    # insertar fila antigua directamente
    old = (datetime.now(timezone.utc) - timedelta(days=200)).isoformat()
    import sqlite3

    with sqlite3.connect(store.path) as conn:
        conn.execute(
            """
            INSERT INTO history
            (topic, geo, analyzed_at, total_signals, top_score, positive, negative, neutral, payload_json)
            VALUES ('old', 'CO', ?, 1, 10, 1, 0, 0, '{"big": true}')
            """
        ,
            (old,),
        )
        mid = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        conn.execute(
            """
            INSERT INTO history
            (topic, geo, analyzed_at, total_signals, top_score, positive, negative, neutral, payload_json)
            VALUES ('mid', 'CO', ?, 1, 10, 1, 0, 0, '{"big": true}')
            """
        ,
            (mid,),
        )

    result = store.prune_history(keep_days=90, keep_payload_days=14)
    assert result["deleted_rows"] >= 1
    assert result["trimmed_payloads"] >= 1

    remaining = store.get_history(topic="mid", days=365)
    assert remaining
    # payload recortado
    assert remaining[0].payload_json is None


def test_pipeline_increments_metrics(tmp_path):
    from trendscope.core import metrics
    from trendscope.core.pipeline import run
    from trendscope.core.query import TrendQuery

    metrics.reset_for_tests()

    def fake(query):
        return [{"source": "m", "title": "hello world AI", "text": "hello world AI"}]

    payload = {
        "meta": {
            "query": {"topic": "x", "geo": "CO"},
            "total_analyzed": 1,
            "sentiment_summary": {"positive": 1, "negative": 0, "neutral": 0, "engine": "local"},
        },
        "top_trends": [{"title": "x", "trend_score": 80, "source": "m"}],
    }

    with patch("trendscope.core.pipeline.SOURCES", [("M", fake)]):
        with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"M"}):
            with patch("trendscope.core.pipeline._SERIAL_SOURCES", set()):
                with patch("trendscope.core.pipeline.cache_get", return_value=None):
                    with patch("trendscope.core.pipeline.cache_set"):
                        with patch(
                            "trendscope.core.pipeline.analyze_items",
                            side_effect=lambda items, q: [
                                {
                                    **i,
                                    "sentiment_label": "positive",
                                    "sentiment_score": 0.9,
                                    "sentiment_engine": "local",
                                    "emotions": {},
                                }
                                for i in items
                            ],
                        ):
                            with patch(
                                "trendscope.core.pipeline.enrich_and_score",
                                side_effect=lambda items, q: [
                                    {**i, "trend_score": 80.0} for i in items
                                ],
                            ):
                                with patch(
                                    "trendscope.core.pipeline.generate_insights",
                                    return_value={},
                                ):
                                    with patch(
                                        "trendscope.core.pipeline.export_json",
                                        return_value=payload,
                                    ):
                                        with patch(
                                            "trendscope.core.pipeline.export_report",
                                            return_value="r",
                                        ):
                                            run(TrendQuery(mode="free", free_topic="x"))

    snap = metrics.snapshot()
    assert snap["counters"].get("pipeline_runs", 0) >= 1
    assert "pipeline" in snap["timings"]
