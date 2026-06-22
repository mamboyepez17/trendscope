"""
XActions-PY — Actions
Like, unlike, follow, unfollow, tweet, retweet, delete.
Todo vía GraphQL interna. Requiere auth_token + ct0 en cookies.
"""

import asyncio
from typing import Optional
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from scraper.client import TwitterClient, AuthError, GRAPHQL_ENDPOINTS, REST_BASE


def _require_auth(client: TwitterClient):
    if not client.is_authenticated():
        raise AuthError("Se requiere autenticación. Configura auth_token y ct0.")


# ─── Tweets ───────────────────────────────────────────────────────────────────

async def post_tweet(
    client: TwitterClient,
    text: str,
    reply_to_id: Optional[str] = None,
) -> dict:
    """Publica un tweet. Requiere auth."""
    _require_auth(client)

    variables = {
        "tweet_text": text,
        "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [],
    }
    if reply_to_id:
        variables["reply"] = {
            "in_reply_to_tweet_id": reply_to_id,
            "exclude_reply_user_ids": [],
        }

    data = await client.graphql("CreateTweet", variables=variables, mutation=True)
    result = (
        data.get("data", {})
            .get("create_tweet", {})
            .get("tweet_results", {})
            .get("result", {})
    )
    return {"success": bool(result), "tweet_id": result.get("rest_id")}


async def delete_tweet(client: TwitterClient, tweet_id: str) -> dict:
    _require_auth(client)
    data = await client.graphql(
        "DeleteTweet",
        variables={"tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    return {"success": "data" in data}


# ─── Engagement ───────────────────────────────────────────────────────────────

async def like_tweet(client: TwitterClient, tweet_id: str) -> dict:
    _require_auth(client)
    data = await client.graphql(
        "FavoriteTweet",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    return {"success": data.get("data", {}).get("favorite_tweet") == "Done"}


async def unlike_tweet(client: TwitterClient, tweet_id: str) -> dict:
    _require_auth(client)
    data = await client.graphql(
        "UnfavoriteTweet",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    return {"success": data.get("data", {}).get("unfavorite_tweet") == "Done"}


async def retweet(client: TwitterClient, tweet_id: str) -> dict:
    _require_auth(client)
    data = await client.graphql(
        "CreateRetweet",
        variables={"tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    result = data.get("data", {}).get("create_retweet", {}).get("retweet_results", {})
    return {"success": bool(result)}


async def unretweet(client: TwitterClient, tweet_id: str) -> dict:
    _require_auth(client)
    data = await client.graphql(
        "DeleteRetweet",
        variables={"source_tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    return {"success": bool(data.get("data"))}


# ─── Follow / Unfollow ────────────────────────────────────────────────────────

async def follow_user(client: TwitterClient, user_id: str) -> dict:
    """Follow por user_id. Usa REST endpoint (no GraphQL mutation disponible)."""
    _require_auth(client)
    data = await client.rest_post(
        "/1.1/friendships/create.json",
        {"user_id": user_id, "skip_status": "true"},
    )
    return {"success": bool(data.get("id_str") or data.get("id"))}


async def unfollow_user(client: TwitterClient, user_id: str) -> dict:
    """Unfollow por user_id."""
    _require_auth(client)
    data = await client.rest_post(
        "/1.1/friendships/destroy.json",
        {"user_id": user_id, "skip_status": "true"},
    )
    return {"success": bool(data.get("id_str") or data.get("id"))}


# ─── Bulk unfollow ────────────────────────────────────────────────────────────

async def bulk_unfollow(
    client: TwitterClient,
    user_ids: list,
    delay_seconds: float = 2.0,
    on_progress=None,
) -> dict:
    """
    Hace unfollow masivo con delay entre cada acción para evitar rate limits.
    on_progress: callable(current, total, username) opcional.
    """
    _require_auth(client)
    success = 0
    failed  = 0

    for i, uid in enumerate(user_ids):
        try:
            result = await unfollow_user(client, uid)
            if result["success"]:
                success += 1
            else:
                failed += 1
        except Exception:
            failed += 1

        if on_progress:
            on_progress(i + 1, len(user_ids), uid)

        await asyncio.sleep(delay_seconds)

    return {
        "total": len(user_ids),
        "success": success,
        "failed": failed,
    }
