"""Topic relevance filter and Google News scraper."""

from unittest.mock import MagicMock, patch

from trendscope.core.pipeline import _filter_topic_relevant
from trendscope.core.query import TrendQuery
from trendscope.scrapers import google_news


def test_filter_keeps_topic_matches():
    items = [
        {"title": "Abelardo de la Espriella anuncia plan"},
        {"title": "GPT-5 is here rolling out"},
        {"text": "Opinion sobre Abelardo"},
    ]
    kept = _filter_topic_relevant(items, "Abelardo de la Espriella")
    assert len(kept) == 2


def test_filter_drops_noise():
    items = [{"title": "Restaurant reservations and AI callers"}]
    assert _filter_topic_relevant(items, "Abelardo de la Espriella") == []


def test_google_news_registered():
    from trendscope.core.pipeline import SOURCES

    assert any(n == "Google News" for n, _ in SOURCES)


def test_google_news_parses_rss():
    rss = """<?xml version="1.0"?>
    <rss><channel>
      <item>
        <title>Abelardo de la Espriella habla en Bogotá</title>
        <link>https://news.google.com/x</link>
        <pubDate>Fri, 12 Sep 2026 10:00:00 GMT</pubDate>
      </item>
    </channel></rss>"""
    session = MagicMock()
    resp = MagicMock(status_code=200, text=rss)
    resp.raise_for_status = lambda: None
    session.get.return_value = resp

    with patch("trendscope.scrapers.google_news.get_session", return_value=session):
        items = google_news.run(
            TrendQuery(mode="free", free_topic="Abelardo de la Espriella")
        )
    assert items
    assert items[0]["source"] == "google_news"
    assert "Abelardo" in items[0]["title"]
