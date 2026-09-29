"""Reddit public JSON mapper — posts + comments (no paid API).

Uses www.reddit.com/*.json with a proper User-Agent and polite delays.
Never raises into the pipeline: returns [] and logs warnings.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery
from trendscope.settings import settings

UA = "TrendScope/1.8 (research; comment intelligence)"

_SORTS = ("relevance", "new", "top")


def _session():
    s = get_session()
    s.headers["User-Agent"] = settings.reddit_user_agent or UA
    return s


def _get_json(url: str, params: dict | None = None) -> dict | None:
    try:
        resp = _session().get(url, params=params, timeout=15)
        if resp.status_code == 429:
            retry = int(resp.headers.get("Retry-After", "5") or 5)
            logger.warning(f"Reddit 429, backoff {retry}s")
            time.sleep(min(retry, 30))
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"Reddit GET {url}: {e}")
        return None


def parse_reddit_post(child: dict) -> dict | None:
    """Map Reddit listing child → TrendScope-ish item."""
    data = child.get("data") or {}
    pid = data.get("id")
    title = (data.get("title") or "").strip()
    if not pid or not title:
        return None
    return {
        "source": "reddit",
        "reddit_id": pid,
        "title": title[:250],
        "text": (data.get("selftext") or title)[:400],
        "subreddit": data.get("subreddit", ""),
        "author": data.get("author", ""),
        "score": data.get("score", 0),
        "upvote_ratio": data.get("upvote_ratio", 0.5),
        "comments": data.get("num_comments", 0),
        "url": data.get("url", ""),
        "permalink": f"https://www.reddit.com{data.get('permalink', '')}"
        if data.get("permalink")
        else "",
        "created_utc": data.get("created_utc", 0),
        "kind": "post",
    }


def parse_reddit_comment(child: dict, depth: int = 0) -> list[dict]:
    """Flatten comment tree nodes → list of comment dicts."""
    out: list[dict] = []
    if not isinstance(child, dict):
        return out
    kind = child.get("kind")
    data = child.get("data") or {}
    if kind == "t1" or data.get("body"):
        body = (data.get("body") or "").strip()
        if body and body not in ("[deleted]", "[removed]"):
            cid = data.get("id") or data.get("name") or ""
            out.append(
                {
                    "source": "reddit_comment",
                    "reddit_id": cid,
                    "post_id": data.get("link_id", "").replace("t3_", ""),
                    "parent_id": data.get("parent_id", ""),
                    "title": body[:200],
                    "text": body[:500],
                    "author": data.get("author", ""),
                    "score": data.get("score", 0),
                    "controversiality": data.get("controversiality", 0),
                    "created_utc": data.get("created_utc", 0),
                    "depth": data.get("depth", depth),
                    "permalink": f"https://www.reddit.com{data.get('permalink', '')}"
                    if data.get("permalink")
                    else "",
                    "kind": "comment",
                }
            )
        replies = data.get("replies")
        if isinstance(replies, dict):
            children = (replies.get("data") or {}).get("children") or []
            for ch in children:
                out.extend(parse_reddit_comment(ch, depth + 1))
    elif kind == "more":
        return out
    else:
        # listing wrapper
        children = (data.get("children") if isinstance(data, dict) else None) or child.get(
            "children"
        )
        if isinstance(children, list):
            for ch in children:
                out.extend(parse_reddit_comment(ch, depth))
    return out


# ── reddit-actions (github.com/mamboyepez17/reddit-actions) ──────────────────
# Si está instalado se usa primero: maneja User-Agent, reintentos y cookies de
# sesión (REDDIT_SESSION_COOKIE / REDDIT_COOKIE_HEADER) cuando Reddit da 403.


def _reddit_actions():
    try:
        import reddit_actions  # noqa: F401

        # reddit-actions lee las cookies del entorno; las de .env no están ahí
        import os

        from trendscope.settings import settings

        for env, val in (("REDDIT_SESSION_COOKIE", settings.reddit_session_cookie),
                         ("REDDIT_COOKIE_HEADER", settings.reddit_cookie_header)):
            if val and not os.environ.get(env):
                os.environ[env] = val

        return reddit_actions
    except ImportError:
        return None


def _post_from_model(p: Any) -> dict:
    return {
        "source": "reddit",
        "reddit_id": p.id,
        "title": (p.title or "")[:250],
        "text": (p.selftext or p.title or "")[:400],
        "subreddit": p.subreddit,
        "author": p.author,
        "score": p.score,
        "upvote_ratio": p.upvote_ratio,
        "comments": p.num_comments,
        "url": p.url,
        "permalink": p.full_permalink,
        "created_utc": p.created_utc,
        "kind": "post",
    }


def _comment_from_model(c: Any, post_id: str) -> dict | None:
    body = (c.body or "").strip()
    if not body or body in ("[deleted]", "[removed]"):
        return None
    return {
        "source": "reddit_comment",
        "reddit_id": c.id,
        "post_id": post_id,
        "parent_id": c.parent_id,
        "title": body[:200],
        "text": body[:500],
        "author": c.author,
        "score": c.score,
        "controversiality": c.controversiality,
        "created_utc": c.created_utc,
        "depth": c.depth,
        "permalink": c.full_permalink,
        "kind": "comment",
    }


def search_public_posts(
    query: str,
    subreddit: str | None = None,
    limit: int = 10,
    max_age_days: float = 7,
) -> list[dict]:
    """Search Reddit posts (reddit-actions si está instalado, si no JSON público).

    Solo posts de la ventana de frescura (parámetro `t` de Reddit)."""
    from trendscope.core.dates import reddit_time_filter

    t = reddit_time_filter(max_age_days)
    ra = _reddit_actions()
    if ra is not None:
        try:
            posts = ra.search_posts(
                query, subreddit=subreddit, sort="relevance", limit=limit,
                extra_params={"t": t},
            )
            out = [_post_from_model(p) for p in posts]
            logger.info(f"Reddit (reddit-actions) '{query}': {len(out)} posts")
            return out
        except Exception as e:
            logger.warning(f"reddit-actions search falló → JSON público: {e}")

    results: list[dict] = []
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {"q": query, "restrict_sr": 1, "sort": "relevance", "limit": limit,
                  "raw_json": 1, "t": t}
    else:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": "relevance", "limit": limit, "raw_json": 1, "t": t}
    data = _get_json(url, params)
    if not data:
        return []
    for child in (data.get("data") or {}).get("children") or []:
        item = parse_reddit_post(child)
        if item:
            results.append(item)
    logger.info(f"Reddit search '{query}': {len(results)} posts")
    return results


def fetch_comments(post_id: str, limit: int = 40) -> list[dict]:
    """Fetch public comments for a post id (t3 id without prefix)."""
    pid = post_id.replace("t3_", "")
    ra = _reddit_actions()
    if ra is not None:
        try:
            comments = ra.get_comments(pid, limit=limit, depth=3)
            out = [c for c in (_comment_from_model(x, pid) for x in comments) if c]
            logger.info(f"Reddit comments (reddit-actions) {pid}: {len(out)}")
            return out[:limit]
        except Exception as e:
            logger.warning(f"reddit-actions comments falló → JSON público: {e}")

    url = f"https://www.reddit.com/comments/{pid}.json"
    params = {"limit": limit, "depth": 3, "raw_json": 1, "sort": "top"}
    data = _get_json(url, params)
    if not data or not isinstance(data, list) or len(data) < 2:
        return []
    comments_listing = data[1]
    children = (comments_listing.get("data") or {}).get("children") or []
    out: list[dict] = []
    for ch in children:
        out.extend(parse_reddit_comment(ch))
    out = out[:limit]
    logger.info(f"Reddit comments {pid}: {len(out)}")
    return out


def run(query: TrendQuery) -> list[dict]:
    """Pipeline entry: posts about the topic (comments fetched separately)."""
    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []
    return search_public_posts(keyword, limit=8, max_age_days=query.max_age_days)
