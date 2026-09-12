"""Middlewares para la API REST de TrendScope."""

import hmac
import time
from collections import deque
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from trendscope.settings import settings


def _client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        xff = request.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()
        xri = request.headers.get("X-Real-IP")
        if xri:
            return xri.strip()
    return request.client.host if request.client else "unknown"


def _parsed_api_keys() -> set[str]:
    if not settings.api_keys:
        return set()
    from trendscope.api.auth_keys import parse_api_keys

    return {k.key for k in parse_api_keys(settings.api_keys)}


def api_key_is_valid(api_key: str | None) -> bool:
    if not api_key:
        return False
    from trendscope.api.auth_keys import match_key

    return match_key(settings.api_keys, api_key) is not None


def resolve_api_key(api_key: str | None):
    from trendscope.api.auth_keys import match_key

    if not api_key:
        return None
    return match_key(settings.api_keys, api_key)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting por IP y, si hay API key, también por org."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._requests: dict[str, deque[float]] = {}
        self._last_prune = time.time()

    def _prune_stale(self, now: float) -> None:
        if now - self._last_prune < 30:
            return
        window_seconds = settings.api_rate_window
        stale = [
            ip
            for ip, window in self._requests.items()
            if not window or now - window[-1] >= window_seconds
        ]
        for ip in stale:
            del self._requests[ip]
        self._last_prune = now

    def _check_bucket(
        self, key: str, now: float, max_requests: int, window_seconds: int
    ) -> tuple[bool, int, int]:
        """Devuelve (allowed, remaining, retry_after)."""
        window = self._requests.get(key)
        if window is None:
            window = deque()
            self._requests[key] = window
        while window and now - window[0] >= window_seconds:
            window.popleft()
        if len(window) >= max_requests:
            retry_after = int(max(1, window_seconds - (now - window[0]))) if window else window_seconds
            return False, 0, retry_after
        window.append(now)
        return True, max(0, max_requests - len(window)), 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        max_requests = settings.api_rate_limit
        window_seconds = settings.api_rate_window
        client_ip = _client_ip(request)
        now = time.time()

        self._prune_stale(now)

        # Si la API key middleware ya identificó la org, aplicar cuota por org además de IP
        org_id = getattr(request.state, "org_id", None)
        api_key = request.headers.get("X-API-Key")
        org_limit = settings.org_rate_limit or max_requests

        allowed, remaining, retry_after = self._check_bucket(
            f"ip:{client_ip}", now, max_requests, window_seconds
        )
        limit_shown = max_requests
        if allowed and org_id and api_key:
            allowed, remaining, retry_after = self._check_bucket(
                f"org:{org_id}", now, org_limit, window_seconds
            )
            limit_shown = org_limit

        if not allowed:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit_shown),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit_shown)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validación opcional de API key por header X-API-Key (con org/scopes)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.api_key_required:
            return await call_next(request)

        # Permitir health check y docs sin key
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc", "/metrics"}:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        matched = resolve_api_key(api_key)
        if matched is None:
            return Response(
                content='{"detail":"Invalid or missing API key. Use header X-API-Key."}',
                status_code=401,
                media_type="application/json",
            )

        request.state.org_id = matched.org_id
        request.state.scopes = matched.scopes

        # Scope check para mutaciones de watchlist
        path = request.url.path
        method = request.method.upper()
        if path.startswith("/watchlist") and method in {"POST", "PUT", "DELETE"}:
            if not matched.allows("watchlist:write"):
                return Response(
                    content='{"detail":"API key lacks watchlist:write scope"}',
                    status_code=403,
                    media_type="application/json",
                )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Cabeceras de seguridad básicas en todas las respuestas HTTP."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.url.path == "/dashboard":
            response.headers.setdefault(
                "Content-Security-Policy",
                (
                    "default-src 'self'; "
                    "img-src 'self' data:; "
                    "script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; "
                    "connect-src 'self' ws: wss:"
                ),
            )
        return response
