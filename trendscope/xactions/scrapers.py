"""
XActions-PY — Scrapers
Replicas en Python de los scrapers HTTP de XActions.

v1.2.0:
  - Nuevos scrapers: replies, favoriters, retweeters, bookmarks, likes de usuario,
    home timeline y trending topics.
  - Mejor manejo de errores (ForbiddenError, RateLimitError).
  - Wrappers sincronos que cierran automáticamente el cliente HTTP.
  - Cache interna de user_id para reducir lookups repetidos.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from .client import (
    DEFAULT_FEATURES,
    ForbiddenError,
    NotFoundError,
    TwitterClient,
    TwitterError,
)

_log = logging.getLogger(__name__)

# Tamaños de página GraphQL (X acepta más de 20 en varios endpoints;
# search suele seguir capado a 20).
PAGE_SIZE_USERS = 100       # Followers / Following
PAGE_SIZE_ENGAGEMENT = 50   # Favoriters / Retweeters
PAGE_SIZE_TWEETS = 40       # UserTweets / replies / likes / home
PAGE_SIZE_BOOKMARKS = 40
PAGE_SIZE_SEARCH = 20       # SearchTimeline: la API limita a ~20

# ─── Cache de user_id (evita lookups repetidos de perfil) ─────────────────────

_USER_ID_CACHE: dict[str, str] = {}


def clear_user_id_cache() -> None:
    """Limpia el cache de username -> user_id."""
    _USER_ID_CACHE.clear()


# ─── Helpers de parseo ────────────────────────────────────────────────────────

def _upgrade_avatar(url: str | None) -> str | None:
    if not url:
        return None
    return url.replace("_normal", "_400x400")


def _safe_int(val: Any, default: int = 0) -> int:
    """Convierte cualquier valor a int de forma segura."""
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def parse_user(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Convierte un resultado GraphQL de usuario al formato XActions."""
    if not raw or raw.get("__typename") == "UserUnavailable":
        return None
    legacy = raw.get("legacy", {})
    return {
        "id": raw.get("rest_id"),
        "username": legacy.get("screen_name"),
        "name": legacy.get("name"),
        "bio": legacy.get("description"),
        "verified": raw.get("is_blue_verified", legacy.get("verified", False)),
        "avatar": _upgrade_avatar(legacy.get("profile_image_url_https")),
        "followers": _safe_int(legacy.get("followers_count", 0)),
        "following": _safe_int(legacy.get("friends_count", 0)),
        "tweets_count": _safe_int(legacy.get("statuses_count", 0)),
        "protected": legacy.get("protected", False),
        "created_at": legacy.get("created_at"),
        "location": legacy.get("location"),
        "website": (legacy.get("entities", {})
                        .get("url", {})
                        .get("urls", [{}])[0]
                        .get("expanded_url")),
        "platform": "twitter",
    }


