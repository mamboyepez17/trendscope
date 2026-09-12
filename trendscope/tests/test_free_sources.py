"""Free no-API sources: Bing News, Wikipedia, Bluesky."""

from unittest.mock import MagicMock, patch

from trendscope.core.query import TrendQuery
from trendscope.scrapers import bing_news, bluesky, wikipedia


def test_sources_registered():
    from trendscope.core.pipeline import SOURCES

    names = {n for n, _ in SOURCES}
    assert {"Bing News", "Wikipedia", "Bluesky"} <= names


def test_bing_news_parses_rss():
    rss = """<?xml version="1.0"?><rss><channel>
    <item><title>Abelardo en noticias</title><link>https://bing.com/x</link>
    <pubDate>Fri, 12 Sep 2026 08:00:00 GMT</pubDate></item></channel></rss>"""
    session = MagicMock()
    resp = MagicMock(status_code=200, text=rss)
    resp.raise_for_status = lambda: None
    session.get.return_value = resp
    with patch("trendscope.scrapers.bing_news.get_session", return_value=session):
        items = bing_news.run(TrendQuery(mode="free", free_topic="Abelardo"))
    assert items and items[0]["source"] == "bing_news"


def test_wikipedia_parses_json():
    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json = lambda: {
        "query": {"search": [{"title": "Colombia", "snippet": "país de América", "wordcount": 100}]}
    }
    session.get.return_value = resp
    with patch("trendscope.scrapers.wikipedia.get_session", return_value=session):
        items = wikipedia.run(TrendQuery(mode="free", free_topic="Colombia"))
    assert items and items[0]["source"] == "wikipedia"
    assert "Colombia" in items[0]["url"]


def test_bluesky_parses_posts():
    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json = lambda: {
        "posts": [
            {
                "uri": "at://did:plc:x/app.bsky.feed.post/abc",
                "likeCount": 3,
                "author": {"handle": "user.bsky.social", "followersCount": 10},
                "record": {"text": "Hola Abelardo", "createdAt": "2026-09-12T10:00:00Z"},
            }
        ]
    }
    session.get.return_value = resp
    with patch("trendscope.scrapers.bluesky.get_session", return_value=session):
        items = bluesky.run(TrendQuery(mode="free", free_topic="Abelardo"))
    assert items and items[0]["source"] == "bluesky"
    assert "bsky.app" in items[0]["url"]
