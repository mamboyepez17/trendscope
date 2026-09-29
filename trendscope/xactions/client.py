"""
XActions-PY — Twitter HTTP Client
Replica del TwitterHttpClient de XActions pero en Python puro.
Sin npm, sin Puppeteer. Solo httpx + las GraphQL internas de Twitter.

v1.2.0:
  - Cliente HTTP persistente (connection pooling / keep-alive).
  - Reintentos con backoff exponencial para errores de red y rate limits.
  - Logging estructurado.
  - Context manager async para cerrar conexiones de forma segura.
  - Helpers REST (GET/POST) para validación de sesión y endpoints legacy.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
import uuid
from typing import Any
from urllib.parse import unquote

import httpx

from .gql_refresh import endpoints_with_cache, refresh_endpoints
from .transaction_id import generate_transaction_id

# ─── Bearer Token público (embebido en el JS bundle de Twitter) ───────────────
BEARER_TOKEN = (
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs"
    "%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)

GRAPHQL_BASE = "https://x.com/i/api/graphql"
REST_BASE = "https://x.com/i/api"
API_BASE = "https://api.x.com"
UPLOAD_BASE = "https://upload.x.com"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# ─── GraphQL endpoints (defaults; se mezclan con cache ~/.xactions) ───────────
_DEFAULT_GRAPHQL_ENDPOINTS: dict[str, dict[str, Any]] = {
    "UserByScreenName": {"queryId": "NimuplG1OB7Fd2btCLdBOw", "operationName": "UserByScreenName"},
    "UserByRestId": {"queryId": "tD8zKvQzwY3kdx5yz6YmOw", "operationName": "UserByRestId"},
    "UserTweets": {"queryId": "QWF3SzpHmykQHsQMixG0cg", "operationName": "UserTweets"},
    "UserTweetsAndReplies": {"queryId": "vMkJyzx1wdmvOeeNG0n6Wg", "operationName": "UserTweetsAndReplies"},
    "UserMedia": {"queryId": "2tLOJWwGuCTytDrGBg8VwQ", "operationName": "UserMedia"},
    "UserLikes": {"queryId": "IohM3gxQHfvWePH5E3KuNA", "operationName": "Likes"},
    "TweetDetail": {"queryId": "U0HTv-bAWTBYylwEMT7x5A", "operationName": "TweetDetail"},
    "Favoriters": {"queryId": "LLkw5EcVutJL6y-2gkz22A", "operationName": "Favoriters"},
    "Retweeters": {"queryId": "X-XEqG5qHQSAwmvy00xfyQ", "operationName": "Retweeters"},
    "SearchTimeline": {"queryId": "flaR-PUMshxFWZWPNpq4zA", "operationName": "SearchTimeline", "method": "POST"},
    "Followers": {"queryId": "gC_lyAxZOptAMLCJX5UhWw", "operationName": "Followers", "method": "POST"},
    "Following": {"queryId": "2vUj-_Ek-UmBVDNtd8OnQA", "operationName": "Following"},
    "Bookmarks": {"queryId": "qToeLeMs43Q8cr7tRYXmaQ", "operationName": "Bookmarks"},
    "HomeTimeline": {"queryId": "-X_hcgQzmHGl29-UXxz4sw", "operationName": "HomeTimeline", "method": "POST"},
    "HomeLatestTimeline": {"queryId": "U0cdisy7QFIoTfu3-Okw0A", "operationName": "HomeLatestTimeline", "method": "POST"},
    # Mutations
    "CreateTweet": {"queryId": "SiM_cAu83R0wnrpmKQQSEw", "operationName": "CreateTweet"},
    "FavoriteTweet": {"queryId": "lI07N6Otwv1PhnEgXILM7A", "operationName": "FavoriteTweet"},
    "UnfavoriteTweet": {"queryId": "ZYKSe-w7KEslx3JhSIk5LA", "operationName": "UnfavoriteTweet"},
    "CreateRetweet": {"queryId": "ojPdsZsimiJrUGLR1sjUtA", "operationName": "CreateRetweet"},
    "DeleteRetweet": {"queryId": "iQtK4dl5hBmXewYZuEOKVw", "operationName": "DeleteRetweet"},
    "DeleteTweet": {"queryId": "VaenaVgh5q5ih7kvyVjgtg", "operationName": "DeleteTweet"},
    "CreateBookmark": {"queryId": "aoDbu3RHznuiSkQ9aNM67Q", "operationName": "CreateBookmark"},
    "DeleteBookmark": {"queryId": "Wlmlj2-xzyS1GN3a6cj-mQ", "operationName": "DeleteBookmark"},
    "FollowUser": {"queryId": None, "operationName": None},  # REST endpoint
    "UnfollowUser": {"queryId": None, "operationName": None},  # REST endpoint
}

# Store vivo: defaults + cache en disco. Se actualiza con refresh_graphql_endpoints().
GRAPHQL_ENDPOINTS: dict[str, dict[str, Any]] = endpoints_with_cache(_DEFAULT_GRAPHQL_ENDPOINTS)

# Refresh global (una sola vez por proceso si varios clientes lo piden)
_gql_refresh_lock: asyncio.Lock | None = None
_gql_refreshed_this_process = False
# Tests/CI pueden desactivar el refresh en red: XACTIONS_NO_GQL_REFRESH=1
_NO_GQL_REFRESH = os.getenv("XACTIONS_NO_GQL_REFRESH", "").strip() in {"1", "true", "yes"}

DEFAULT_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": False,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}

_log = logging.getLogger(__name__)


def _is_stale_query_error(message: str) -> bool:
    """Detecta errores típicos de queryId roto/obsoleto."""
    msg = (message or "").lower()
    needles = (
        "query does not exist",
        "query not found",
        "no query",
        "invalid query",
        "queryid",
        "operationname",
        "cannot query field",
        "document is not defined",
    )
    return any(n in msg for n in needles)


async def refresh_graphql_endpoints(
    force: bool = False,
    cookie: str | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Refresca GRAPHQL_ENDPOINTS (una vez por proceso salvo force=True).
    Si se pasa `cookie` (auth_token/ct0), se prioriza el bundle logueado de X
    y twikit queda solo como fallback.
    """
    global _gql_refreshed_this_process, _gql_refresh_lock
    if _NO_GQL_REFRESH:
        _log.debug("Refresh GraphQL desactivado (XACTIONS_NO_GQL_REFRESH)")
        return GRAPHQL_ENDPOINTS
    if _gql_refresh_lock is None:
        _gql_refresh_lock = asyncio.Lock()
    async with _gql_refresh_lock:
        if _gql_refreshed_this_process and not force:
            return GRAPHQL_ENDPOINTS
        _log.info("Refrescando GraphQL query IDs (auth=%s)…", bool(cookie))
        try:
            merged = await refresh_endpoints(GRAPHQL_ENDPOINTS, cookie=cookie)
        except (httpx.HTTPError, OSError, ValueError) as e:
            _log.warning("Refresh GraphQL falló: %s", e)
            _gql_refreshed_this_process = True  # no martillear la red
            return GRAPHQL_ENDPOINTS
        GRAPHQL_ENDPOINTS.clear()
        GRAPHQL_ENDPOINTS.update(merged)
        _gql_refreshed_this_process = True
        return GRAPHQL_ENDPOINTS


