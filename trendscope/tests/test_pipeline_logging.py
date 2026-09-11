"""Pipeline logging, cache key and concurrency behaviour."""

from unittest.mock import patch

from loguru import logger

from trendscope.core.pipeline import _cache_key
from trendscope.core.query import TrendQuery


class TestCacheKey:
    def test_includes_top_n(self):
        q1 = TrendQuery(mode="free", free_topic="crypto", top_n=10)
        q2 = TrendQuery(mode="free", free_topic="crypto", top_n=50)
        assert _cache_key(q1) != _cache_key(q2)

    def test_includes_geo_and_engine(self):
        q1 = TrendQuery(mode="free", free_topic="ai", geo="CO", sentiment_engine="local")
        q2 = TrendQuery(mode="free", free_topic="ai", geo="MX", sentiment_engine="local")
        q3 = TrendQuery(mode="free", free_topic="ai", geo="CO", sentiment_engine="claude")
        assert _cache_key(q1) != _cache_key(q2)
        assert _cache_key(q1) != _cache_key(q3)

    def test_stable_for_same_query(self):
        q1 = TrendQuery(mode="free", free_topic="crypto", top_n=25)
        q2 = TrendQuery(mode="free", free_topic="crypto", top_n=25)
        assert _cache_key(q1) == _cache_key(q2)


class TestLoguruSinksPreserved:
    def test_pipeline_does_not_remove_sinks(self):
        from trendscope.core.pipeline import SOURCES, _run_unlocked

        before = len(logger._core.handlers)

        def fake_scraper(query):
            return [{"source": "fake", "title": "hello world", "text": "hello world"}]

        with patch("trendscope.core.pipeline.SOURCES", [("Fake", fake_scraper)]):
            with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"Fake"}):
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
                                            "trendscope.core.pipeline.export_report",
                                            return_value="report",
                                        ):
                                            from trendscope.core.query import TrendQuery as TQ

                                            _run_unlocked(TQ(mode="free", free_topic="x"))

        after = len(logger._core.handlers)
        assert after >= before
        assert after >= 1


class TestSourceErrorsInPayload:
    def test_failing_source_recorded(self):
        from trendscope.core.pipeline import _run_unlocked
        from trendscope.core.query import TrendQuery as TQ

        def ok_scraper(query):
            return [{"source": "ok", "title": "t", "text": "t"}]

        def bad_scraper(query):
            raise RuntimeError("boom")

        with patch(
            "trendscope.core.pipeline.SOURCES",
            [("Good", ok_scraper), ("Bad", bad_scraper)],
        ):
            with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"Good", "Bad"}):
                with patch("trendscope.core.pipeline._SERIAL_SOURCES", set()):
                    with patch("trendscope.core.pipeline.cache_get", return_value=None):
                        with patch("trendscope.core.pipeline.cache_set"):
                            with patch(
                                "trendscope.core.pipeline.analyze_items",
                                side_effect=lambda items, q: [
                                    {
                                        **i,
                                        "sentiment_label": "neutral",
                                        "sentiment_score": 0.5,
                                        "sentiment_engine": "local",
                                        "emotions": {},
                                    }
                                    for i in items
                                ],
                            ):
                                with patch(
                                    "trendscope.core.pipeline.enrich_and_score",
                                    side_effect=lambda items, q: [
                                        {**i, "trend_score": 50.0} for i in items
                                    ],
                                ):
                                    with patch(
                                        "trendscope.core.pipeline.generate_insights",
                                        return_value={},
                                    ):
                                        with patch(
                                            "trendscope.core.pipeline.export_report",
                                            return_value="r",
                                        ):
                                            payload, _ = _run_unlocked(
                                                TQ(mode="free", free_topic="x")
                                            )

        assert "Bad" in payload["meta"]["source_errors"]
        assert "boom" in payload["meta"]["source_errors"]["Bad"]
