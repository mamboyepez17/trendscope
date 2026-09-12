"""Bluesky public search — free, no API key (public.api.bsky.app)."""

from __future__ import annotations

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery

SEARCH = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def run(query: TrendQuery) -> list[dict]:
    session = get_session()
    results: list[dict] = []
    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []
    try:
        resp = session.get(
            SEARCH,
            params={"q": keyword, "limit": 15, "sort": "latest"},
            timeout=12,
            headers={"User-Agent": "TrendScope/1.8"},
        )
        resp.raise_for_status()
        posts = resp.json().get("posts", [])
        for p in posts:
            record = p.get("record") or {}
            text = (record.get("text") or "").strip()
            if not text:
                continue
            author = (p.get("author") or {}).get("handle", "")
            uri = p.get("uri", "")
            # at://did:plc:xxx/app.bsky.feed.post/yyy → https://bsky.app/profile/handle/post/id
            post_id = uri.rsplit("/", 1)[-1] if uri else ""
            url = f"https://bsky.app/profile/{author}/post/{post_id}" if author and post_id else ""
            results.append(
                {
                    "source": "bluesky",
                    "keyword": keyword,
                    "title": text[:200],
                    "text": text[:200],
                    "url": url,
                    "likes": p.get("likeCount", 0),
                    "replies": p.get("replyCount", 0),
                    "reposts": p.get("repostCount", 0),
                    "user_followers": (p.get("author") or {}).get("followersCount", 0),
                    "created_at": record.get("createdAt"),
                    "published_at": record.get("createdAt"),
                }
            )
        logger.info(f"Bluesky '{keyword}': {len(results)} posts")
    except Exception as e:
        logger.warning(f"Bluesky '{keyword}': {e}")
    return results
