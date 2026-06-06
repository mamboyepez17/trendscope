# scrapers/tweetclaw.py
# Optional local JSON source produced by TweetClaw or another Xquik-compatible exporter.
import json
from pathlib import Path
from typing import Any

from loguru import logger

from config import TWEETCLAW_RESULTS_FILE
from core.query import TrendQuery


def _to_int(value: Any) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(str(value).replace(",", "").strip())
    except ValueError:
        return 0


def _first_text(item: dict, *names: str) -> str:
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _first_int(item: dict, *names: str) -> int:
    for name in names:
        value = item.get(name)
        number = _to_int(value)
        if number > 0:
            return number
    return 0


def _nested_followers(item: dict) -> int:
    for key in ("author", "user"):
        value = item.get(key)
        if isinstance(value, dict):
            followers = _first_int(
                value,
                "followers",
                "followers_count",
                "follower_count",
                "user_followers",
            )
            if followers > 0:
                return followers
    return _first_int(item, "user_followers", "author_followers", "followers")


def _extract_items(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    for key in ("tweets", "items", "results", "data"):
        value = payload.get(key)
        nested = _extract_items(value)
        if nested:
            return nested

    return []


def _tweet_url(item: dict) -> str:
    url = _first_text(item, "url", "tweet_url", "permalink")
    if url:
        return url

    tweet_id = _first_text(item, "id", "id_str", "tweet_id")
    if tweet_id:
        return f"https://twitter.com/i/web/status/{tweet_id}"
    return ""


def _normalize(item: dict, query: TrendQuery) -> dict | None:
    text = _first_text(item, "text", "full_text", "content", "body")
    if not text:
        return None

    keyword = ""
    lowered = text.lower()
    for candidate in query.keywords:
        if candidate.lower() in lowered:
            keyword = candidate
            break

    if not keyword:
        keyword = query.free_topic or query.category or "tweetclaw"

    return {
        "source": "tweetclaw",
        "keyword": keyword,
        "text": text[:200],
        "likes": _first_int(item, "likes", "like_count", "favorite_count", "favourites"),
        "retweets": _first_int(item, "retweets", "retweet_count", "reposts", "repost_count"),
        "replies": _first_int(item, "replies", "reply_count", "comments"),
        "user_followers": _nested_followers(item),
        "url": _tweet_url(item),
    }


def run(query: TrendQuery) -> list[dict]:
    """Load TweetClaw/Xquik tweet results from a local JSON file."""
    if not TWEETCLAW_RESULTS_FILE:
        logger.info("TweetClaw: TWEETCLAW_RESULTS_FILE no configurado, saltando fuente")
        return []

    path = Path(TWEETCLAW_RESULTS_FILE).expanduser()
    if not path.exists():
        logger.warning(f"TweetClaw: archivo no encontrado: {path}")
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        logger.warning(f"TweetClaw: JSON invalido en {path}: {exc}")
        return []

    results = [
        normalized
        for item in _extract_items(payload)
        if (normalized := _normalize(item, query)) is not None
    ]
    logger.info(f"TweetClaw total: {len(results)} tweets desde {path}")
    return results
