"""
XActions-PY — Actions
Like, unlike, follow, unfollow, tweet, retweet, delete, bookmark.
Todo vía GraphQL interna o REST legacy. Requiere auth_token + ct0 en cookies.

v1.2.0:
  - Agregados create_bookmark / delete_bookmark.
  - Mejor manejo de errores y cierre de cliente.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from .caps import check_write, load_caps, record_write, save_caps
from .client import UPLOAD_BASE, AuthError, TwitterClient

_log = logging.getLogger(__name__)

# Set to False to bypass on-disk daily caps (not recommended)
CAPS_ENABLED = True


def _require_auth(client: TwitterClient) -> None:
    if not client.is_authenticated():
        raise AuthError("Se requiere autenticación. Configura auth_token y ct0.")


def _account_key(client: Any) -> str:
    cookies = getattr(client, "_cookies", None) or {}
    token = cookies.get("auth_token") or getattr(client, "_cookie_str", "")[:20]
    return f"acct:{hash(token) & 0xFFFFFFFF:08x}"


def _before_write(client: Any, operation: str) -> None:
    """Raise WriteCapExceeded before hitting X (does not record yet)."""
    if not CAPS_ENABLED:
        return
    data = load_caps()
    check_write(data, operation, _account_key(client))


def _after_write(client: Any, operation: str) -> None:
    """Record a successful write against the daily budget."""
    if not CAPS_ENABLED:
        return
    try:
        data = load_caps()
        data = record_write(data, operation, _account_key(client))
        save_caps(data)
    except OSError as e:
        _log.warning("No se pudo registrar write cap: %s", e)


# ─── Media upload ─────────────────────────────────────────────────────────────

async def upload_media(client: TwitterClient, file_path: str) -> dict[str, Any]:
    """
    Sube una imagen (jpg/png/gif/webp) a Twitter y devuelve su media_id.
    Requiere auth. Límite simple upload: ~5MB por imagen.
    (Los videos requieren chunked upload INIT/APPEND/FINALIZE — no soportado aún.)
    """
    _require_auth(client)
    data = await client.rest_upload(f"{UPLOAD_BASE}/1.1/media/upload.json", file_path)
    media_id = data.get("media_id_string") or str(data.get("media_id", ""))
    if not media_id:
        raise AuthError(f"No se obtuvo media_id: {data}")
    return {"success": True, "media_id": media_id, "size": data.get("size")}


# ─── Tweets ───────────────────────────────────────────────────────────────────

async def post_tweet(
    client: TwitterClient,
    text: str,
    reply_to_id: str | None = None,
    media_ids: list | None = None,
) -> dict[str, Any]:
    """Publica un tweet (con media opcional). Requiere auth."""
    _require_auth(client)
    _before_write(client, "tweet")

    media_entities = [{"media_id": mid, "tagged_users": []} for mid in (media_ids or [])]
    variables = {
        "tweet_text": text,
        "dark_request": False,
        "media": {"media_entities": media_entities, "possibly_sensitive": False},
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
    # TweetWithVisibilityResults anida el tweet real en .tweet
    if isinstance(result, dict) and result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet") or {}

    tweet_id = None
    if isinstance(result, dict):
        tweet_id = (
            result.get("rest_id")
            or (result.get("legacy") or {}).get("id_str")
            or (result.get("tweet") or {}).get("rest_id")
        )

    # Errores GraphQL dentro del payload (sin HTTP error)
    errors = data.get("errors") or []
    error_msg = None
    if errors:
        error_msg = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])

    if tweet_id:
        _after_write(client, "tweet")

    return {
        "success": bool(tweet_id),
        "tweet_id": tweet_id,
        "error": error_msg,
        "raw_keys": list(data.keys()) if not tweet_id else None,
    }


async def post_thread(
    client: TwitterClient,
    tweets: list[str],
    delay_seconds: float = 1.5,
) -> dict[str, Any]:
    """
    Publica un hilo: cada tweet responde al anterior.
    Requiere auth. `delay_seconds` entre tweets para evitar rate limits.
    """
    _require_auth(client)
    if not tweets:
        return {"success": False, "tweet_ids": [], "error": "lista vacía"}

    tweet_ids: list[str] = []
    reply_to: str | None = None
    for i, text in enumerate(tweets):
        text = (text or "").strip()
        if not text:
            continue
        result = await post_tweet(client, text, reply_to_id=reply_to)
        if not result.get("success") or not result.get("tweet_id"):
            return {
                "success": False,
                "tweet_ids": tweet_ids,
                "failed_at": i,
                "error": (
                    result.get("error")
                    or f"No se pudo publicar el tweet {i + 1}/{len(tweets)}"
                ),
            }
        tweet_ids.append(result["tweet_id"])
        reply_to = result["tweet_id"]
        if i < len(tweets) - 1:
            await asyncio.sleep(delay_seconds)

    return {
        "success": True,
        "tweet_ids": tweet_ids,
        "root_id": tweet_ids[0] if tweet_ids else None,
        "count": len(tweet_ids),
    }


async def delete_tweet(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "DeleteTweet",
        variables={"tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    return {"success": "data" in data}


# ─── Engagement ─────────────────────────────────────────────────────────────

async def like_tweet(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    _before_write(client, "like")
    data = await client.graphql(
        "FavoriteTweet",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    ok = data.get("data", {}).get("favorite_tweet") == "Done"
    if ok:
        _after_write(client, "like")
    return {"success": ok}


async def unlike_tweet(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "UnfavoriteTweet",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    return {"success": data.get("data", {}).get("unfavorite_tweet") == "Done"}


async def retweet(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "CreateRetweet",
        variables={"tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    result = data.get("data", {}).get("create_retweet", {}).get("retweet_results", {})
    return {"success": bool(result)}


async def unretweet(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "DeleteRetweet",
        variables={"source_tweet_id": tweet_id, "dark_request": False},
        mutation=True,
    )
    return {"success": bool(data.get("data"))}


# ─── Bookmarks ───────────────────────────────────────────────────────────────

async def create_bookmark(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "CreateBookmark",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    return {"success": "data" in data}


async def delete_bookmark(client: TwitterClient, tweet_id: str) -> dict[str, Any]:
    _require_auth(client)
    data = await client.graphql(
        "DeleteBookmark",
        variables={"tweet_id": tweet_id},
        mutation=True,
    )
    return {"success": "data" in data}


# ─── Follow / Unfollow ─────────────────────────────────────────────────────────

async def follow_user(client: TwitterClient, user_id: str) -> dict[str, Any]:
    """Follow por user_id. Usa REST endpoint (no GraphQL mutation disponible)."""
    _require_auth(client)
    _before_write(client, "follow")
    data = await client.rest_post(
        "/1.1/friendships/create.json",
        {"user_id": user_id, "skip_status": "true"},
    )
    ok = bool(data.get("id_str") or data.get("id"))
    if ok:
        _after_write(client, "follow")
    return {"success": ok}


async def unfollow_user(client: TwitterClient, user_id: str) -> dict[str, Any]:
    """Unfollow por user_id."""
    _require_auth(client)
    _before_write(client, "unfollow")
    data = await client.rest_post(
        "/1.1/friendships/destroy.json",
        {"user_id": user_id, "skip_status": "true"},
    )
    ok = bool(data.get("id_str") or data.get("id"))
    if ok:
        _after_write(client, "unfollow")
    return {"success": ok}


# ─── Bulk unfollow ─────────────────────────────────────────────────────────────

async def bulk_unfollow(
    client: TwitterClient,
    user_ids: list,
    delay_seconds: float = 2.0,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> dict[str, Any]:
    """
    Hace unfollow masivo con delay entre cada acción para evitar rate limits.
    on_progress: callback(current, total, user_id) opcional.
    """
    _require_auth(client)
    success = 0
    failed = 0

    for i, uid in enumerate(user_ids):
        try:
            result = await unfollow_user(client, uid)
            if result["success"]:
                success += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            _log.warning("bulk_unfollow: falló user_id=%s (%s)", uid, e)

        if on_progress:
            on_progress(i + 1, len(user_ids), uid)

        await asyncio.sleep(delay_seconds)

    return {
        "total": len(user_ids),
        "success": success,
        "failed": failed,
    }
