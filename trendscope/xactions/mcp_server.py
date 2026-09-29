"""
XActions-PY — MCP Server
Servidor MCP para agentes AI (Claude, Mambo, etc.)
Sin npm. Usa MCPServer (mcp>=2) o FastMCP (mcp 1.x) + httpx puro.

v1.2.0:
  - Herramientas nuevas: replies, favoriters, retweeters, user likes, bookmarks,
    home timeline, trending topics, validación de cookies, bookmark/unbookmark.
  - Mejor manejo de errores (ForbiddenError).

v1.5.0:
  - Compatible con mcp 2.x (MCPServer) y mcp 1.x (FastMCP).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

try:
    # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _MCPServer
except ImportError:  # pragma: no cover - compat mcp 1.x
    from mcp.server.fastmcp import FastMCP as _MCPServer

from .actions import (
    bulk_unfollow,
    create_bookmark,
    delete_bookmark,
    delete_tweet,
    follow_user,
    like_tweet,
    post_thread,
    post_tweet,
    retweet,
    unfollow_user,
    unlike_tweet,
)
from .analyzer import analyze_tweets, compare_accounts
from .client import (
    AuthError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    TwitterClient,
    TwitterError,
)
from .pool import ClientPool
from .scrapers import (
    get_bookmarks,
    get_home_timeline,
    get_trends,
    get_tweet_favoriters,
    get_tweet_replies,
    get_tweet_retweeters,
    get_user_id,
    get_user_likes,
    scrape_followers,
    scrape_following,
    scrape_non_followers,
    scrape_profile,
    scrape_tweets,
    search_tweets,
)
from .search_query import build_search_query

# ─── Inicialización ───────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

mcp = _MCPServer(
    "xactions-py",
    instructions="X/Twitter automation toolkit — Python port of XActions. Sin npm.",
)

_cookies = os.getenv("TWITTER_COOKIES", "")
_proxy = os.getenv("TWITTER_PROXY")
_client: TwitterClient | ClientPool | None = None
_client_key: str | None = None


def get_client(cookies: str | None = None) -> TwitterClient | ClientPool:
    """
    Retorna el cliente singleton, reconfigurándolo si se pasan cookies nuevas.
    Si hay varias cookies (separadas por '|||' o salto de línea) crea un pool.
    """
    global _client, _client_key
    effective = cookies or _cookies
    if _client is None or effective != _client_key:
        old = _client
        parts = [c.strip() for c in effective.replace("\n", "|||").split("|||") if c.strip()]
        _client = ClientPool(parts, proxy=_proxy) if len(parts) > 1 else TwitterClient(
            cookies=parts[0] if parts else "", proxy=_proxy
        )
        _client_key = effective
        # Cerrar el cliente anterior (libera sockets) sin bloquear el loop.
        if old is not None:
            asyncio.get_running_loop().create_task(old.aclose())
    return _client


def _fmt_error(e: Exception) -> str:
    if isinstance(e, AuthError):
        return f"❌ Error de autenticación: {e}. Verifica tu auth_token y ct0."
    if isinstance(e, ForbiddenError):
        return f"🚫 Acceso denegado: {e}. Puede ser una restricción de la API para esta cuenta/query."
    if isinstance(e, RateLimitError):
        return f"⏳ Rate limit alcanzado: {e}. Espera unos minutos."
    if isinstance(e, NotFoundError):
        return f"🔍 No encontrado: {e}"
    if isinstance(e, TwitterError):
        return f"🐦 Error de Twitter: {e}"
    return f"💥 Error inesperado: {type(e).__name__}: {e}"


# ─── Herramientas MCP ─────────────────────────────────────────────────────────

@mcp.tool()
async def x_set_cookies(cookies: str) -> str:
    """
    Configura las cookies de sesión de Twitter para esta sesión.
    Obtén auth_token y ct0 de: x.com → DevTools (F12) → Application → Cookies.
    cookies: string formato 'auth_token=xxx; ct0=yyy'
    """
    get_client(cookies)
    return "✅ Cookies configuradas correctamente."


@mcp.tool()
async def x_validate_cookies() -> str:
    """Verifica que las cookies actuales sean válidas."""
    try:
        client = get_client()
        result = await client.validate_cookies()
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_profile(username: str) -> str:
    """
    Obtiene el perfil completo de un usuario de Twitter/X.
    username: nombre de usuario sin @ (ej: 'elonmusk')
    """
    try:
        client = get_client()
        profile = await scrape_profile(client, username)
        return json.dumps(profile, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_followers(username: str, limit: int = 100) -> str:
    """
    Obtiene la lista de followers de un usuario.
    username: nombre de usuario sin @
    limit: máximo de usuarios a obtener (default 100, max recomendado 500)
    """
    try:
        client = get_client()
        followers = await scrape_followers(client, username, limit=limit)
        return json.dumps({
            "count": len(followers),
            "followers": followers,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_following(username: str, limit: int = 100) -> str:
    """
    Obtiene la lista de usuarios que sigue una cuenta.
    username: nombre de usuario sin @
    limit: máximo de usuarios a obtener
    """
    try:
        client = get_client()
        following = await scrape_following(client, username, limit=limit)
        return json.dumps({
            "count": len(following),
            "following": following,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_non_followers(username: str, limit: int = 200) -> str:
    """
    Encuentra usuarios que sigues pero que NO te siguen de vuelta.
    Útil para hacer limpieza de following.
    username: tu nombre de usuario sin @
    limit: cuántos following revisar (default 200)
    """
    try:
        client = get_client()
        non_followers = await scrape_non_followers(client, username, limit=limit)
        return json.dumps({
            "count": len(non_followers),
            "non_followers": non_followers,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_tweets(
    username: str,
    limit: int = 50,
    include_replies: bool = False,
) -> str:
    """
    Obtiene los tweets recientes de un usuario.
    username: nombre de usuario sin @
    limit: cantidad de tweets (default 50)
    include_replies: incluir respuestas (default False)
    """
    try:
        client = get_client()
        tweets = await scrape_tweets(client, username, limit=limit, include_replies=include_replies)
        return json.dumps({
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_user_likes(username: str, limit: int = 50) -> str:
    """Obtiene los tweets a los que les dio like un usuario."""
    try:
        client = get_client()
        tweets = await get_user_likes(client, username, limit=limit)
        return json.dumps({
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_search_tweets(
    query: str,
    limit: int = 50,
    mode: str = "Top",
) -> str:
    """
    Busca tweets por query.
    query: término de búsqueda
    limit: cantidad de resultados (default 50)
    mode: 'Latest' o 'Top'
    """
    try:
        client = get_client()
        tweets = await search_tweets(client, query, limit=limit, mode=mode)
        return json.dumps({
            "query": query,
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_tweet_replies(tweet_id: str, limit: int = 50) -> str:
    """Obtiene replies/conversación de un tweet."""
    try:
        client = get_client()
        tweets = await get_tweet_replies(client, tweet_id, limit=limit)
        return json.dumps({
            "tweet_id": tweet_id,
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_tweet_favoriters(tweet_id: str, limit: int = 100) -> str:
    """Obtiene usuarios que dieron like a un tweet."""
    try:
        client = get_client()
        users = await get_tweet_favoriters(client, tweet_id, limit=limit)
        return json.dumps({
            "tweet_id": tweet_id,
            "count": len(users),
            "users": users,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_tweet_retweeters(tweet_id: str, limit: int = 100) -> str:
    """Obtiene usuarios que hicieron retweet de un tweet."""
    try:
        client = get_client()
        users = await get_tweet_retweeters(client, tweet_id, limit=limit)
        return json.dumps({
            "tweet_id": tweet_id,
            "count": len(users),
            "users": users,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_bookmarks(limit: int = 50) -> str:
    """Obtiene los bookmarks del usuario autenticado. Requiere auth."""
    try:
        client = get_client()
        tweets = await get_bookmarks(client, limit=limit)
        return json.dumps({
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_home_timeline(limit: int = 50, latest: bool = False) -> str:
    """Obtiene el home timeline del usuario autenticado. Requiere auth."""
    try:
        client = get_client()
        tweets = await get_home_timeline(client, limit=limit, latest=latest)
        return json.dumps({
            "count": len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_analyze_user(username: str, limit: int = 100) -> str:
    """
    Analiza el engagement de un usuario: promedios, engagement rate,
    top tweets, mejores horas y días para publicar.
    username: nombre de usuario sin @
    limit: cuántos tweets recientes analizar (default 100)
    """
    try:
        client = get_client()
        profile = await scrape_profile(client, username)
        tweets = await scrape_tweets(client, username, limit=limit)
        report = analyze_tweets(tweets, profile=profile)
        report["username"] = username
        return json.dumps(report, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_trends(woeid: int = 1) -> str:
    """Obtiene trending topics. woeid=1 es worldwide."""
    try:
        client = get_client()
        trends = await get_trends(client, woeid=woeid)
        return json.dumps({
            "count": len(trends),
            "trends": trends,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_post_tweet(
    text: str,
    reply_to_id: str | None = None,
) -> str:
    """
    Publica un tweet. Requiere autenticación (auth_token).
    text: contenido del tweet (máx 280 caracteres)
    reply_to_id: ID del tweet al que responder (opcional)
    """
    try:
        client = get_client()
        result = await post_tweet(client, text, reply_to_id=reply_to_id)
        if result["success"]:
            return f"✅ Tweet publicado. ID: {result['tweet_id']}"
        return "❌ No se pudo publicar el tweet."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_post_thread(tweets: list[str], delay: float = 1.5) -> str:
    """
    Publica un hilo de tweets (cada uno responde al anterior). Requiere auth.
    tweets: lista de textos en orden
    delay: segundos entre tweets (default 1.5)
    """
    try:
        client = get_client()
        result = await post_thread(client, tweets, delay_seconds=delay)
        if result["success"]:
            return (
                f"✅ Hilo publicado ({result['count']} tweets).\n"
                f"  Root: {result['root_id']}\n"
                f"  IDs: {', '.join(result['tweet_ids'])}"
            )
        return f"❌ {result.get('error', 'Error publicando hilo')}"
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_compare_accounts(user_a: str, user_b: str, limit: int = 50) -> str:
    """
    Compara dos cuentas: followers, engagement rate y promedios.
    user_a / user_b: nombres de usuario sin @
    limit: tweets recientes a analizar por cuenta (default 50)
    """
    try:
        client = get_client()
        prof_a, tw_a, prof_b, tw_b = await asyncio.gather(
            scrape_profile(client, user_a),
            scrape_tweets(client, user_a, limit=limit),
            scrape_profile(client, user_b),
            scrape_tweets(client, user_b, limit=limit),
        )
        report = compare_accounts(prof_a, tw_a, prof_b, tw_b)
        return json.dumps(report, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_build_search_query(
    base: str = "",
    from_user: str | None = None,
    since: str | None = None,
    until: str | None = None,
    min_faves: int | None = None,
    lang: str | None = None,
    exclude_retweets: bool = False,
) -> str:
    """
    Construye una query de búsqueda avanzada de X (operadores from/since/min_faves…).
    Úsala con x_search_tweets.
    """
    q = build_search_query(
        base,
        from_user=from_user,
        since=since,
        until=until,
        min_faves=min_faves,
        lang=lang,
        exclude_retweets=exclude_retweets,
    )
    return json.dumps({"query": q}, ensure_ascii=False)


@mcp.tool()
async def x_delete_tweet(tweet_id: str) -> str:
    """
    Elimina un tweet por su ID. Requiere autenticación.
    tweet_id: ID numérico del tweet
    """
    try:
        client = get_client()
        result = await delete_tweet(client, tweet_id)
        return "✅ Tweet eliminado." if result["success"] else "❌ No se pudo eliminar el tweet."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_like_tweet(tweet_id: str) -> str:
    """Da like a un tweet. Requiere autenticación."""
    try:
        result = await like_tweet(get_client(), tweet_id)
        return "✅ Like dado." if result["success"] else "❌ No se pudo dar like."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_unlike_tweet(tweet_id: str) -> str:
    """Quita el like de un tweet. Requiere autenticación."""
    try:
        result = await unlike_tweet(get_client(), tweet_id)
        return "✅ Like quitado." if result["success"] else "❌ No se pudo quitar el like."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_retweet(tweet_id: str) -> str:
    """Hace retweet de un tweet. Requiere autenticación."""
    try:
        result = await retweet(get_client(), tweet_id)
        return "✅ Retweet hecho." if result["success"] else "❌ No se pudo hacer retweet."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_follow_user(username: str) -> str:
    """
    Sigue a un usuario. Requiere autenticación.
    username: nombre de usuario sin @
    """
    try:
        client = get_client()
        user_id = await get_user_id(client, username)
        result = await follow_user(client, user_id)
        return f"✅ Siguiendo a @{username}." if result["success"] else f"❌ No se pudo seguir a @{username}."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_unfollow_user(username: str) -> str:
    """
    Deja de seguir a un usuario. Requiere autenticación.
    username: nombre de usuario sin @
    """
    try:
        client = get_client()
        user_id = await get_user_id(client, username)
        result = await unfollow_user(client, user_id)
        return f"✅ Dejaste de seguir a @{username}." if result["success"] else f"❌ No se pudo hacer unfollow de @{username}."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_bookmark_tweet(tweet_id: str) -> str:
    """Agrega un tweet a bookmarks. Requiere autenticación."""
    try:
        client = get_client()
        result = await create_bookmark(client, tweet_id)
        return "✅ Bookmark agregado." if result["success"] else "❌ No se pudo agregar bookmark."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_unbookmark_tweet(tweet_id: str) -> str:
    """Elimina un tweet de bookmarks. Requiere autenticación."""
    try:
        client = get_client()
        result = await delete_bookmark(client, tweet_id)
        return "✅ Bookmark eliminado." if result["success"] else "❌ No se pudo eliminar bookmark."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_bulk_unfollow_non_followers(
    username: str,
    limit: int = 200,
    delay: float = 2.0,
    dry_run: bool = False,
) -> str:
    """
    Hace unfollow masivo de todos los que no te siguen de vuelta.
    ÚSALO CON CUIDADO — hace cambios reales en tu cuenta.
    username: tu nombre de usuario sin @
    limit: cuántos following revisar (default 200)
    delay: segundos entre cada unfollow (default 2.0, no bajar de 1.0)
    dry_run: si es True solo muestra quién sería unfollowed, sin hacer nada
    """
    try:
        client = get_client()
        non_followers = await scrape_non_followers(client, username, limit=limit)

        if not non_followers:
            return "✅ ¡Todos tus following te siguen de vuelta! No hay nada que hacer."

        user_ids = [u["id"] for u in non_followers if u.get("id")]
        names = [f"@{u['username']}" for u in non_followers[:5]]
        preview = ", ".join(names)
        if len(non_followers) > 5:
            preview += f" y {len(non_followers) - 5} más..."

        if dry_run:
            return (
                f"🔍 DRY-RUN — no se hizo ningún unfollow.\n"
                f"  Se haría unfollow de: {len(user_ids)} usuarios\n"
                f"  Primeros: {preview}"
            )

        result = await bulk_unfollow(client, user_ids, delay_seconds=delay)

        return (
            f"✅ Unfollow masivo completado.\n"
            f"  Total:   {result['total']}\n"
            f"  Éxitos:  {result['success']}\n"
            f"  Fallos:  {result['failed']}\n"
            f"  Usuarios: {preview}"
        )
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_list_drafts(status: str = "pending") -> str:
    """List write drafts. status: pending|approved|discarded|executed or empty for all."""
    try:
        from .drafts import list_drafts

        items = list_drafts(status=status or None)
        return json.dumps({"count": len(items), "drafts": items}, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_approve_draft(draft_id: str) -> str:
    """Mark a draft as approved (does not execute; use CLI drafts approve to run)."""
    try:
        from .drafts import approve

        d = approve(draft_id)
        if not d:
            return f"Draft not found: {draft_id}"
        return f"✅ Draft {draft_id} approved. Run via: xactions drafts approve {draft_id}"
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_discard_draft(draft_id: str) -> str:
    """Discard a pending draft."""
    try:
        from .drafts import discard

        d = discard(draft_id)
        if not d:
            return f"Draft not found: {draft_id}"
        return f"🗑️ Draft {draft_id} discarded."
    except Exception as e:
        return _fmt_error(e)


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from .mcp_groups import apply_env_filter_to_mcp

    kept = apply_env_filter_to_mcp(mcp)
    logging.getLogger(__name__).info("MCP tools advertised: %d", len(kept))
    mcp.run(transport="stdio")