def parse_tweet(raw: dict[str, Any], author: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """
    Convierte un resultado GraphQL de tweet al formato XActions.
    Maneja multiples variantes de estructura que Twitter devuelve:
    - TweetWithVisibilityResults
    - Tweet
    - TweetTombstone (descartado)
    """
    if not raw:
        return None

    # El tweet puede venir directo o dentro de tweet_results.result
    result = raw.get("tweet_results", {}).get("result") if "tweet_results" in raw else raw
    if not result:
        # A veces viene como itemContent con tweet_results anidado
        result = raw.get("itemContent", {}).get("tweet_results", {}).get("result", raw)

    if not result or result.get("__typename") == "TweetTombstone":
        return None

    # TweetWithVisibilityResults tiene el tweet real dentro de .tweet
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet", result)

    core = result.get("core", {})
    legacy = result.get("legacy", {})
    metrics = result.get("public_metrics") or {}

    # El id puede estar en varios lugares
    tweet_id = result.get("rest_id") or legacy.get("id_str") or raw.get("rest_id")
    if not tweet_id:
        return None

    # Author: priorizar el que se pasa, sino extraer del core
    tweet_author = author
    if not tweet_author:
        user_result = core.get("user_results", {}).get("result", {})
        if user_result:
            tweet_author = parse_user(user_result)

    # Texto: full_text es el completo, text es el truncado
    text = legacy.get("full_text") or legacy.get("text") or ""

    # Metricas: pueden venir en legacy o en public_metrics (API v2)
    likes = _safe_int(legacy.get("favorite_count", 0)) or _safe_int(metrics.get("like_count", 0))
    retweets = _safe_int(legacy.get("retweet_count", 0)) or _safe_int(metrics.get("retweet_count", 0))
    replies = _safe_int(legacy.get("reply_count", 0)) or _safe_int(metrics.get("reply_count", 0))
    quotes = _safe_int(legacy.get("quote_count", 0)) or _safe_int(metrics.get("quote_count", 0))
    views = _safe_int(result.get("views", {}).get("count", 0))
    bookmarks = _safe_int(legacy.get("bookmark_count", 0))

    return {
        "id": tweet_id,
        "text": text,
        "author": tweet_author or {},
        "created_at": legacy.get("created_at"),
        "likes": likes,
        "retweets": retweets,
        "replies": replies,
        "quotes": quotes,
        "views": views,
        "bookmarks": bookmarks,
        "lang": legacy.get("lang"),
        "is_reply": bool(legacy.get("in_reply_to_status_id_str")),
        "is_retweet": "retweeted_status_result" in legacy,
        "is_quote": "quoted_status_id_str" in legacy,
        "media": _parse_media(legacy),
        "url": f"https://x.com/i/web/status/{tweet_id}",
        "platform": "twitter",
    }


def _parse_media(legacy: dict[str, Any]) -> list[dict[str, Any]]:
    entities = legacy.get("extended_entities", legacy.get("entities", {}))
    media_list = entities.get("media", [])
    result = []
    for m in media_list:
        entry: dict[str, Any] = {
            "type": m.get("type"),
            "url": m.get("media_url_https"),
        }
        if m.get("type") == "video":
            variants = (m.get("video_info", {}).get("variants", []))
            mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
            if mp4s:
                best = max(mp4s, key=lambda v: v.get("bitrate", 0))
                entry["video_url"] = best["url"]
        result.append(entry)
    return result


def _parse_user_list(instructions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """Extrae usuarios y cursor de las instrucciones de una timeline GraphQL."""
    users: list[dict[str, Any]] = []
    cursor: str | None = None

    for instruction in instructions:
        itype = instruction.get("type") or instruction.get("__typename", "")
        if "AddEntries" in itype or "TimelineAddEntries" in itype:
            for entry in instruction.get("entries", []):
                entry_id = entry.get("entryId", "")
                content = entry.get("content", {})

                if entry_id.startswith("cursor-bottom"):
                    cursor = (
                        content.get("value")
                        or content.get("itemContent", {}).get("value")
                    )
                    continue

                item_content = content.get("itemContent", {})
                if item_content.get("itemType") == "TimelineUser":
                    raw_user = item_content.get("user_results", {}).get("result")
                    parsed = parse_user(raw_user)
                    if parsed:
                        users.append(parsed)

    return users, cursor


def _parse_tweet_list(instructions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str | None]:
    """Extrae tweets y cursor de las instrucciones de una timeline GraphQL."""
    tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    for instruction in instructions:
        itype = instruction.get("type") or instruction.get("__typename", "")
        if "AddEntries" not in itype and "TimelineAddEntries" not in itype:
            continue

        for entry in instruction.get("entries", []):
            entry_id = entry.get("entryId", "")
            content = entry.get("content", {})

            # Cursor para paginacion
            if "cursor-bottom" in entry_id or "cursor-top" in entry_id:
                cursor = content.get("value") or content.get("itemContent", {}).get("value")
                continue

            # Tweet normal
            item_content = content.get("itemContent", {})
            if item_content.get("itemType") == "TimelineTweet":
                tweet = parse_tweet(item_content)
                if tweet:
                    tweets.append(tweet)
                continue

            # Thread: puede tener multiples tweets dentro
            if "TimelineTimelineModule" in str(content.get("itemType", "")):
                for sub_item in content.get("items", []):
                    sub_content = sub_item.get("item", {}).get("itemContent", {})
                    if sub_content.get("itemType") == "TimelineTweet":
                        tweet = parse_tweet(sub_content)
                        if tweet:
                            tweets.append(tweet)

    return tweets, cursor


def _instructions_from_data(data: dict[str, Any], path: list[str]) -> list[dict[str, Any]]:
    """Navega por la respuesta GraphQL y devuelve las instructions."""
    node = data.get("data", {})
    for key in path:
        if not isinstance(node, dict):
            return []
        node = node.get(key, {})
    if not isinstance(node, dict):
        return []
    return node.get("instructions", [])


# ─── Scrapers de perfil ───────────────────────────────────────────────────────

async def scrape_profile(client: TwitterClient, username: str) -> dict[str, Any]:
    """Obtiene el perfil de un usuario por @username."""
    data = await client.graphql(
        "UserByScreenName",
        variables={
            "screen_name": username,
            "withSafetyModeUserFields": True,
        },
        features={
            **DEFAULT_FEATURES,
            "hidden_profile_likes_enabled": True,
            "hidden_profile_subscriptions_enabled": True,
        },
    )
    raw = (
        data.get("data", {})
            .get("user", {})
            .get("result", {})
    )
    if not raw:
        raise NotFoundError(f"Usuario @{username} no encontrado")
    profile = parse_user(raw)
    if not profile:
        raise NotFoundError(f"Usuario @{username} no disponible (cuenta suspendida o bloqueada)")
    return profile


# ─── Scrapers de relaciones ───────────────────────────────────────────────────

async def _paginate_users(
    client: TwitterClient,
    endpoint: str,
    user_id: str,
    limit: int = 100,
    checkpoint_key: str | None = None,
) -> list[dict[str, Any]]:
    """Paginador generico para followers/following/favoriters/retweeters."""
    from .watch import load_cursor, mark_scrape_complete, save_cursor

    all_users: list[dict[str, Any]] = []
    cursor: str | None = None
    if checkpoint_key:
        cursor = load_cursor(checkpoint_key)
        if cursor:
            _log.info("Resuming scrape %s from checkpoint cursor", checkpoint_key)

    while len(all_users) < limit:
        variables: dict[str, Any] = {
            "userId": user_id,
            "count": min(PAGE_SIZE_USERS, limit - len(all_users)),
            "includePromotedContent": False,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql(endpoint, variables=variables)

        timeline = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline", {})
                .get("timeline", {})
        )
        instructions = timeline.get("instructions", [])
        batch, new_cursor = _parse_user_list(instructions)

        if not batch:
            break

        all_users.extend(batch)

        if checkpoint_key and new_cursor:
            save_cursor(checkpoint_key, new_cursor)

        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor

    if checkpoint_key and len(all_users) >= limit:
        # finished requested slice — keep cursor so next call continues
        pass
    elif checkpoint_key and not cursor:
        mark_scrape_complete(checkpoint_key)

    return all_users[:limit]


async def get_user_id(client: TwitterClient, username: str) -> str:
    """Obtiene el ID numerico de un usuario (con cache en memoria)."""
    key = username.lower()
    if key in _USER_ID_CACHE:
        return _USER_ID_CACHE[key]
    profile = await scrape_profile(client, username)
    uid = profile.get("id")
    if not uid:
        raise NotFoundError(f"No se pudo obtener el ID de @{username}")
    _USER_ID_CACHE[key] = uid
    return uid


async def scrape_followers(
    client: TwitterClient,
    username: str,
    limit: int = 100,
    checkpoint: bool = False,
) -> list[dict[str, Any]]:
    user_id = await get_user_id(client, username)
    key = f"followers:{username.lower()}" if checkpoint else None
    return await _paginate_users(client, "Followers", user_id, limit, checkpoint_key=key)


async def scrape_following(
    client: TwitterClient,
    username: str,
    limit: int = 100,
    checkpoint: bool = False,
) -> list[dict[str, Any]]:
    user_id = await get_user_id(client, username)
    key = f"following:{username.lower()}" if checkpoint else None
    return await _paginate_users(client, "Following", user_id, limit, checkpoint_key=key)


async def scrape_non_followers(client: TwitterClient, username: str, limit: int = 200) -> list[dict[str, Any]]:
    """Retorna los usuarios que sigues pero que no te siguen de vuelta.

    Resuelve el user_id una sola vez y consulta followers/following en
    paralelo, reduciendo el tiempo total aproximadamente a la mitad.
    """
    user_id = await get_user_id(client, username)
    following, followers = await asyncio.gather(
        _paginate_users(client, "Following", user_id, limit),
        _paginate_users(client, "Followers", user_id, limit),
    )
    follower_ids = {u["id"] for u in followers if u.get("id")}
    return [u for u in following if u.get("id") not in follower_ids]


# ─── Scraper de tweets ────────────────────────────────────────────────────────

async def scrape_tweets(
    client: TwitterClient,
    username: str,
    limit: int = 50,
    include_replies: bool = False,
) -> list[dict[str, Any]]:
    user_id = await get_user_id(client, username)
    endpoint = "UserTweetsAndReplies" if include_replies else "UserTweets"
    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "userId": user_id,
            "count": min(PAGE_SIZE_TWEETS, limit - len(all_tweets)),
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql(endpoint, variables=variables)

        timeline = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline_v2", {})
                .get("timeline", {})
        )
        instructions = timeline.get("instructions", [])
        batch, new_cursor = _parse_tweet_list(instructions)

        all_tweets.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


async def get_user_likes(
    client: TwitterClient,
    username: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Obtiene los tweets que le gustaron a un usuario (públicos)."""
    user_id = await get_user_id(client, username)
    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "userId": user_id,
            "count": min(PAGE_SIZE_TWEETS, limit - len(all_tweets)),
            "includePromotedContent": False,
            "withClientEventToken": False,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql("UserLikes", variables=variables)
        timeline = (
            data.get("data", {})
                .get("user", {})
                .get("result", {})
                .get("timeline_v2", {})
                .get("timeline", {})
        )
        instructions = timeline.get("instructions", [])
        batch, new_cursor = _parse_tweet_list(instructions)

        all_tweets.extend(batch)
        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


# ─── Replies y thread ───────────────────────────────────────────────────────────

async def get_tweet_replies(
    client: TwitterClient,
    tweet_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Obtiene replies/conversación de un tweet vía TweetDetail."""
    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
            "withV2Timeline": True,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql(
            "TweetDetail",
            variables=variables,
            features={
                **DEFAULT_FEATURES,
                "rweb_lists_timeline_redesign_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweet_gql_enabled": True,
                "responsive_web_enhance_cards_enabled": False,
            },
        )

        instructions = _instructions_from_data(
            data,
            ["threaded_conversation_with_injections_v2", "instructions"],
        )
        if not instructions:
            # Fallback a otros paths posibles
            instructions = _instructions_from_data(
                data,
                ["tweet", "result", "timeline_response", "timeline", "instructions"],
            )

        batch, new_cursor = _parse_tweet_list(instructions)
        all_tweets.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


# ─── Engagement: favoriters y retweeters ──────────────────────────────────────

async def get_tweet_favoriters(
    client: TwitterClient,
    tweet_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Obtiene usuarios que dieron like a un tweet."""
    all_users: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_users) < limit:
        variables: dict[str, Any] = {
            "tweetId": tweet_id,
            "count": min(PAGE_SIZE_ENGAGEMENT, limit - len(all_users)),
            "includePromotedContent": False,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql("Favoriters", variables=variables)
        timeline = (
            data.get("data", {})
                .get("favoriters_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        batch, new_cursor = _parse_user_list(timeline)
        all_users.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_users[:limit]


async def get_tweet_retweeters(
    client: TwitterClient,
    tweet_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Obtiene usuarios que hicieron retweet a un tweet."""
    all_users: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_users) < limit:
        variables: dict[str, Any] = {
            "tweetId": tweet_id,
            "count": min(PAGE_SIZE_ENGAGEMENT, limit - len(all_users)),
            "includePromotedContent": False,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql("Retweeters", variables=variables)
        timeline = (
            data.get("data", {})
                .get("retweeters_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        batch, new_cursor = _parse_user_list(timeline)
        all_users.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_users[:limit]


# ─── Bookmarks ──────────────────────────────────────────────────────────────────

async def get_bookmarks(
    client: TwitterClient,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Obtiene los bookmarks del usuario autenticado. Requiere auth."""
    if not client.is_authenticated():
        raise TwitterError("Bookmarks requiere autenticación")

    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "count": min(PAGE_SIZE_BOOKMARKS, limit - len(all_tweets)),
            "includePromotedContent": False,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql(
            "Bookmarks",
            variables=variables,
            features={
                **DEFAULT_FEATURES,
                "graphql_timeline_v2_bookmark_timeline": True,
            },
        )
        timeline = (
            data.get("data", {})
                .get("bookmark_timeline_v2", {})
                .get("timeline", {})
                .get("instructions", [])
        )
        batch, new_cursor = _parse_tweet_list(timeline)
        all_tweets.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


# ─── Home timeline ────────────────────────────────────────────────────────────

async def get_home_timeline(
    client: TwitterClient,
    limit: int = 50,
    latest: bool = False,
) -> list[dict[str, Any]]:
    """Obtiene el home timeline del usuario autenticado. Requiere auth."""
    if not client.is_authenticated():
        raise TwitterError("Home timeline requiere autenticación")

    endpoint = "HomeLatestTimeline" if latest else "HomeTimeline"
    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "count": min(PAGE_SIZE_TWEETS, limit - len(all_tweets)),
            "includePromotedContent": True,
            "latestControlAvailable": True,
            "requestContext": "launch",
            "withCommunity": True,
        }
        if cursor:
            variables["cursor"] = cursor

        data = await client.graphql(endpoint, variables=variables)
        timeline = (
            data.get("data", {})
                .get("home", {})
                .get("home_timeline_urt", {})
                .get("instructions", [])
        )
        batch, new_cursor = _parse_tweet_list(timeline)
        all_tweets.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


# ─── Trends ───────────────────────────────────────────────────────────────────

async def get_trends(client: TwitterClient, woeid: int = 1) -> list[dict[str, Any]]:
    """
    Obtiene trending topics de Twitter/X via REST API.
    woeid: 1 = worldwide, 23424977 = USA, 44418 = London, etc.
    """
    data = await client.rest_get("/1.1/trends/place.json", params={"id": str(woeid)})
    if not isinstance(data, list) or not data:
        return []

    trends = data[0].get("trends", [])
    return [
        {
            "name": t.get("name"),
            "query": t.get("query"),
            "url": t.get("url"),
            "tweet_volume": t.get("tweet_volume"),
            "promoted": t.get("promoted_content") is not None,
        }
        for t in trends
    ]


# ─── Búsqueda ─────────────────────────────────────────────────────────────────

async def search_tweets(
    client: TwitterClient,
    query: str,
    limit: int = 50,
    mode: str = "Top",
) -> list[dict[str, Any]]:
    """
    Busca tweets por query.
    mode="Top" devuelve tweets con mas engagement (likes, RTs).
    mode="Latest" devuelve los mas recientes (suelen tener menos engagement).
    """
    all_tweets: list[dict[str, Any]] = []
    cursor: str | None = None

    while len(all_tweets) < limit:
        variables: dict[str, Any] = {
            "rawQuery": query,
            "count": min(PAGE_SIZE_SEARCH, limit - len(all_tweets)),
            "querySource": "typed_query",
            "product": mode,
        }
        if cursor:
            variables["cursor"] = cursor

        try:
            data = await client.graphql("SearchTimeline", variables=variables)
        except ForbiddenError as e:
            # Twitter/X a veces bloquea ciertas queries. Si ya teníamos
            # resultados, los devolvemos (con warning); si no, propagamos
            # el error para que el usuario sepa que fue un bloqueo.
            if all_tweets:
                _log.warning("Búsqueda bloqueada (403) tras %d tweets: %s", len(all_tweets), e)
                break
            raise

        timeline = (
            data.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
        )
        if not timeline:
            break

        instructions = timeline.get("instructions", [])
        batch, new_cursor = _parse_tweet_list(instructions)

        all_tweets.extend(batch)

        if not new_cursor or new_cursor == cursor or not batch:
            break
        cursor = new_cursor

    return all_tweets[:limit]


# ─── Wrapper sincrono (para uso facil desde otros proyectos) ───────────────────

def _run_sync(coro):
    """Ejecuta una corrutina en un loop nuevo y la cierra correctamente."""
    return asyncio.run(coro)


async def _with_client(cookies: str, coro):
    async with TwitterClient(cookies=cookies) as client:
        return await coro(client)


def search_tweets_sync(
    cookies: str,
    query: str,
    limit: int = 50,
    mode: str = "Top",
) -> list[dict[str, Any]]:
    """Wrapper sincrono para buscar tweets. No requiere asyncio."""
    return _run_sync(_with_client(cookies, lambda c: search_tweets(c, query=query, limit=limit, mode=mode)))


def scrape_profile_sync(cookies: str, username: str) -> dict[str, Any]:
    """Wrapper sincrono para obtener perfil de usuario."""
    return _run_sync(_with_client(cookies, lambda c: scrape_profile(c, username)))


def scrape_tweets_sync(
    cookies: str,
    username: str,
    limit: int = 50,
    include_replies: bool = False,
) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener tweets de un usuario."""
    return _run_sync(_with_client(cookies, lambda c: scrape_tweets(c, username, limit, include_replies)))


def get_user_likes_sync(cookies: str, username: str, limit: int = 50) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener likes públicos de un usuario."""
    return _run_sync(_with_client(cookies, lambda c: get_user_likes(c, username, limit)))


def get_tweet_replies_sync(cookies: str, tweet_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener replies de un tweet."""
    return _run_sync(_with_client(cookies, lambda c: get_tweet_replies(c, tweet_id, limit)))


def get_tweet_favoriters_sync(cookies: str, tweet_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener usuarios que dieron like a un tweet."""
    return _run_sync(_with_client(cookies, lambda c: get_tweet_favoriters(c, tweet_id, limit)))


def get_tweet_retweeters_sync(cookies: str, tweet_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener usuarios que retuitearon un tweet."""
    return _run_sync(_with_client(cookies, lambda c: get_tweet_retweeters(c, tweet_id, limit)))


def get_bookmarks_sync(cookies: str, limit: int = 50) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener bookmarks del usuario autenticado."""
    return _run_sync(_with_client(cookies, lambda c: get_bookmarks(c, limit)))


def get_home_timeline_sync(cookies: str, limit: int = 50, latest: bool = False) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener el home timeline."""
    return _run_sync(_with_client(cookies, lambda c: get_home_timeline(c, limit, latest)))


def get_trends_sync(cookies: str, woeid: int = 1) -> list[dict[str, Any]]:
    """Wrapper sincrono para obtener trending topics."""
    return _run_sync(_with_client(cookies, lambda c: get_trends(c, woeid)))


def validate_cookies_sync(cookies: str) -> dict[str, Any]:
    """Wrapper sincrono para validar que las cookies funcionan."""
    return _run_sync(_with_client(cookies, lambda c: c.validate_cookies()))
