"""
XActions-PY — MCP Server
Servidor MCP para agentes AI (Claude, Mambo, etc.)
Sin npm. Usa FastMCP + httpx puro.

Herramientas disponibles:
  x_get_profile       — Perfil de un usuario
  x_get_followers     — Lista de followers
  x_get_following     — Lista de following
  x_get_non_followers — Usuarios que no te siguen de vuelta
  x_get_tweets        — Tweets de un usuario
  x_search_tweets     — Búsqueda de tweets
  x_post_tweet        — Publicar tweet
  x_delete_tweet      — Eliminar tweet
  x_like_tweet        — Like a un tweet
  x_unlike_tweet      — Quitar like
  x_retweet           — Retweet
  x_follow_user       — Seguir usuario
  x_unfollow_user     — Dejar de seguir
  x_bulk_unfollow     — Unfollow masivo de no-followers

Config vía variables de entorno:
  TWITTER_COOKIES  — String completo de cookies (auth_token=xxx; ct0=yyy)
  TWITTER_PROXY    — Proxy opcional (http://... o socks5://...)
"""

import os
import json
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Importar cliente y scrapers
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper.client import TwitterClient, TwitterError, AuthError, RateLimitError, NotFoundError
from scraper.scrapers import (
    scrape_profile,
    scrape_followers,
    scrape_following,
    scrape_non_followers,
    scrape_tweets,
    search_tweets,
    get_user_id,
)
from actions.actions import (
    post_tweet,
    delete_tweet,
    like_tweet,
    unlike_tweet,
    retweet,
    follow_user,
    unfollow_user,
    bulk_unfollow,
)

# ─── Inicialización ───────────────────────────────────────────────────────────

mcp = FastMCP(
    "xactions-py",
    instructions="X/Twitter automation toolkit — Python port of XActions. Sin npm.",
)

_cookies = os.getenv("TWITTER_COOKIES", "")
_proxy   = os.getenv("TWITTER_PROXY")
_client: Optional[TwitterClient] = None


def get_client(cookies: Optional[str] = None) -> TwitterClient:
    """Retorna el cliente singleton, reconfigurándolo si se pasan cookies nuevas."""
    global _client
    effective_cookies = cookies or _cookies
    if _client is None or (cookies and cookies != _client._cookie_str):
        _client = TwitterClient(cookies=effective_cookies, proxy=_proxy)
    return _client


def _fmt_error(e: Exception) -> str:
    if isinstance(e, AuthError):
        return f"❌ Error de autenticación: {e}. Verifica tu auth_token y ct0."
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
async def x_get_profile(username: str) -> str:
    """
    Obtiene el perfil completo de un usuario de Twitter/X.
    username: nombre de usuario sin @ (ej: 'elonmusk')
    """
    try:
        client  = get_client()
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
        client    = get_client()
        followers = await scrape_followers(client, username, limit=limit)
        return json.dumps({
            "count":     len(followers),
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
        client    = get_client()
        following = await scrape_following(client, username, limit=limit)
        return json.dumps({
            "count":     len(following),
            "following": following,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_get_non_followers(username: str, limit: int = 200) -> str:
    """
    Encuentra usuarios que sigues pero que NO te siguen de vuelta.
    Útil para hacer limpieza de following.
    username: nombre de usuario sin @
    limit: cuántos following revisar (default 200)
    """
    try:
        client       = get_client()
        non_followers = await scrape_non_followers(client, username, limit=limit)
        return json.dumps({
            "count":         len(non_followers),
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
            "count":  len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_search_tweets(
    query: str,
    limit: int = 50,
    mode: str = "Latest",
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
            "query":  query,
            "count":  len(tweets),
            "tweets": tweets,
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_post_tweet(
    text: str,
    reply_to_id: Optional[str] = None,
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
        client  = get_client()
        user_id = await get_user_id(client, username)
        result  = await follow_user(client, user_id)
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
        client  = get_client()
        user_id = await get_user_id(client, username)
        result  = await unfollow_user(client, user_id)
        return f"✅ Dejaste de seguir a @{username}." if result["success"] else f"❌ No se pudo hacer unfollow de @{username}."
    except Exception as e:
        return _fmt_error(e)


@mcp.tool()
async def x_bulk_unfollow_non_followers(username: str, limit: int = 200, delay: float = 2.0) -> str:
    """
    Hace unfollow masivo de todos los que no te siguen de vuelta.
    ÚSALO CON CUIDADO — hace cambios reales en tu cuenta.
    username: tu nombre de usuario sin @
    limit: cuántos following revisar (default 200)
    delay: segundos entre cada unfollow (default 2.0, no bajar de 1.0)
    """
    try:
        client        = get_client()
        non_followers = await scrape_non_followers(client, username, limit=limit)

        if not non_followers:
            return "✅ ¡Todos tus following te siguen de vuelta! No hay nada que hacer."

        user_ids = [u["id"] for u in non_followers if u.get("id")]
        names    = [f"@{u['username']}" for u in non_followers[:5]]
        preview  = ", ".join(names)
        if len(non_followers) > 5:
            preview += f" y {len(non_followers) - 5} más..."

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


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run(transport="stdio")
