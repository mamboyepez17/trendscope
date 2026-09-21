"""Hacker News comments via Algolia (free, no key) — conversation fallback."""

from __future__ import annotations

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery


def fetch_hn_comments(query: str, limit: int = 20) -> list[dict]:
    session = get_session()
    try:
        resp = session.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "tags": "comment", "hitsPerPage": limit},
            timeout=12,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits") or []
        out = []
        for h in hits:
            text = (h.get("comment_text") or "").strip()
            if not text:
                continue
            out.append(
                {
                    "source": "hackernews_comment",
                    "reddit_id": h.get("objectID", ""),
                    "post_id": str(h.get("story_id", "")),
                    "title": text[:200],
                    "text": text[:500],
                    "author": h.get("author", ""),
                    "score": 0,
                    "created_utc": h.get("created_at_i", 0),
                    "permalink": f"https://news.ycombinator.com/item?id={h.get('objectID','')}",
                    "kind": "comment",
                }
            )
        logger.info(f"HN comments '{query}': {len(out)}")
        return out
    except Exception as e:
        logger.warning(f"HN comments '{query}': {e}")
        return []


def fetch_hn_posts(query: str, limit: int = 8) -> list[dict]:
    session = get_session()
    try:
        resp = session.get(
            "https://hn.algolia.com/api/v1/search",
            params={
                "query": query,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": "points>3",
            },
            timeout=12,
        )
        resp.raise_for_status()
        hits = resp.json().get("hits") or []
        out = []
        for h in hits:
            title = (h.get("title") or h.get("story_title") or "").strip()
            if not title:
                continue
            oid = h.get("objectID", "")
            out.append(
                {
                    "source": "hackernews",
                    "reddit_id": oid,
                    "title": title[:250],
                    "text": (h.get("story_text") or title)[:300],
                    "author": h.get("author", ""),
                    "score": h.get("points", 0),
                    "comments": h.get("num_comments", 0),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={oid}",
                    "permalink": f"https://news.ycombinator.com/item?id={oid}",
                    "created_utc": h.get("created_at_i", 0),
                    "kind": "post",
                }
            )
        logger.info(f"HN posts '{query}': {len(out)}")
        return out
    except Exception as e:
        logger.warning(f"HN posts '{query}': {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    kw = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not kw:
        return []
    return fetch_hn_comments(kw, limit=15)
