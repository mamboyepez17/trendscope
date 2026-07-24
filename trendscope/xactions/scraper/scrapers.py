"""
XActions-PY — Scrapers
Replicas en Python de los scrapers HTTP de XActions.
v1.1.0: Mejorado parse_tweet para manejar todas las variantes de GraphQL,
        mejor extraccion de metricas, y wrapper sync para uso facil.
"""

import asyncio
from typing import Optional, List, Dict, Any
from .client import TwitterClient, DEFAULT_FEATURES, NotFoundError, TwitterError


# ─── Helpers de parseo ────────────────────────────────────────────────────────

def _upgrade_avatar(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return url.replace("_normal", "_400x400")


def _safe_int(val: Any, default: int = 0) -> int:
    """Convierte cualquier valor a int de forma segura."""
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def parse_user(raw: Dict) -> Optional[Dict]:
    """Convierte un resultado GraphQL de usuario al formato XActions."""
    if not raw or raw.get("__typename") == "UserUnavailable":
        return None
    legacy = raw.get("legacy", {})
    return {
        "id":             raw.get("rest_id"),
        "username":       legacy.get("screen_name"),
        "name":           legacy.get("name"),
        "bio":            legacy.get("description"),
        "verified":       raw.get("is_blue_verified", legacy.get("verified", False)),
        "avatar":         _upgrade_avatar(legacy.get("profile_image_url_https")),
        "followers":      _safe_int(legacy.get("followers_count", 0)),
        "following":      _safe_int(legacy.get("friends_count", 0)),
        "tweets_count":   _safe_int(legacy.get("statuses_count", 0)),
        "protected":      legacy.get("protected", False),
        "created_at":     legacy.get("created_at"),
        "location":       legacy.get("location"),
        "website":        (legacy.get("entities", {})
                               .get("url", {})
                               .get("urls", [{}])[0]
                               .get("expanded_url")),
        "platform":       "twitter",
    }


def parse_tweet(raw: Dict, author: Optional[Dict] = None) -> Optional[Dict]:
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

    core    = result.get("core", {})
    legacy  = result.get("legacy", {})
    notes   = result.get("notes", {})
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

    # Bookmark count (si esta disponible)
    bookmarks = _safe_int(legacy.get("bookmark_count", 0))

    return {
        "id":           tweet_id,
        "text":         text,
        "author":       tweet_author or {},
        "created_at":   legacy.get("created_at"),
        "likes":        likes,
        "retweets":     retweets,
        "replies":      replies,
        "quotes":       quotes,
        "views":        views,
        "bookmarks":    bookmarks,
        "lang":         legacy.get("lang"),
        "is_reply":     bool(legacy.get("in_reply_to_status_id_str")),
        "is_retweet":   "retweeted_status_result" in legacy,
        "is_quote":     "quoted_status_id_str" in legacy,
        "media":        _parse_media(legacy),
        "url":          f"https://x.com/i/web/status/{tweet_id}",
        "platform":     "twitter",
    }


def _parse_media(legacy: Dict) -> List[Dict]:
    entities = legacy.get("extended_entities", legacy.get("entities", {}))
    media_list = entities.get("media", [])
    result = []
    for m in media_list:
        entry: Dict[str, Any] = {
            "type": m.get("type"),
            "url":  m.get("media_url_https"),
        }
        if m.get("type") == "video":
            variants = (m.get("video_info", {}).get("variants", []))
            mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
            if mp4s:
                best = max(mp4s, key=lambda v: v.get("bitrate", 0))
                entry["video_url"] = best["url"]
        result.append(entry)
    return result


def _parse_user_list(instructions: List) -> tuple[List[Dict], Optional[str]]:
    """Extrae usuarios y cursor de las instrucciones de una timeline GraphQL."""
    users: List[Dict] = []
    cursor: Optional[str] = None

    for instruction in instructions:
        itype = instruction.get("type") or instruction.get("__typename", "")
        if "AddEntries" in itype or "TimelineAddEntries" in itype:
            for entry in instruction.get("entries", []):
                entry_id = entry.get("entryId", "")
                content  = entry.get("content", {})

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


def _parse_tweet_list(instructions: List) -> tuple[List[Dict], Optional[str]]:
    """Extrae tweets y cursor de las instrucciones de una timeline GraphQL."""
    tweets: List[Dict] = []
    cursor: Optional[str] = None

    for instruction in instructions:
        itype = instruction.get("type") or instruction.get("__typename", "")
        if "AddEntries" not in itype and "TimelineAddEntries" not in itype:
            continue

        for entry in instruction.get("entries", []):
            entry_id = entry.get("entryId", "")
            content  = entry.get("content", {})

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


# ─── Scrapers de perfil ───────────────────────────────────────────────────────

async def scrape_profile(client: TwitterClient, username: str) -> Dict:
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
    return parse_user(raw)


# ─── Scrapers de relaciones ───────────────────────────────────────────────────

async def _paginate_users(
    client: TwitterClient,
    endpoint: str,
    user_id: str,
    limit: int = 100,
) -> List[Dict]:
    """Paginador generico para followers/following."""
    all_users: List[Dict] = []
    cursor: Optional[str] = None

    while len(all_users) < limit:
        variables: Dict[str, Any] = {
            "userId": user_id,
            "count": min(20, limit - len(all_users)),
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

        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor

    return all_users[:limit]


async def get_user_id(client: TwitterClient, username: str) -> str:
    """Obtiene el ID numerico de un usuario."""
    profile = await scrape_profile(client, username)
    uid = profile.get("id")
    if not uid:
        raise NotFoundError(f"No se pudo obtener el ID de @{username}")
    return uid


async def scrape_followers(
    client: TwitterClient,
    username: str,
    limit: int = 100,
) -> List[Dict]:
    user_id = await get_user_id(client, username)
    return await _paginate_users(client, "Followers", user_id, limit)


async def scrape_following(
    client: TwitterClient,
    username: str,
    limit: int = 100,
) -> List[Dict]:
    user_id = await get_user_id(client, username)
    return await _paginate_users(client, "Following", user_id, limit)


async def scrape_non_followers(
    client: TwitterClient,
    username: str,
    limit: int = 200,
) -> List[Dict]:
    """Retorna los usuarios que sigues pero que no te siguen de vuelta."""
    following = await scrape_following(client, username, limit=limit)
    followers  = await scrape_followers(client, username, limit=limit)
    follower_ids = {u["id"] for u in followers if u.get("id")}
    return [u for u in following if u.get("id") not in follower_ids]


# ─── Scraper de tweets ────────────────────────────────────────────────────────

async def scrape_tweets(
    client: TwitterClient,
    username: str,
    limit: int = 50,
    include_replies: bool = False,
) -> List[Dict]:
    user_id   = await get_user_id(client, username)
    endpoint  = "UserTweetsAndReplies" if include_replies else "UserTweets"
    all_tweets: List[Dict] = []
    cursor: Optional[str] = None

    while len(all_tweets) < limit:
        variables: Dict[str, Any] = {
            "userId": user_id,
            "count": min(40, limit - len(all_tweets)),
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


async def search_tweets(
    client: TwitterClient,
    query: str,
    limit: int = 50,
    mode: str = "Top",  # "Top" (con engagement) o "Latest" (mas recientes)
) -> List[Dict]:
    """
    Busca tweets por query.
    mode="Top" devuelve tweets con mas engagement (likes, RTs).
    mode="Latest" devuelve los mas recientes (suelen tener menos engagement).
    """
    all_tweets: List[Dict] = []
    cursor: Optional[str] = None

    while len(all_tweets) < limit:
        variables: Dict[str, Any] = {
            "rawQuery": query,
            "count": min(20, limit - len(all_tweets)),
            "querySource": "typed_query",
            "product": mode,
        }
        if cursor:
            variables["cursor"] = cursor

        try:
            data = await client.graphql("SearchTimeline", variables=variables)
        except TwitterError as e:
            if "HTTP 403" in str(e) or "NoneType" in str(e):
                # Twitter a veces da 403 en ciertas queries, retornar lo que tengamos
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

def search_tweets_sync(
    cookies: str,
    query: str,
    limit: int = 50,
    mode: str = "Top",
) -> List[Dict]:
    """
    Wrapper sincrono para buscar tweets. No requiere asyncio.
    Uso: search_tweets_sync("auth_token=xxx; ct0=yyy", "crypto Colombia", 20)
    """
    client = TwitterClient(cookies=cookies)
    if not client.is_authenticated():
        raise TwitterError("Cookies no validas: falta auth_token")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            search_tweets(client, query=query, limit=limit, mode=mode)
        )
    finally:
        loop.close()

    return results


def scrape_profile_sync(cookies: str, username: str) -> Dict:
    """Wrapper sincrono para obtener perfil de usuario."""
    client = TwitterClient(cookies=cookies)
    if not client.is_authenticated():
        raise TwitterError("Cookies no validas: falta auth_token")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(scrape_profile(client, username))
    finally:
        loop.close()

    return results


def scrape_tweets_sync(
    cookies: str,
    username: str,
    limit: int = 50,
    include_replies: bool = False,
) -> List[Dict]:
    """Wrapper sincrono para obtener tweets de un usuario."""
    client = TwitterClient(cookies=cookies)
    if not client.is_authenticated():
        raise TwitterError("Cookies no validas: falta auth_token")

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(
            scrape_tweets(client, username, limit, include_replies)
        )
    finally:
        loop.close()

    return results
