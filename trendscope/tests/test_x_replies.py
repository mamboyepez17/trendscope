"""Respuestas reales de X vía xactions-py (get_tweet_replies_sync)."""

from unittest.mock import MagicMock, patch

from trendscope.core.query import TrendQuery
from trendscope.scrapers import x_replies


def _tweet(tid, text, replies=0, is_reply=False, likes=0, user="u"):
    return {"id": tid, "text": text, "replies": replies, "is_reply": is_reply, "likes": likes,
            "author": {"username": user}, "created_at": "Tue Sep 29 10:00:00 +0000 2026",
            "url": f"https://x.com/i/web/status/{tid}"}


def _fake_xa():
    search = MagicMock(return_value=[
        _tweet("1", "La reforma a la salud avanza", replies=40),
        _tweet("2", "Otro tema sin relación", replies=99),
        _tweet("3", "Reforma a la salud: sin respuestas", replies=0),
    ])
    convo = MagicMock(return_value=[
        _tweet("1", "La reforma a la salud avanza", replies=40),  # tweet focal
        _tweet("10", "Qué rabia con esta reforma 😡", is_reply=True, likes=12, user="ana"),
        _tweet("11", "Por fin, me encanta", is_reply=True, user="leo"),
        _tweet("10", "Qué rabia con esta reforma 😡", is_reply=True, user="ana"),  # repetido
    ])
    return MagicMock(search_tweets_sync=search, get_tweet_replies_sync=convo), search, convo


def test_returns_only_real_replies_of_relevant_threads():
    xa, search, convo = _fake_xa()
    with patch("trendscope.scrapers.x_replies.cookie_string", return_value="auth_token=a; ct0=b"):
        with patch("trendscope.scrapers.x_replies.xactions", return_value=xa):
            rows = x_replies.run(TrendQuery(mode="free", free_topic="reforma a la salud"))
    # Solo se abre el hilo relevante con respuestas (id 1)
    convo.assert_called_once()
    assert convo.call_args.args[1] == "1"
    assert [r["reddit_id"] for r in rows] == ["10", "11"]
    assert all(r["source"] == "twitter_comment" and r["kind"] == "comment" for r in rows)
    assert rows[0]["author"] == "ana" and rows[0]["created_utc"]
    assert "since:" in search.call_args.kwargs["query"]


def test_no_cookies_returns_empty():
    with patch("trendscope.scrapers.x_replies.cookie_string", return_value=None):
        assert x_replies.run(TrendQuery(mode="free", free_topic="x")) == []
