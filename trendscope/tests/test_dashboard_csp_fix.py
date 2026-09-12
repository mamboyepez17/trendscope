"""Dashboard CSP fix: inline script must be external (script-src 'self')."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_dashboard_has_no_inline_script():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    # only external script tags
    assert "<script>" not in html
    assert 'src="/static/dashboard.js"' in html


def test_dashboard_js_served(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/static/dashboard.js")
    assert resp.status_code == 200
    assert b"function analyze" in resp.content
    assert b"loadCategories" in resp.content


def test_dashboard_csp_allows_self_only(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/dashboard")
    csp = resp.headers.get("Content-Security-Policy", "")
    assert "script-src 'self'" in csp
