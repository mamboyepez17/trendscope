"""
XActions-PY — Scrapers
Replicas en Python de los scrapers HTTP de XActions.
"""

from typing import Optional, List, Dict, Any
from .client import TwitterClient, DEFAULT_FEATURES, NotFoundError


# ─── Helpers de parseo ────────────────────────────────────────────────────────

def _upgrade_avatar(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    return url.replace("_normal", "_400x400")


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
        "followers":      legacy.get("followers_count", 0),
        "following":      legacy.get("friends_count", 0),
        "tweets_count":   legacy.get("statuses_count", 0),
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
    """Convierte un resultado GraphQL de tweet al formato XActions."""
    if not raw:
        return None
    result = raw.get("tweet_results", {}).get("result") or raw
    if result.get("__typename") == "TweetTombstone":
        return None

    core    = result.get("core", {})
    legacy  = result.get("legacy", {})
    metrics = result.get("public_metrics") or {}

    return {
        "id":         result.get("rest_id") or legacy.get("id_str"),
        "text":       legacy.get("full_text", ""),
        "author":     author or parse_user(
            core.get("user_results", {}).get("result", {})
        ),
        "created_at": legacy.get("created_at"),
        "likes":      legacy.get("favorite_count", 0),
        "retweets":   legacy.get("retweet_count", 0),
        "replies":    legacy.get("reply_count", 0),
        "quotes":     legacy.get("quote_count", 0),
        "views":      int(result.get("views", {}).get("count", 0) or 0),
        "lang":       legacy.get("lang"),
        "is_reply":   bool(legacy.get("in_reply_to_status_id_str")),
        "is_retweet": "retweeted_status_result" in legacy,
        "media":      _parse_media(legacy),
        "url":        f"https://x.com/i/web/status/{result.get('rest_id') or legacy.get('id_str')}",
        "platform":   "twitter",
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
    """Paginador genérico para followers/following."""
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
    """Obtiene el ID numérico de un usuario (requerido para queries de relaciones)."""
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
    """
    Retorna los usuarios que sigues pero que no te siguen de vuelta.
    """
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
        new_cursor: Optional[str] = None

        for instruction in instructions:
            itype = instruction.get("type", "")
            if "AddEntries" not in itype:
                continue
            for entry in instruction.get("entries", []):
                entry_id = entry.get("entryId", "")
                content  = entry.get("content", {})

                if entry_id.startswith("cursor-bottom"):
                    new_cursor = (
                        content.get("value")
                        or content.get("itemContent", {}).get("value")
                    )
                    continue

                item_content = content.get("itemContent", {})
                if item_content.get("itemType") == "TimelineTweet":
                    tweet = parse_tweet(item_content)
                    if tweet:
                        all_tweets.append(tweet)

        if not new_cursor or new_cursor == cursor:
            break
        cursor = new_cursor

    return all_tweets[:limit]


async def search_tweets(
    client: TwitterClient,
    query: str,
    limit: int = 50,
    mode: str = "Latest",  # "Latest" o "Top"
) -> List[Dict]:
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

        data = await client.graphql("SearchTimeline", variables=variables)

        timeline = (
            data.get("data", {})
                .get("search_by_raw_query", {})
                .get("search_timeline", {})
                .get("timeline", {})
        )
        instructions = timeline.get("instructions", [])
        new_cursor: Optional[str] = None

        for instruction in instructions:
            itype = instruction.get("type", "")
            if "AddEntries" not in itype:
                continue
            for entry in instruction.get("entries", []):
                entry_id = entry.get("entryId", "")
                content  = entry.get("content", {})

                if "cursor-bottom" in entry_id:
                    new_cursor = content.get("value") or content.get("itemContent", {}).get("value")
                    continue

                item_content = content.get("itemContent", {})
                if item_content.get("itemType") == "TimelineTweet":
                    tweet = parse_tweet(item_content)
                    if tweet:
                        all_tweets.append(tweet)

        if not new_cursor or new_cursor == cursor or not all_tweets:
            break
        cursor = new_cursor

    return all_tweets[:limit]
