"""Sentiment language detection and text selection."""

from trendscope.core.query import TrendQuery
from trendscope.sentiment import analyze_items
from trendscope.sentiment.local_engine import _detect_language


def test_spanish_accent_forces_es():
    assert _detect_language("Qué porquería, odio este servicio basura") == "es"
    assert _detect_language("El presidente se reunió con ministros") == "es"
    assert _detect_language("¡Increíble! Ganó el partido") == "es"


def test_english_detected():
    assert _detect_language("The president met with ministers today") == "en"
    assert _detect_language("This is a great and amazing product") == "en"


def test_default_is_es_for_ambiguous():
    assert _detect_language("crypto blockchain") == "es"  # LatAm-first default


def test_analyze_items_labels_spanish_negative():
    items = [{"source": "t", "title": "Qué porquería, odio este servicio basura"}]
    q = TrendQuery(mode="free", free_topic="x", sentiment_engine="local")
    out = analyze_items(items, q)
    assert out[0]["sentiment_label"] == "negative"
    # local_es (pysentimiento) o local_fallback_es (léxico, sin torch)
    assert out[0]["sentiment_engine"] in {"local_es", "local_fallback_es"}
    assert out[0]["emotion"] == "anger"
    assert out[0]["polarity"] < 0


def test_analyze_items_uses_text_when_title_short():
    items = [
        {
            "source": "t",
            "title": "News",
            "text": "El gobierno anunció un desastre y una crisis terrible",
        }
    ]
    q = TrendQuery(mode="free", free_topic="x", sentiment_engine="local")
    out = analyze_items(items, q)
    assert out[0]["sentiment_label"] == "negative"
