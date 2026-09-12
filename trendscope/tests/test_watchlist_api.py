"""Tests for watchlist API endpoints (isolated app factory)."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestWatchlistAPI:
    def _client(self, isolated_app):
        return TestClient(isolated_app)

    def test_create_watch_item(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.post(
                "/watchlist?topic=crypto+Colombia&interval_minutes=30"
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["topic"] == "crypto Colombia"
        assert data["interval_minutes"] == 30

    def test_create_with_invalid_category(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.post("/watchlist?topic=x&category=not_real")
        assert resp.status_code == 400

    def test_list_watch_items(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            client.post("/watchlist?topic=crypto")
            resp = client.get("/watchlist")
        assert resp.status_code == 200
        assert len(resp.json()["items"]) >= 1

    def test_history_empty(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.get("/history?topic=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_watchlist_stats(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.get("/watchlist/stats")
        assert resp.status_code == 200
        assert "total_watchlist" in resp.json()

    def test_interval_too_small_rejected(self, isolated_app):
        client = self._client(isolated_app)
        with patch("trendscope.api.middleware.settings.api_key_required", False):
            resp = client.post("/watchlist?topic=x&interval_minutes=1")
        assert resp.status_code == 422
