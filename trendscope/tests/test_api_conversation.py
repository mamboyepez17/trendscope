"""API conversation + discover endpoints."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _client(isolated_app):
    return TestClient(isolated_app)


def test_discover_returns_topics(isolated_app):
    client = _client(isolated_app)
    fake = [
        {"source": "gt", "keyword": "bitcoin", "approx_traffic": "50000+"},
        {"source": "gt", "keyword": "elecciones", "approx_traffic": "20000+"},
    ]
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        with patch(
            "trendscope.scrapers.google_trends._fetch_rss", return_value=fake
        ):
            resp = client.get("/discover", params={"geo": "CO"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["geo"] == "CO"
    assert data["topics"][0]["topic"] == "bitcoin"


def test_conversation_mood_endpoint(isolated_app):
    client = _client(isolated_app)
    posts = [
        {
            "source": "reddit",
            "reddit_id": "abc",
            "title": "Noticia Abelardo",
            "num_comments": 2,
            "kind": "post",
        }
    ]
    comments = [
        {
            "source": "reddit_comment",
            "kind": "comment",
            "reddit_id": "c1",
            "text": "Excelente apoyo total al anuncio",
        },
        {
            "source": "reddit_comment",
            "kind": "comment",
            "reddit_id": "c2",
            "text": "Desastre y rechazo a esta corrupción",
        },
    ]
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        with patch(
            "trendscope.scrapers.reddit_comments.search_public_posts",
            return_value=posts,
        ):
            with patch(
                "trendscope.scrapers.reddit_comments.fetch_comments",
                return_value=comments,
            ):
                with patch(
                    "trendscope.scrapers.x_replies.run", return_value=[]
                ):
                    with patch(
                        "trendscope.scrapers.hn_comments.fetch_hn_posts",
                        return_value=[],
                    ):
                        with patch(
                            "trendscope.scrapers.hn_comments.fetch_hn_comments",
                            return_value=comments,
                        ):
                            resp = client.get(
                                "/conversation",
                                params={"topic": "Abelardo", "limit": 3},
                            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["topic"] == "Abelardo"
    assert data["mood"]["total"] >= 2
    assert "emoji" in data["mood"]
    assert "acceptance_score" in data["mood"]


def test_conversation_isolated_app_has_mood_emoji():
    from trendscope.analyzer.conversation import analyze_conversation

    s = analyze_conversation(
        [{"kind": "comment", "text": "imbécil basura mierda"}]
    )
    assert s["emoji"]
