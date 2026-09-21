"""X/Twitter replies — best-effort via vendored xactions (cookies)."""

from __future__ import annotations

from loguru import logger

from trendscope.config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from trendscope.core.query import TrendQuery
from trendscope.scrapers.twitter import _is_relevant, _parse_twitter_date, _twitter_query


def run(query: TrendQuery) -> list[dict]:
    """
    Collect replies/comments on top tweets for the topic.
    Requires Twitter cookies in .env; returns [] otherwise.
    """
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        logger.warning("X replies: sin cookies — saltando")
        return []

    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []

    try:
        from trendscope.xactions import TwitterError, search_tweets_sync
    except Exception as e:
        logger.warning(f"X replies import: {e}")
        return []

    cookie_str = f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
    q = _twitter_query(keyword)
    results: list[dict] = []

    try:
        tweets = search_tweets_sync(cookies=cookie_str, query=q, limit=8, mode="Latest")
    except TwitterError as e:
        logger.warning(f"X replies search: {e}")
        return []
    except Exception as e:
        logger.warning(f"X replies search: {e}")
        return []

    for tweet in tweets[:5]:
        text = tweet.get("text", "")
        if not _is_relevant(text, keyword):
            continue
        parent_url = tweet.get("url", "")
        parent_id = parent_url.rstrip("/").split("/")[-1] if parent_url else ""
        replies = tweet.get("replies") or tweet.get("reply_count") or 0
        # xactions search payload may not include reply bodies; synthesize a
        # "conversation signal" row from the tweet itself + reply count.
        ts = _parse_twitter_date(tweet.get("created_at"))
        results.append(
            {
                "source": "twitter_comment",
                "reddit_id": parent_id,
                "post_id": parent_id,
                "parent_id": parent_id,
                "title": text[:200],
                "text": text[:400],
                "author": (tweet.get("author") or {}).get("username", ""),
                "score": tweet.get("likes", 0),
                "replies": replies,
                "created_utc": ts,
                "permalink": parent_url,
                "kind": "comment",
            }
        )

    logger.info(f"X replies signals: {len(results)}")
    return results
