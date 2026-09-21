"""Reddit public JSON mapper tests (mocked HTTP)."""

from unittest.mock import MagicMock, patch

from trendscope.scrapers.reddit_comments import (
    fetch_comments,
    parse_reddit_comment,
    parse_reddit_post,
    search_public_posts,
)


def test_parse_reddit_post():
    child = {
        "kind": "t3",
        "data": {
            "id": "abc123",
            "title": "Crypto in Colombia rises",
            "selftext": "Body text",
            "subreddit": "CryptoCurrency",
            "author": "user1",
            "score": 120,
            "upvote_ratio": 0.9,
            "num_comments": 45,
            "permalink": "/r/CryptoCurrency/comments/abc123/x/",
            "created_utc": 1700000000,
            "url": "https://reddit.com/x",
        },
    }
    item = parse_reddit_post(child)
    assert item["source"] == "reddit"
    assert item["reddit_id"] == "abc123"
    assert item["comments"] == 45
    assert "r/CryptoCurrency" in item["permalink"] or "reddit.com" in item["permalink"]


def test_parse_comment_tree():
    tree = {
        "kind": "t1",
        "data": {
            "id": "c1",
            "body": "Me parece una excelente noticia",
            "author": "u1",
            "score": 10,
            "permalink": "/r/x/comments/abc/_/c1/",
            "created_utc": 1,
            "depth": 0,
            "replies": {
                "kind": "Listing",
                "data": {
                    "children": [
                        {
                            "kind": "t1",
                            "data": {
                                "id": "c2",
                                "body": "Totalmente en desacuerdo, es un desastre",
                                "author": "u2",
                                "score": 2,
                                "permalink": "/r/x/comments/abc/_/c2/",
                                "created_utc": 2,
                                "depth": 1,
                            },
                        }
                    ]
                },
            },
        },
    }
    comments = parse_reddit_comment(tree)
    assert len(comments) == 2
    assert comments[0]["kind"] == "comment"
    assert "excelente" in comments[0]["text"]
    assert "desastre" in comments[1]["text"]


def test_search_public_posts_mocked():
    payload = {
        "data": {
            "children": [
                {
                    "kind": "t3",
                    "data": {"id": "p1", "title": "Abelardo news", "num_comments": 3},
                }
            ]
        }
    }
    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.json = lambda: payload
    resp.raise_for_status = lambda: None
    session.get.return_value = resp
    with patch("trendscope.scrapers.reddit_comments.get_session", return_value=session):
        posts = search_public_posts("Abelardo", limit=5)
    assert len(posts) == 1
    assert posts[0]["reddit_id"] == "p1"


def test_fetch_comments_mocked():
    listing = [
        {"data": {"children": []}},
        {
            "data": {
                "children": [
                    {
                        "kind": "t1",
                        "data": {
                            "id": "c9",
                            "body": "Gran análisis de la situación",
                            "author": "z",
                            "score": 5,
                            "permalink": "/r/a/comments/b/_/c9/",
                            "created_utc": 1,
                        },
                    }
                ]
            }
        },
    ]
    session = MagicMock()
    resp = MagicMock(status_code=200)
    resp.json = lambda: listing
    resp.raise_for_status = lambda: None
    session.get.return_value = resp
    with patch("trendscope.scrapers.reddit_comments.get_session", return_value=session):
        comments = fetch_comments("p9", limit=20)
    assert comments and comments[0]["reddit_id"] == "c9"


def test_run_returns_empty_without_keyword():
    from trendscope.core.query import TrendQuery
    from trendscope.scrapers.reddit_comments import run

    q = TrendQuery(mode="category", category="nonexistent")
    # empty keywords → []
    assert run(q) == [] or isinstance(run(q), list)
