"""Tests for watchlist API endpoints."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendscope.server_api import app


class WatchlistAPITest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_create_watch_item(self):
        with patch("trendscope.server_api.watchlist_scheduler"):
            resp = self.client.post("/watchlist?topic=crypto+Colombia&interval_minutes=30")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["topic"], "crypto Colombia")
        self.assertEqual(data["interval_minutes"], 30)

    def test_create_with_invalid_category(self):
        with patch("trendscope.server_api.watchlist_scheduler"):
            resp = self.client.post("/watchlist?topic=x&category=not_real")
        self.assertEqual(resp.status_code, 400)

    def test_list_watch_items(self):
        with patch("trendscope.server_api.watchlist_scheduler"):
            self.client.post("/watchlist?topic=crypto")
            resp = self.client.get("/watchlist")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()["items"]), 1)

    def test_history_empty(self):
        resp = self.client.get("/history?topic=nonexistent")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_watchlist_stats(self):
        resp = self.client.get("/watchlist/stats")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("total_watchlist", resp.json())


if __name__ == "__main__":
    unittest.main()
