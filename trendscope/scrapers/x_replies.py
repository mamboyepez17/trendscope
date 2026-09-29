"""X/Twitter: respuestas REALES a los tweets más comentados del tema.

1. Busca tweets recientes del tema (modo Top: los que más conversación tienen).
2. Para los que tienen respuestas, trae la conversación con
   `get_tweet_replies_sync` (endpoint TweetDetail de xactions-py).
3. Devuelve solo las respuestas (no el tweet original ni el hilo de arriba).

Requiere cookies de X en .env; sin ellas devuelve [].
"""

from __future__ import annotations

from loguru import logger

from trendscope.core.query import TrendQuery
from trendscope.scrapers.twitter import _is_relevant, _parse_twitter_date, _twitter_query
from trendscope.scrapers.x_client import cookie_string, xactions


def _reply_row(reply: dict, parent: dict) -> dict | None:
    text = (reply.get("text") or "").strip()
    if not text:
        return None
    author = reply.get("author") or {}
    return {
        "source": "twitter_comment",
        "reddit_id": str(reply.get("id") or ""),
        "post_id": str(parent.get("id") or ""),
        "parent_id": str(parent.get("id") or ""),
        "title": text[:200],
        "text": text[:500],
        "author": author.get("username", "") if isinstance(author, dict) else str(author),
        "score": reply.get("likes", 0),
        "likes": reply.get("likes", 0),
        "replies": reply.get("replies", 0),
        "lang": reply.get("lang"),
        "created_utc": _parse_twitter_date(reply.get("created_at")),
        "permalink": reply.get("url", ""),
        "kind": "comment",
    }


def run(query: TrendQuery, max_threads: int = 5, replies_per_thread: int = 25) -> list[dict]:
    cookies = cookie_string()
    if not cookies:
        logger.warning("X replies: sin cookies — saltando")
        return []

    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []

    from trendscope.core.dates import since_day

    xa = xactions()
    q = f"{_twitter_query(keyword)} since:{since_day(query.max_age_days)}"
    try:
        tweets = xa.search_tweets_sync(cookies=cookies, query=q, limit=30, mode="Top")
    except Exception as e:
        logger.warning(f"X replies search: {e}")
        return []

    parents = [
        t for t in tweets
        if _is_relevant(t.get("text", ""), keyword) and (t.get("replies") or 0) > 0 and t.get("id")
    ]
    parents.sort(key=lambda t: t.get("replies") or 0, reverse=True)

    get_replies = getattr(xa, "get_tweet_replies_sync", None)
    results: list[dict] = []
    seen: set[str] = set()
    if get_replies is None:
        logger.warning("xactions sin get_tweet_replies_sync — actualiza xactions-py")
        return []

    for parent in parents[:max_threads]:
        pid = str(parent["id"])
        try:
            convo = get_replies(cookies, pid, limit=replies_per_thread + 5)
        except Exception as e:
            logger.warning(f"X replies {pid}: {e}")
            continue
        for reply in convo:
            rid = str(reply.get("id") or "")
            # Fuera el tweet original, lo repetido y lo que no es respuesta
            if not rid or rid == pid or rid in seen or not reply.get("is_reply", True):
                continue
            row = _reply_row(reply, parent)
            if row:
                seen.add(rid)
                results.append(row)

    logger.info(f"X replies: {len(results)} respuestas de {min(len(parents), max_threads)} hilos")
    return results
