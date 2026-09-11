"""Scope enforcement on watchlist mutations."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trendscope.api.middleware import APIKeyMiddleware


def _app():
    app = FastAPI()
    app.add_middleware(APIKeyMiddleware)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.post("/watchlist")
    def create():
        return {"created": True}

    return app


def test_scoped_key_read_ok_write_forbidden():
    client = TestClient(_app())
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch(
            "trendscope.api.middleware.settings.api_keys",
            "ro-key|acme|trends:read",
        ):
            r = client.get("/ok", headers={"X-API-Key": "ro-key"})
            assert r.status_code == 200
            w = client.post("/watchlist", headers={"X-API-Key": "ro-key"})
            assert w.status_code == 403


def test_scoped_key_with_write_allowed():
    client = TestClient(_app())
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch(
            "trendscope.api.middleware.settings.api_keys",
            "rw-key|acme|trends:read+watchlist:write",
        ):
            w = client.post("/watchlist", headers={"X-API-Key": "rw-key"})
            assert w.status_code == 200


def test_legacy_full_key_still_works():
    client = TestClient(_app())
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch("trendscope.api.middleware.settings.api_keys", "legacy-key"):
            w = client.post("/watchlist", headers={"X-API-Key": "legacy-key"})
            assert w.status_code == 200
