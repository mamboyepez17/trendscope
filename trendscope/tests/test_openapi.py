"""OpenAPI completeness checks."""

from unittest.mock import patch

from fastapi.testclient import TestClient


def test_openapi_includes_core_paths(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for p in ("/trends", "/watchlist", "/jobs/{job_id}", "/jobs/{job_id}/events", "/forecast", "/health", "/metrics"):
        assert p in paths, p


def test_openapi_has_tags(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        spec = client.get("/openapi.json").json()
    tags = {t["name"] for t in spec.get("tags", [])}
    assert "trends" in tags
    assert "watchlist" in tags
    assert "jobs" in tags
    assert "ops" in tags
