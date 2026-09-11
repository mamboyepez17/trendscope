"""Tests para trendscope/api/middleware.py."""
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from trendscope.api.middleware import RateLimitMiddleware, APIKeyMiddleware


def _build_app():
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIKeyMiddleware)

    @app.get("/test")
    def test_route():
        return {"ok": True}

    return app


class MiddlewareTest(unittest.TestCase):
    def _client(self):
        return TestClient(_build_app())

    def test_rate_limit_allows_under_limit(self):
        with patch("trendscope.api.middleware.settings.api_rate_limit", 3):
            with patch("trendscope.api.middleware.settings.api_rate_window", 60):
                client = self._client()
                for _ in range(3):
                    resp = client.get("/test")
                    self.assertEqual(resp.status_code, 200)

    def test_rate_limit_blocks_over_limit(self):
        with patch("trendscope.api.middleware.settings.api_rate_limit", 3):
            with patch("trendscope.api.middleware.settings.api_rate_window", 60):
                client = self._client()
                for _ in range(3):
                    client.get("/test")
                resp = client.get("/test")
                self.assertEqual(resp.status_code, 429)

    def test_api_key_optional_by_default(self):
        client = self._client()
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.get("/test")
        self.assertEqual(resp.status_code, 200)

    def test_api_key_required_blocks_without_key(self):
        client = self._client()
        with patch("trendscope.api.middleware.settings.api_key_required", True):
            with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
                resp = client.get("/test")
        self.assertEqual(resp.status_code, 401)

    def test_api_key_required_allows_with_key(self):
        client = self._client()
        with patch("trendscope.api.middleware.settings.api_key_required", True):
            with patch("trendscope.api.middleware.settings.api_keys", "secret-key"):
                resp = client.get("/test", headers={"X-API-Key": "secret-key"})
        self.assertEqual(resp.status_code, 200)

    def test_rate_limit_headers_present(self):
        client = self._client()
        with patch("trendscope.api.middleware.settings.api_rate_limit", 10):
            with patch("trendscope.api.middleware.settings.api_rate_window", 60):
                resp = client.get("/test")
        self.assertIn("X-RateLimit-Limit", resp.headers)
        self.assertIn("X-RateLimit-Remaining", resp.headers)

    def test_rate_limit_429_includes_retry_after(self):
        client = self._client()
        with patch("trendscope.api.middleware.settings.api_rate_limit", 1):
            with patch("trendscope.api.middleware.settings.api_rate_window", 60):
                client.get("/test")
                resp = client.get("/test")
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Retry-After", resp.headers)

    def test_stale_ips_pruned(self):
        import time as time_mod

        from trendscope.api.middleware import RateLimitMiddleware

        mw = RateLimitMiddleware(app=None)
        now = time_mod.time()
        mw._requests["1.1.1.1"] = __import__("collections").deque([now - 3600])
        mw._last_prune = 0  # force prune
        with patch("trendscope.api.middleware.settings.api_rate_window", 60):
            mw._prune_stale(now)
        self.assertNotIn("1.1.1.1", mw._requests)

    def test_trust_proxy_headers_uses_xff(self):
        from starlette.datastructures import Headers
        from starlette.requests import Request

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/t",
            "headers": [(b"x-forwarded-for", b"203.0.113.9, 10.0.0.1")],
            "query_string": b"",
            "client": ("10.0.0.1", 1234),
        }
        request = Request(scope)

        with patch("trendscope.api.middleware.settings.trust_proxy_headers", True):
            from trendscope.api.middleware import _client_ip

            self.assertEqual(_client_ip(request), "203.0.113.9")

        with patch("trendscope.api.middleware.settings.trust_proxy_headers", False):
            from trendscope.api.middleware import _client_ip

            self.assertEqual(_client_ip(request), "10.0.0.1")


if __name__ == "__main__":
    unittest.main()
