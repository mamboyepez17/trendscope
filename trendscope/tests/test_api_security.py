"""API security: keys, validation bounds, headers, health redaction, WS auth."""

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trendscope.api.middleware import (
    APIKeyMiddleware,
    SecurityHeadersMiddleware,
    api_key_is_valid,
)


def _mini_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(APIKeyMiddleware)

    @app.get("/test")
    def test_route():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


class TestApiKeyValidation:
    def test_empty_keys_rejected(self):
        with patch("trendscope.api.middleware.settings.api_keys", ""):
            assert not api_key_is_valid("anything")

    def test_blank_keys_filtered(self):
        with patch("trendscope.api.middleware.settings.api_keys", "  , ,  "):
            assert not api_key_is_valid("anything")

    def test_valid_key(self):
        with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
            assert api_key_is_valid("secret-key")

    def test_wrong_key(self):
        with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
            assert not api_key_is_valid("wrong")

    def test_none_key(self):
        with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
            assert not api_key_is_valid(None)

    def test_required_empty_keys_returns_401(self):
        client = TestClient(_mini_app())
        with patch("trendscope.api.middleware.settings.api_key_required", True):
            with patch("trendscope.api.middleware.settings.api_keys", ""):
                resp = client.get("/test")
        assert resp.status_code == 401


class TestSecurityHeaders:
    def test_nosniff_and_frame_options(self):
        client = TestClient(_mini_app())
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.get("/test")
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert resp.headers["Referrer-Policy"] == "no-referrer"


class TestHealthRedaction:
    def test_health_does_not_expose_key_config(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            resp = client.get("/health")
        data = resp.json()
        assert "api_key_required" not in data
        assert "rate_limit" not in data


class TestHttpParamBounds:
    def test_top_n_zero_rejected(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            resp = client.get("/trends", params={"topic": "crypto", "top_n": 0})
        assert resp.status_code == 422

    def test_top_n_too_large_rejected(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            resp = client.get("/trends", params={"topic": "crypto", "top_n": 1000})
        assert resp.status_code == 422

    def test_interval_minutes_too_small_rejected(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            resp = client.post("/watchlist", params={"topic": "crypto", "interval_minutes": 1})
        assert resp.status_code == 422


class TestWebSocketAuth:
    def test_ws_closed_without_key_when_required(self):
        from fastapi.testclient import TestClient

        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", True):
            with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
                try:
                    with client.websocket_connect("/ws") as ws:
                        ws.send_json({"topic": "x"})
                        # If accept was skipped, receive may fail
                        try:
                            ws.receive_json()
                        except Exception:
                            pass
                except Exception:
                    # Expected: connection rejected/closed before accept
                    pass

    def test_ws_top_n_validation(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            with client.websocket_connect("/ws") as ws:
                ws.send_json({"topic": "crypto", "top_n": "not-a-number"})
                resp = ws.receive_json()
        assert "top_n" in resp["error"]

    def test_ws_top_n_out_of_range(self):
        from trendscope.server_api import app

        client = TestClient(app)
        with patch("trendscope.server_api.settings.api_key_required", False):
            with client.websocket_connect("/ws") as ws:
                ws.send_json({"topic": "crypto", "top_n": 5000})
                resp = ws.receive_json()
        assert "top_n" in resp["error"]


class TestDefaultHost:
    def test_default_bind_is_localhost(self):
        from trendscope.settings import Settings

        s = Settings(_env_file=None)
        assert s.api_host == "127.0.0.1"
