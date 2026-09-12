"""App factory: no DB side effects at import; injectable stores."""

import os
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_create_app_returns_fastapi(tmp_path):
    from trendscope.api.factory import create_app
    from trendscope.watchlist.store import WatchlistStore

    store = WatchlistStore(db_path=tmp_path / "w.db")
    app = create_app(store=store, enable_scheduler=False)
    assert app.title.startswith("TrendScope")


def test_isolated_app_health(tmp_path, isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_isolated_app_watchlist_uses_injected_store(tmp_path, isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        with patch("trendscope.api.factory.settings.watchlist_enabled", False):
            resp = client.post(
                "/watchlist", params={"topic": "ai", "interval_minutes": 30}
            )
    assert resp.status_code == 200
    assert resp.json()["topic"] == "ai"
    # DB under tmp, not project data/
    assert (tmp_path / "watchlist.db").exists()


def test_importing_server_api_module_exists():
    import trendscope.server_api as api

    assert hasattr(api, "app")
    assert hasattr(api, "create_app")
    assert hasattr(api, "watchlist_store")


def test_create_app_registers_core_paths(isolated_app):
    paths = {r.path for r in isolated_app.routes if hasattr(r, "path")}
    for p in (
        "/health",
        "/trends",
        "/watchlist",
        "/history",
        "/forecast",
        "/metrics",
        "/ws",
        "/jobs/{job_id}",
    ):
        assert p in paths, p