# ─── Excepciones ───────────────────────────────────────────────────────────────

class TwitterError(Exception):
    """Base de errores del cliente."""
    pass


class RateLimitError(TwitterError):
    """HTTP 429 o código 88 de la API."""
    pass


class AuthError(TwitterError):
    """HTTP 401/403 o código 32 de la API."""
    pass


class NotFoundError(TwitterError):
    """HTTP 404 o código 34 de la API."""
    pass


class ForbiddenError(TwitterError):
    """HTTP 403 — acceso denegado a un recurso."""
    pass


# ─── Cliente ────────────────────────────────────────────────────────────────────

class TwitterClient:
    """
    Cliente HTTP asíncrono para la GraphQL interna de Twitter/X.
    Equivalente directo del TwitterHttpClient de XActions en Python.

    Uso:
        async with TwitterClient(cookies=...) as client:
            profile = await scrape_profile(client, "elonmusk")
    """

    def __init__(
        self,
        cookies: str | None = None,
        proxy: str | None = None,
        max_retries: int = 3,
        timeout: float = 30.0,
        user_agent: str | None = None,
        max_rate_limit_wait: float = 60.0,
    ):
        self._cookie_str = cookies or ""
        self._cookies: dict[str, str] = {}
        self._proxy = proxy
        self._max_retries = max(0, max_retries)
        self._timeout = timeout
        self._user_agent = user_agent or random.choice(USER_AGENTS)
        self._csrf_token: str | None = None
        self._client: httpx.AsyncClient | None = None
        self._closed = False
        self._last_rate_limit_reset: int | None = None
        self._client_uuid = str(uuid.uuid4())
        # Seguimiento proactivo de rate limits por path (x-rate-limit-*)
        self._max_rate_limit_wait = max(0.0, max_rate_limit_wait)
        self._rate_limits: dict[str, dict[str, Any]] = {}

        if cookies:
            self._parse_cookies(cookies)

    # ─── Ciclo de vida ─────────────────────────────────────────────────────────

    async def __aenter__(self) -> TwitterClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    def __del__(self):
        # Limpieza best-effort si el usuario olvidó cerrar.
        if self._client is not None and not self._closed:
            try:
                asyncio.get_running_loop().create_task(self.aclose())
            except RuntimeError:
                pass

    async def aclose(self) -> None:
        """Cierra el cliente HTTP y libera conexiones."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self._closed = True
        _log.debug("TwitterClient cerrado")

    def close(self) -> None:
        """Cierre síncrono (útil para wrappers sync)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No hay loop corriendo; usamos un loop nuevo.
            asyncio.run(self.aclose())
        else:
            # Hay un loop corriendo: no se puede bloquear; programamos el cierre.
            loop = asyncio.get_event_loop()
            loop.create_task(self.aclose())

    @property
    def _http(self) -> httpx.AsyncClient:
        """Devuelve el cliente HTTP persistente, creándolo si es necesario."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                proxy=self._proxy,
                timeout=self._timeout,
                follow_redirects=True,
            )
            _log.debug("TwitterClient: cliente HTTP creado")
        return self._client

    # ─── Cookies / auth ──────────────────────────────────────────────────────────

    def _parse_cookies(self, cookie_str: str) -> None:
        """Parsea string de cookies 'name=val; name2=val2' a dict."""
        self._cookies = {}
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                self._cookies[k.strip()] = unquote(v.strip())
        self._csrf_token = self._cookies.get("ct0", "")
        self._cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())

    def set_cookies(self, cookie_str: str) -> None:
        self._cookie_str = cookie_str
        self._parse_cookies(cookie_str)

    def is_authenticated(self) -> bool:
        return bool(self._cookies.get("auth_token"))

    def _build_headers(
        self,
        extra: dict[str, str] | None = None,
        method: str = "GET",
        path: str = "/",
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "User-Agent": self._user_agent,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://x.com/",
            "Origin": "https://x.com",
            "x-twitter-active-user": "yes",
            "x-twitter-client-language": "en",
            "x-client-uuid": self._client_uuid,
            "x-client-transaction-id": generate_transaction_id(method, path),
        }
        if self._csrf_token:
            headers["x-csrf-token"] = self._csrf_token
        if self._cookies:
            headers["Cookie"] = self._cookie_str
        if self.is_authenticated():
            headers["x-twitter-auth-type"] = "OAuth2Session"
        if extra:
            headers.update(extra)
        return headers

    # ─── Requests ────────────────────────────────────────────────────────────────

    def _rate_limit_key(self, url: str) -> str:
        """Clave estable por recurso GraphQL/REST (sin query string ni queryId)."""
        path = url.split("?", 1)[0].rstrip("/")
        parts = [p for p in path.split("/") if p]
        if "graphql" in parts:
            gi = parts.index("graphql")
            # .../graphql/<queryId>/<Operation>
            if len(parts) > gi + 2:
                return f"graphql/{parts[gi + 2]}"
        return "/".join(parts[-2:]) if len(parts) >= 2 else path

    def _record_rate_limit(self, url: str, response: httpx.Response) -> None:
        """Guarda remaining/reset de la respuesta para throttle proactivo."""
        remaining = response.headers.get("x-rate-limit-remaining")
        reset = response.headers.get("x-rate-limit-reset")
        if remaining is None and reset is None:
            return
        key = self._rate_limit_key(url)
        entry: dict[str, Any] = {"updated_at": time.time()}
        try:
            if remaining is not None:
                entry["remaining"] = int(remaining)
            if reset is not None:
                entry["reset"] = int(reset)
                self._last_rate_limit_reset = int(reset)
        except (ValueError, TypeError):
            return
        self._rate_limits[key] = entry

    def rate_limit_status(self) -> dict[str, dict[str, Any]]:
        """Snapshot de rate limits conocidos (para CLI/tests)."""
        return {k: dict(v) for k, v in self._rate_limits.items()}

    async def _maybe_throttle(self, url: str) -> None:
        """
        Si remaining=0 y el reset está en el futuro, espera ANTES del request
        (evita pegar 429 cuando ya sabemos que se agotó).
        """
        key = self._rate_limit_key(url)
        entry = self._rate_limits.get(key)
        if not entry:
            return
        remaining = entry.get("remaining")
        reset = entry.get("reset")
        if remaining is None or remaining > 0 or reset is None:
            return
        wait = float(reset) - time.time()
        if wait <= 0:
            return
        # Cap configurable; si el reset está lejos, no bloqueamos el proceso entero
        wait = min(wait, self._max_rate_limit_wait)
        if wait <= 0:
            return
        _log.warning(
            "Rate limit agotado en %s (remaining=0). Espera proactiva %.1fs",
            key,
            wait,
        )
        await asyncio.sleep(wait)

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        """Calcula segundos de espera antes de reintentar."""
        if response is not None and response.status_code == 429:
            # Twitter usa x-rate-limit-reset (timestamp unix) o retry-after.
            reset_ts = response.headers.get("x-rate-limit-reset")
            if reset_ts:
                try:
                    wait = max(0.0, float(reset_ts) - time.time())
                    self._last_rate_limit_reset = int(reset_ts)
                    wait = min(wait, self._max_rate_limit_wait)
                    _log.warning("Rate limit. Esperando %.1fs (reset=%s)", wait, reset_ts)
                    return wait
                except (ValueError, TypeError):
                    pass
            retry_after = response.headers.get("retry-after")
            if retry_after:
                try:
                    return min(float(retry_after), self._max_rate_limit_wait)
                except (ValueError, TypeError):
                    pass
        return min(2.0 ** attempt, 30.0)

    async def _request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json_payload: dict[str, Any] | None = None,
        data_payload: dict[str, Any] | None = None,
        allow_replay: bool = True,
    ) -> httpx.Response:
        """Request base con reintentos, rate-limit handling y logging."""
        request_headers = self._build_headers(
            headers,
            method=method,
            path=url.split("?", 1)[0],
        )
        last_exception: Exception | None = None
        # Las mutations no se reintentan: un timeout tras ser procesada
        # por el servidor duplicaría la acción (like, tweet, unfollow...).
        max_attempts = 1 if not allow_replay else self._max_retries + 1

        for attempt in range(max_attempts):
            try:
                # Throttle proactivo si este endpoint ya se agotó
                await self._maybe_throttle(url)

                if method.upper() == "GET":
                    resp = await self._http.get(url, headers=request_headers, params=params)
                elif json_payload is not None:
                    resp = await self._http.post(url, headers=request_headers, json=json_payload)
                elif data_payload is not None:
                    resp = await self._http.post(url, headers=request_headers, data=data_payload)
                else:
                    resp = await self._http.post(url, headers=request_headers)

                self._record_rate_limit(url, resp)

                # Twitter rota el CSRF token en sesiones largas: si la respuesta
                # trae un ct0 nuevo, lo adoptamos para las próximas peticiones.
                new_ct0 = resp.cookies.get("ct0")
                if new_ct0 and new_ct0 != self._csrf_token:
                    self._csrf_token = new_ct0
                    self._cookies["ct0"] = new_ct0
                    self._cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
                    _log.debug("CSRF token actualizado desde la respuesta")

                if resp.status_code == 429:
                    if attempt < max_attempts - 1:
                        delay = self._retry_delay(attempt, resp)
                        await asyncio.sleep(delay)
                        continue
                    raise RateLimitError(f"Rate limited. Reset: {self._last_rate_limit_reset}")

                if resp.status_code == 401:
                    raise AuthError(f"No autenticado o cookie expirada (HTTP {resp.status_code})")

                if resp.status_code == 403:
                    raise ForbiddenError(f"Acceso denegado (HTTP {resp.status_code}): {resp.text[:200]}")

                if resp.status_code == 404:
                    raise NotFoundError(f"Recurso no encontrado (HTTP {resp.status_code})")

                if resp.status_code >= 400:
                    raise TwitterError(f"HTTP {resp.status_code}: {resp.text[:500]}")

                return resp

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    delay = 2.0 ** attempt
                    _log.warning("Error de red en intento %d/%d: %s. Reintentando en %.1fs", attempt + 1, max_attempts, e, delay)
                    await asyncio.sleep(delay)
                    continue
                raise TwitterError(f"Error de red tras {max_attempts} intentos: {e}")

        raise TwitterError(f"Max reintentos alcanzados: {last_exception}")

    # ─── GraphQL ─────────────────────────────────────────────────────────────────

    async def graphql(
        self,
        endpoint_name: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None = None,
        mutation: bool = False,
        _allow_refresh: bool = True,
    ) -> dict[str, Any]:
        """Ejecuta una query o mutation GraphQL contra la API interna de Twitter."""
        try:
            return await self._graphql_once(endpoint_name, variables, features, mutation)
        except (NotFoundError, TwitterError) as e:
            # QueryId roto: 404 o error GraphQL de operación inexistente.
            # Es seguro reintentar incluso en mutations: la operación no llegó a ejecutarse.
            if not _allow_refresh:
                raise
            msg = str(e)
            is_404 = isinstance(e, NotFoundError)
            if not (is_404 or _is_stale_query_error(msg)):
                raise
            _log.warning(
                "Posible queryId obsoleto en %s (%s). Intentando refresh…",
                endpoint_name,
                msg[:120],
            )
            await refresh_graphql_endpoints(force=True, cookie=self._cookie_str or None)
            return await self._graphql_once(endpoint_name, variables, features, mutation)

    async def _graphql_once(
        self,
        endpoint_name: str,
        variables: dict[str, Any],
        features: dict[str, Any] | None,
        mutation: bool,
    ) -> dict[str, Any]:
        ep = GRAPHQL_ENDPOINTS.get(endpoint_name)
        if not ep:
            raise TwitterError(f"Endpoint GraphQL desconocido: {endpoint_name}")
        query_id = ep["queryId"]
        operation = ep["operationName"]

        if not query_id or not operation:
            raise TwitterError(f"Endpoint {endpoint_name} no tiene queryId/operationName configurado")

        url = f"{GRAPHQL_BASE}/{query_id}/{operation}"
        features_payload = features if features is not None else DEFAULT_FEATURES
        use_post = mutation or ep.get("method") == "POST"

        if use_post:
            payload = {
                "variables": variables,
                "features": features_payload,
                "queryId": query_id,
            }
            resp = await self._request(
                "POST",
                url,
                headers={"Content-Type": "application/json"},
                json_payload=payload,
                allow_replay=not mutation,
            )
        else:
            params = {
                "variables": json.dumps(variables),
                "features": json.dumps(features_payload),
            }
            resp = await self._request("GET", url, params=params)

        data = resp.json()
        if "errors" in data and data["errors"]:
            err = data["errors"][0]
            code = err.get("code", 0)
            message = err.get("message", "Unknown API error")
            if code == 32:
                raise AuthError(message)
            if code == 88:
                raise RateLimitError(message)
            if code == 34:
                raise NotFoundError(message)
            if _is_stale_query_error(message):
                raise NotFoundError(message)
            raise TwitterError(f"API error {code}: {message}")

        return data

    # ─── REST helpers ────────────────────────────────────────────────────────────

    async def rest_get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """GET a un endpoint REST (ej. verify_credentials)."""
        url = f"{REST_BASE}{path}"
        resp = await self._request("GET", url, params=params)
        return resp.json()

    async def rest_post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST a un endpoint REST (usado para follow/unfollow)."""
        url = f"{REST_BASE}{path}"
        resp = await self._request(
            "POST",
            url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data_payload=data,
        )
        return resp.json()

    async def rest_upload(
        self,
        url: str,
        file_path: str,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Sube un archivo binario via multipart/form-data (media upload).
        No usa _request porque multipart no puede reintentarse de forma segura
        y requiere headers distintos (httpx pone el boundary solo).
        """
        if self._closed:
            raise TwitterError("El cliente está cerrado")
        import os

        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            files = {"media": (filename, f)}
            resp = await self._http.post(
                url,
                headers=self._build_headers(),
                files=files,
                data=extra_data or {},
            )

        if resp.status_code == 401:
            raise AuthError("No autenticado para subir media")
        if resp.status_code == 403:
            raise ForbiddenError(f"Acceso denegado al subir media: {resp.text[:200]}")
        if resp.status_code == 429:
            raise RateLimitError("Rate limited al subir media")
        if resp.status_code >= 400:
            raise TwitterError(f"HTTP {resp.status_code} al subir media: {resp.text[:300]}")

        return resp.json()

    # ─── Validación de sesión ────────────────────────────────────────────────────

    async def validate_cookies(self) -> dict[str, Any]:
        """
        Verifica que las cookies sean válidas con una query GraphQL autenticada
        (HomeLatestTimeline). El REST verify_credentials de X ya no existe.
        Devuelve {valid, username?, user_id?} o {valid: False, error}.
        """
        if not self.is_authenticated():
            raise AuthError("Falta auth_token en las cookies")
        try:
            data = await self.graphql(
                "HomeLatestTimeline",
                variables={
                    "count": 5,
                    "includePromotedContent": False,
                    "withCommunity": True,
                    "latestControlAvailable": True,
                },
            )
        except (AuthError, ForbiddenError, NotFoundError) as e:
            return {"valid": False, "error": str(e)}
        except TwitterError as e:
            # 404 de query roto no implica cookies malas; lo tratamos como inválido con detalle
            return {"valid": False, "error": str(e)}

        if not data or "data" not in data:
            return {"valid": False, "error": "Respuesta GraphQL vacía o sin data"}

        # Intentar extraer username del home (best-effort)
        username = None
        user_id = None
        try:
            instructions = (
                data.get("data", {})
                .get("home", {})
                .get("home_timeline_urt", {})
                .get("instructions", [])
            )
            for instruction in instructions:
                for entry in instruction.get("entries", []):
                    content = entry.get("content", {})
                    item = content.get("itemContent") or {}
                    user_results = (
                        item.get("tweet_results", {})
                        .get("result", {})
                        .get("core", {})
                        .get("user_results", {})
                        .get("result", {})
                    )
                    if user_results:
                        legacy = user_results.get("legacy", {})
                        username = legacy.get("screen_name")
                        user_id = user_results.get("rest_id")
                        if username:
                            break
                if username:
                    break
        except (TypeError, AttributeError):
            pass

        return {
            "valid": True,
            "user_id": user_id,
            "username": username,
            "via": "HomeLatestTimeline",
        }

    # ─── GraphQL query ID refresh (con cookies de esta sesión) ─────────────────

    async def refresh_gql_endpoints(self, force: bool = True) -> dict[str, dict[str, Any]]:
        """
        Refresca los query IDs GraphQL usando las cookies de este cliente
        (bundle logueado primero; twikit solo como fallback).
        """
        return await refresh_graphql_endpoints(
            force=force,
            cookie=self._cookie_str or None,
        )
