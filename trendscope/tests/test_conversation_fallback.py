"""Conversation fallbacks when Reddit is blocked."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_hn_comments_parses_algolia():
    from unittest.mock import MagicMock

    from trendscope.scrapers.hn_comments import fetch_hn_comments

    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.raise_for_status = lambda: None
    resp.json = lambda: {
        "hits": [
            {
                "objectID": "1",
                "comment_text": "Gran debate sobre el tema",
                "author": "pg",
                "created_at_i": 1,
                "story_id": 99,
            }
        ]
    }
    session.get.return_value = resp
    with patch("trendscope.scrapers.hn_comments.get_session", return_value=session):
        out = fetch_hn_comments("crypto")
    assert out and out[0]["source"] == "hackernews_comment"
    assert "debate" in out[0]["text"]


def test_conversation_works_without_reddit(isolated_app):
    client = TestClient(isolated_app)
    hn_comments = [
        {
            "source": "hackernews_comment",
            "kind": "comment",
            "reddit_id": "1",
            "text": "Excelente análisis, apoyo la idea",
        },
        {
            "source": "hackernews_comment",
            "kind": "comment",
            "reddit_id": "2",
            "text": "Desastre total y rechazo",
        },
    ]
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        with patch(
            "trendscope.scrapers.reddit_comments.search_public_posts",
            return_value=[],
        ):
            with patch(
                "trendscope.scrapers.hn_comments.fetch_hn_posts",
                return_value=[{"source": "hackernews", "reddit_id": "s1", "title": "T", "kind": "post"}],
            ):
                with patch(
                    "trendscope.scrapers.hn_comments.fetch_hn_comments",
                    return_value=hn_comments,
                ):
                    with patch("trendscope.scrapers.x_replies.run", return_value=[]):
                        resp = client.get("/conversation", params={"topic": "prueba"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["counts"]["comments"] >= 2
    assert "hackernews" in data["sources"]
    assert data["mood"]["emoji"]


def test_dashboard_css_vars_in_js():
    from pathlib import Path

    js = Path("trendscope/static/dashboard.js").read_text(encoding="utf-8")
    assert "getCss('--pos'" in js
    assert "#00d4ff" not in js
