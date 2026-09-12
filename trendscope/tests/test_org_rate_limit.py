"""Rate limit per org (in addition to per-IP)."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trendscope.api.middleware import APIKeyMiddleware, RateLimitMiddleware


def _app():
    app = FastAPI()
    # APIKey outermost so it sets org_id before RateLimit
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)

    @app.get("/ok")
    def ok():
        return {"ok": True}

    return app


def test_org_quota_independent():
    client = TestClient(_app())
    keys = "kA|orgA|trends:read,kB|orgB|trends:read"
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch("trendscope.api.middleware.settings.api_keys", keys):
            with patch("trendscope.api.middleware.settings.api_rate_limit", 100):
                with patch("trendscope.api.middleware.settings.org_rate_limit", 2):
                    with patch("trendscope.api.middleware.settings.api_rate_window", 60):
                        # orgA exhausts its org quota
                        assert client.get("/ok", headers={"X-API-Key": "kA"}).status_code == 200
                        assert client.get("/ok", headers={"X-API-Key": "kA"}).status_code == 200
                        assert client.get("/ok", headers={"X-API-Key": "kA"}).status_code == 429
                        # orgB still has budget
                        assert client.get("/ok", headers={"X-API-Key": "kB"}).status_code == 200


def test_org_headers_show_org_limit():
    client = TestClient(_app())
    with patch("trendscope.api.middleware.settings.api_key_required", True):
        with patch("trendscope.api.middleware.settings.api_keys", "k|orgX|trends:read"):
            with patch("trendscope.api.middleware.settings.api_rate_limit", 50):
                with patch("trendscope.api.middleware.settings.org_rate_limit", 7):
                    resp = client.get("/ok", headers={"X-API-Key": "k"})
    assert resp.headers["X-RateLimit-Limit"] == "7"
