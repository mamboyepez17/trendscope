"""Stance, calibration, and sentiment cache."""

from trendscope.core.query import TrendQuery
from trendscope.sentiment import analyze_items
from trendscope.sentiment.cache import (
    cache_clear,
    cache_get,
    cache_set,
    cache_stats,
    calibrate_score,
)
from trendscope.sentiment.base import SentimentResult
from trendscope.sentiment.stance import analyze_stance, enrich_stance, summarize_stances


class TestStance:
    def test_support_phrase(self):
        r = analyze_stance(
            "El presidente Abelardo de la Espriella recibe admiración y apoyo masivo",
            topic="Abelardo de la Espriella",
            sentiment_label="positive",
        )
        assert r.label == "support"

    def test_against_phrase(self):
        r = analyze_stance(
            "La oposición critica y denuncia al gobierno por corrupción",
            topic="gobierno",
            sentiment_label="negative",
        )
        assert r.label == "against"

    def test_negation_flips_support(self):
        r = analyze_stance("No apoyan al presidente", topic="presidente")
        assert r.label == "against"

    def test_unknown_short(self):
        assert analyze_stance("ok").label == "unknown"

    def test_enrich_and_summary(self):
        items = [
            {"title": "Apoyo total al plan"},
            {"title": "Crítica dura y rechazo al plan"},
            {"title": "Hace frío"},
        ]
        enrich_stance(items, topic="plan")
        assert items[0]["stance"] == "support"
        assert items[1]["stance"] == "against"
        s = summarize_stances(items)
        assert s["support"] == 1
        assert s["against"] == 1
        assert s["dominant"] in {"support", "against", "mixed", "unknown"}


class TestCalibration:
    def test_neutral_near_half(self):
        assert abs(calibrate_score("neutral", 0.9) - 0.5) < 0.15

    def test_positive_high(self):
        assert calibrate_score("positive", 0.95) > 0.85

    def test_clamped(self):
        assert 0.0 <= calibrate_score("positive", 1.5) <= 1.0
        assert 0.0 <= calibrate_score("negative", -1) <= 1.0


class TestCache:
    def setup_method(self):
        cache_clear()

    def test_miss_then_hit(self):
        r = SentimentResult(text="hola", label="positive", score=0.9, engine="t", emotions={})
        assert cache_get("hola mundo", "t") is None
        cache_set("hola mundo", "t", r)
        got = cache_get("hola mundo", "t")
        assert got is not None
        assert got.label == "positive"
        assert cache_stats()["entries"] == 1


class TestPipelineStanceField:
    def test_analyze_items_sets_stance(self):
        items = [{"source": "t", "title": "Apoyo y admiración al presidente"}]
        q = TrendQuery(mode="free", free_topic="presidente", sentiment_engine="local")
        out = analyze_items(items, q)
        assert "stance" in out[0]
        assert out[0]["stance"] in {"support", "against", "mixed", "unknown"}
