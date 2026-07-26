"""Tests for WebSocket endpoint /ws."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendscope.server_api import app


class WebSocketTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def _ws_client(self, headers=None):
        headers = headers or {}
        return self.client.websocket_connect("/ws", headers=headers)

    def test_websocket_connect_and_disconnect(self):
        with patch("trendscope.server_api.settings.api_key_required", False):
            with self._ws_client() as ws:
                pass

    def test_websocket_invalid_json(self):
        with patch("trendscope.server_api.settings.api_key_required", False):
            with self._ws_client() as ws:
                ws.send_text("not-json")
                resp = ws.receive_json()
        self.assertEqual(resp["error"], "Invalid JSON")

    def test_websocket_missing_topic_and_category(self):
        with patch("trendscope.server_api.settings.api_key_required", False):
            with self._ws_client() as ws:
                ws.send_json({})
                resp = ws.receive_json()
        self.assertEqual(resp["error"], "topic or category required")

    def test_websocket_unknown_category(self):
        with patch("trendscope.server_api.settings.api_key_required", False):
            with self._ws_client() as ws:
                ws.send_json({"category": "not_real"})
                resp = ws.receive_json()
        self.assertIn("Unknown category", resp["error"])

    def test_websocket_pipeline_success(self):
        payload = {
            "meta": {
                "query": {"topic": "crypto", "geo": "CO"},
                "total_analyzed": 5,
                "sentiment_summary": {"positive": 3, "negative": 1, "neutral": 1},
            },
            "top_trends": [
                {"title": "Bitcoin", "trend_score": 95, "source": "reddit"}
            ],
        }
        with patch("trendscope.server_api.settings.api_key_required", False):
            with patch("trendscope.server_api.run_pipeline", return_value=(payload, None)):
                with self._ws_client() as ws:
                    ws.send_json({"topic": "crypto", "top_n": 10})
                    resp = ws.receive_json()
        self.assertEqual(resp["meta"]["query"]["topic"], "crypto")
        self.assertEqual(resp["meta"]["total_analyzed"], 5)
        self.assertEqual(resp["top_trends"][0]["title"], "Bitcoin")


if __name__ == "__main__":
    unittest.main()
