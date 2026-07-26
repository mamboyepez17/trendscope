"""Middlewares para la API REST de TrendScope."""

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from trendscope.settings import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting simple por IP: configurable desde settings."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        max_requests = settings.api_rate_limit
        window_seconds = settings.api_rate_window
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Limpiar ventana
        window = self._requests.get(client_ip, [])
        window = [t for t in window if now - t < window_seconds]

        if len(window) >= max_requests:
            return Response(
                content='{"detail":"Rate limit exceeded. Try again later."}',
                status_code=429,
                media_type="application/json",
            )

        window.append(now)
        self._requests[client_ip] = window

        return await call_next(request)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Validación opcional de API key por header X-API-Key."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not settings.api_key_required:
            return await call_next(request)

        # Permitir health check y docs sin key
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        keys = set(settings.api_keys.split(",")) if settings.api_keys else set()
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in keys:
            return Response(
                content='{"detail":"Invalid or missing API key. Use header X-API-Key."}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
