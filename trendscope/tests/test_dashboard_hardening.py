"""Dashboard hardening: local Chart.js, strict CSP, API key wiring."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_chartjs_is_local():
    static = Path("trendscope/static/chart.umd.min.js")
    assert static.exists()
    assert static.stat().st_size > 10000


def test_dashboard_does_not_use_cdn():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert "cdn.jsdelivr.net" not in html
    assert "/static/chart.umd.min.js" in html


def test_dashboard_csp_allows_self_scripts(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/dashboard")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self'" in csp
    assert "cdn.jsdelivr.net" not in csp


def test_static_chart_served(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/static/chart.umd.min.js")
    assert resp.status_code == 200
    assert len(resp.content) > 10000


def test_dashboard_html_uses_api_key_helper():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert "getApiKey" in html
    assert "X-API-Key" in html
