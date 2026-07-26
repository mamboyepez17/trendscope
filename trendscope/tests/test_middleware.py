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


if __name__ == "__main__":
    unittest.main()
