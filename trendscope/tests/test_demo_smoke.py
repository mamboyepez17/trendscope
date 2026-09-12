"""Demo payload, /smoke endpoint, and settings validation."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from trendscope.api.validation import validate_settings
from trendscope.demo.seed import build_demo_payload


def test_demo_payload_shape():
    p = build_demo_payload()
    assert p["top_trends"]
    assert p["meta"]["sentiment_summary"]["overall"] == "positive"
    assert "agent_prompt" in p


def test_demo_endpoint(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/demo")
    assert resp.status_code == 200
    assert resp.json()["top_trends"]


def test_smoke_endpoint(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        with patch(
            "trendscope.ops.run_doctor_report",
            return_value={"HN": {"status": "ok", "message": "x"}},
        ):
            resp = client.get("/smoke")
    data = resp.json()
    assert resp.status_code == 200
    assert data["offline_smoke"]["ok"] is True
    assert data["doctor_ok_sources"] == 1


def test_validate_settings_exposed_without_keys():
    with patch("trendscope.api.validation.settings.api_host", "0.0.0.0"):
        with patch("trendscope.api.validation.settings.api_key_required", False):
            warnings = validate_settings()
    assert any("API keys" in w for w in warnings)


def test_validate_settings_keys_required_empty():
    with patch("trendscope.api.validation.settings.api_key_required", True):
        with patch("trendscope.api.validation.settings.api_keys", ""):
            warnings = validate_settings()
    assert any("API_KEYS is empty" in w for w in warnings)
