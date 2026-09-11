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
    return {k.strip() for k in settings.api_keys.split(",") if k.strip()}


def api_key_is_valid(api_key: str | None) -> bool:
    if not api_key:
        return False
    keys = _parsed_api_keys()
    if not keys:
        return False
    return any(hmac.compare_digest(api_key, k) for k in keys)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting simple por IP: configurable desde settings."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._requests: dict[str, deque[float]] = {}
        self._last_prune = time.time()

    def _prune_stale(self, now: float) -> None:
        # Evitar memory leak: purgar IPs cuya ventana esté vacía
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

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        max_requests = settings.api_rate_limit
        window_seconds = settings.api_rate_window
        client_ip = _client_ip(request)
        now = time.time()

        self._prune_stale(now)

        window = self._requests.get(client_ip)
        if window is None:
            window = deque()
            self._requests[client_ip] = window

        while window and now - window[0] >= window_seconds:
            window.popleft()

        if len(window) >= max_requests:
            retry_after = int(max(1, window_seconds - (now - window[0]))) if window else window_seconds
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        window.append(now)
        response = await call_next(request)
        remaining = max(0, max_requests - len(window))
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validación opcional de API key por header X-API-Key."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.api_key_required:
            return await call_next(request)

        # Permitir health check y docs sin key
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key_is_valid(api_key):
            return Response(
                content='{"detail":"Invalid or missing API key. Use header X-API-Key."}',
                status_code=401,
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
                    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                    "style-src 'self' 'unsafe-inline'"
                ),
            )
        return response
