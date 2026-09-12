"""Typed payload helpers and GDELT scraper."""

from unittest.mock import MagicMock, patch

from trendscope.core.query import TrendQuery
from trendscope.models.payload import validate_payload
from trendscope.scrapers import gdelt


def test_validate_ok_payload():
    payload = {
        "meta": {
            "query": {"topic": "ai", "geo": "CO"},
            "sentiment_summary": {
                "positive": 1,
                "negative": 0,
                "neutral": 0,
                "engine": "local",
                "overall": "positive",
            },
            "total_analyzed": 1,
        },
        "top_trends": [{"title": "x", "source": "reddit", "trend_score": 80}],
    }
    assert validate_payload(payload) == []


def test_validate_missing_meta():
    assert validate_payload({}) == ["meta missing or not a dict"]


def test_validate_missing_source_on_trend():
    payload = {
        "meta": {"query": {}, "sentiment_summary": {}, "total_analyzed": 0},
        "top_trends": [{"title": "x"}],
    }
    errors = validate_payload(payload)
    assert any("source" in e for e in errors)


def test_gdelt_registered_in_sOURCES():
    from trendscope.core.pipeline import SOURCES

    names = [n for n, _ in SOURCES]
    assert "GDELT" in names


def test_gdelt_parses_articles():
    fake = {
        "articles": [
            {
                "title": "AI boom in Colombia",
                "url": "https://example.com/a",
                "domain": "example.com",
                "language": "Spanish",
                "seendate": "20260212T120000Z",
            }
        ]
    }
    session = MagicMock()
    session.get.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    session.get.return_value.json = lambda: fake

    with patch("trendscope.scrapers.gdelt.get_session", return_value=session):
        items = gdelt.run(TrendQuery(mode="free", free_topic="AI Colombia"))

    assert items
    assert items[0]["source"] == "gdelt"
    assert "AI boom" in items[0]["title"]
