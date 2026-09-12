"""App factory for TrendScope API — no side effects at import time."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from loguru import logger

from trendscope import __version__
from trendscope.api.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from trendscope.settings import settings
from trendscope.watchlist.scheduler import WatchlistScheduler
from trendscope.watchlist.store import WatchlistStore, get_store


class AppState:
    """Dependencies of one app instance (injectable in tests)."""

    def __init__(
        self,
        store: Optional[WatchlistStore] = None,
        scheduler: Optional[WatchlistScheduler] = None,
        enable_scheduler: Optional[bool] = None,
    ):
        self.store = store if store is not None else get_store()
        self.scheduler = (
            scheduler if scheduler is not None else WatchlistScheduler(self.store)
        )
        self.enable_scheduler = (
            settings.watchlist_enabled if enable_scheduler is None else enable_scheduler
        )


def _warn_if_exposed() -> None:
    if settings.api_host not in {"127.0.0.1", "localhost", "::1"} and not settings.api_key_required:
        logger.warning(
            "API expuesta en {} SIN API key. Configura API_KEY_REQUIRED=true y API_KEYS.",
            settings.api_host,
        )


def create_app(
    store: Optional[WatchlistStore] = None,
    scheduler: Optional[WatchlistScheduler] = None,
    enable_scheduler: Optional[bool] = None,
    configure_logging: bool = False,
) -> FastAPI:
    """Construye la aplicación FastAPI. No toca la DB hasta que se use `store`."""
    if configure_logging:
        from trendscope.logging_config import setup_logging

        setup_logging()

    state = AppState(store=store, scheduler=scheduler, enable_scheduler=enable_scheduler)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        _warn_if_exposed()
        if state.enable_scheduler:
            state.scheduler.start()
        try:
            yield
        finally:
            if state.enable_scheduler:
                state.scheduler.stop()

    app = FastAPI(
        title="TrendScope API",
        description=(
            "Universal trend intelligence — multi-source analysis with sentiment, "
            "watchlist monitoring, alerts, forecasting, and async jobs."
        ),
        version=__version__,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "trends", "description": "Analyze trends and narratives"},
            {"name": "watchlist", "description": "Recurring monitoring and history"},
            {"name": "jobs", "description": "Async analysis jobs"},
            {"name": "ops", "description": "Health, metrics, cache, doctor"},
            {"name": "export", "description": "Downloadable exports"},
        ],
    )
    app.state.ts = state

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)

    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    from trendscope.api.routes import register_routes

    register_routes(app, state)
    return app


def get_app_state(app: FastAPI) -> AppState:
    return app.state.ts
