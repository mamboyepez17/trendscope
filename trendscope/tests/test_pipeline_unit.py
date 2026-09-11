"""Pipeline unit tests with all scrapers mocked — no network."""

from unittest.mock import patch

from trendscope.core.pipeline import _run_unlocked
from trendscope.core.query import TrendQuery


def _items(n: int = 3) -> list[dict]:
    return [
        {
            "source": "mock",
            "title": f"mock trend {i} about AI",
            "text": f"mock trend {i} about AI",
            "url": f"https://example.com/{i}",
        }
        for i in range(n)
    ]


def _fake_analyze(items, query):
    for item in items:
        item["sentiment_label"] = "positive"
        item["sentiment_score"] = 0.9
        item["sentiment_engine"] = "local"
        item["emotions"] = {}
    return items


def _fake_score(items, query):
    for i, item in enumerate(items):
        item["trend_score"] = 90.0 - i
    return items


def test_pipeline_end_to_end_mocked(tmp_path):
    def fake_scraper(query):
        return _items(5)

    query = TrendQuery(mode="free", free_topic="ai", top_n=10)

    with patch("trendscope.core.pipeline.SOURCES", [("Mock", fake_scraper)]):
        with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"Mock"}):
            with patch("trendscope.core.pipeline._SERIAL_SOURCES", set()):
                with patch("trendscope.core.pipeline.cache_get", return_value=None):
                    with patch("trendscope.core.pipeline.cache_set") as mock_set:
                        with patch(
                            "trendscope.core.pipeline.analyze_items", side_effect=_fake_analyze
                        ):
                            with patch(
                                "trendscope.core.pipeline.enrich_and_score",
                                side_effect=_fake_score,
                            ):
                                with patch(
                                    "trendscope.core.pipeline.generate_insights",
                                    return_value={"summary": "ok"},
                                ):
                                    with patch(
                                        "trendscope.core.pipeline.export_json",
                                        side_effect=lambda items, q, ins: {
                                            "meta": {
                                                "query": {"topic": "ai", "geo": "CO"},
                                                "total_analyzed": len(items),
                                                "sentiment_summary": {
                                                    "positive": len(items),
                                                    "negative": 0,
                                                    "neutral": 0,
                                                    "engine": "local",
                                                    "overall": "positive",
                                                },
                                                "sources_used": ["mock"],
                                            },
                                            "top_trends": items,
                                        },
                                    ):
                                        with patch(
                                            "trendscope.core.pipeline.export_report",
                                            return_value="# report",
                                        ):
                                            payload, report = _run_unlocked(query)

    assert payload["top_trends"]
    assert payload["meta"]["sentiment_summary"]["engine"] != "failed"
    assert report == "# report"
    mock_set.assert_called_once()


def test_pipeline_cache_hit_skips_scrape():
    cached_payload = {"meta": {"query": {"topic": "x"}}, "top_trends": []}
    query = TrendQuery(mode="free", free_topic="x")

    def boom(query):
        raise AssertionError("scrapers should not run on cache hit")

    with patch(
        "trendscope.core.pipeline.cache_get",
        return_value=[cached_payload, "cached-report"],
    ):
        with patch("trendscope.core.pipeline.SOURCES", [("Boom", boom)]):
            payload, report = _run_unlocked(query)

    assert payload is cached_payload
    assert report == "cached-report"


def test_pipeline_semaphore_raises_when_saturated():
    import threading

    from trendscope.core import pipeline

    # Saturar el semáforo
    acquired = []
    for _ in range(2):
        ok = pipeline._PIPELINE_SEMAPHORE.acquire(blocking=False)
        acquired.append(ok)
    assert all(acquired)

    try:
        query = TrendQuery(mode="free", free_topic="z")
        try:
            pipeline.run(query)
            raised = False
        except RuntimeError:
            raised = True
        assert raised
    finally:
        for _ in range(2):
            pipeline._PIPELINE_SEMAPHORE.release()
