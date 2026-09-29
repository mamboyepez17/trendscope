"""Frescura: parseo de fechas, ventana global y filtros por fuente."""

import time
from unittest.mock import MagicMock, patch

from trendscope.core.dates import parse_date, reddit_time_filter
from trendscope.core.pipeline import apply_freshness
from trendscope.core.query import TrendQuery


def test_parse_date_formats():
    assert parse_date("Tue, 29 Sep 2026 10:00:00 GMT") is not None
    assert parse_date("2026-09-29T10:00:00Z") is not None
    assert parse_date("20260929T100000Z") is not None
    assert parse_date(1790000000) == 1790000000.0
    assert parse_date("") is None
    assert parse_date("hace un rato") is None


def test_old_items_dropped_recent_kept():
    now = time.time()
    items = [
        {"source": "google_news", "title": "hoy", "published_at": time.strftime(
            "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now - 3600))},
        {"source": "google_news", "title": "hace 2 años", "published_at": "Mon, 01 Jan 2024 10:00:00 GMT"},
        {"source": "twitter", "title": "tweet viejo", "created_utc": now - 40 * 86400},
        {"source": "google_trends_rss", "title": "trending ahora"},
        {"source": "bing_news", "title": "sin fecha"},
    ]
    kept, info = apply_freshness(items, 7)
    titles = {i["title"] for i in kept}
    assert titles == {"hoy", "trending ahora", "sin fecha"}
    assert info["dropped_old"] == 2
    assert info["undated"] == 1
    # La fecha RSS quedó normalizada → ahora sí recibe bonus de recencia
    assert next(i for i in kept if i["title"] == "hoy")["created_utc"] > now - 7200


def test_reddit_time_filter():
    assert reddit_time_filter(1) == "day"
    assert reddit_time_filter(7) == "week"
    assert reddit_time_filter(30) == "month"


def test_google_news_asks_for_recent_only():
    from trendscope.scrapers import google_news

    session = MagicMock()
    resp = MagicMock()
    resp.text = "<rss><channel></channel></rss>"
    session.get.return_value = resp
    q = TrendQuery(mode="free", free_topic="petro", max_age_days=3)
    with patch("trendscope.scrapers.google_news.get_session", return_value=session):
        google_news.run(q)
    url = session.get.call_args_list[0].args[0]
    assert "when%3A3d" in url


def test_twitter_query_has_since():
    from trendscope.scrapers import twitter

    captured = {}

    def fake_search(cookies, query, limit, mode):
        captured.setdefault("queries", []).append(query)
        return []

    q = TrendQuery(mode="free", free_topic="petro", max_age_days=7)
    with patch.object(twitter, "TWITTER_AUTH_TOKEN", "a"), patch.object(twitter, "TWITTER_CT0", "b"):
        with patch("trendscope.xactions.search_tweets_sync", side_effect=fake_search):
            twitter.run(q)
    assert captured["queries"] and all("since:" in x for x in captured["queries"])
