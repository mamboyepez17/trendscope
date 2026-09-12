"""Recency scoring and Twitter date parsing."""

import time
from datetime import datetime, timezone

from trendscope.analyzer.scorer import _recency_bonus, score_item
from trendscope.core.query import TrendQuery
from trendscope.scrapers.twitter import _parse_twitter_date


def test_parse_twitter_date():
    ts = _parse_twitter_date("Wed Oct 10 20:19:24 +0000 2018")
    assert ts is not None
    assert ts < time.time()  # in the past


def test_recent_item_scores_higher_than_old_same_engagement():
    now = time.time()
    recent = {
        "source": "twitter",
        "title": "Abelardo de la Espriella news",
        "likes": 10,
        "retweets": 2,
        "views": 5000,
        "created_utc": now - 3600,
        "sentiment_label": "neutral",
    }
    old = dict(recent)
    old["created_utc"] = now - 40 * 86400
    q = TrendQuery(mode="free", free_topic="Abelardo de la Espriella")
    assert score_item(recent, q) > score_item(old, q)
    assert _recency_bonus(recent) >= 14
    assert _recency_bonus(old) < 0


def test_youtube_relative_date_parse():
    from trendscope.scrapers.youtube import _parse_published_utc

    ts = _parse_published_utc("Hace 2 días")
    assert ts is not None
    assert abs((time.time() - ts) - 2 * 86400) < 120
    assert _parse_published_utc("Streamed 3 hours ago") is not None
