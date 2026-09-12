"""Source health runtime scores."""

from unittest.mock import patch

from trendscope.core import source_health


def setup_function():
    source_health.reset_for_tests()


def test_score_unknown_is_optimistic():
    assert source_health.snapshot() == {}
    # no registry entry → not skipped
    assert not source_health.should_skip("Unknown")


def test_success_improves_score():
    source_health.record_success("HN", 0.1)
    source_health.record_success("HN", 0.2)
    snap = source_health.snapshot()
    assert snap["HN"]["score"] == 1.0
    assert not source_health.should_skip("HN")


def test_failures_lower_score_and_skip():
    for _ in range(5):
        source_health.record_failure("Amazon", "boom")
    source_health.record_success("Amazon", 0.1)
    snap = source_health.snapshot()
    assert snap["Amazon"]["score"] < 0.2
    with patch("trendscope.core.source_health.settings.source_health_skip", True):
        assert source_health.should_skip("Amazon")


def test_skip_disabled_by_config():
    for _ in range(10):
        source_health.record_failure("X", "err")
    with patch("trendscope.core.source_health.settings.source_health_skip", False):
        assert not source_health.should_skip("X")


def test_pipeline_includes_source_health_in_meta(tmp_path):
    from trendscope.core.pipeline import _run_unlocked
    from trendscope.core.query import TrendQuery

    def ok(query):
        source_health.record_success("Mock", 0.01)
        return [{"source": "mock", "title": "hello world AI"}]

    def bad(query):
        source_health.record_failure("Bad", "nope")
        raise RuntimeError("nope")

    payload = {
        "meta": {
            "query": {"topic": "x", "geo": "CO"},
            "total_analyzed": 1,
            "sentiment_summary": {
                "positive": 1,
                "negative": 0,
                "neutral": 0,
                "engine": "local",
            },
        },
        "top_trends": [{"title": "x", "trend_score": 80, "source": "mock"}],
    }

    with patch(
        "trendscope.core.pipeline.SOURCES",
        [("Mock", ok), ("Bad", bad)],
    ):
        with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"Mock", "Bad"}):
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
                                            out, _ = _run_unlocked(
                                                TrendQuery(mode="free", free_topic="x")
                                            )

    assert "source_health" in out["meta"]
    assert "source_errors" in out["meta"]
