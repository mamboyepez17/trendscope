"""Dashboard UI: dual theme, mood panel, editorial palette."""

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_dashboard_has_theme_toggle_and_light_css():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert 'id="themeToggle"' in html
    assert '[data-theme="light"]' in html
    assert "[data-theme=\"dark\"]" in html or ':root' in html


def test_dashboard_has_mood_box():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert 'id="moodBox"' in html
    assert "mood-face" in html


def test_js_theme_and_conversation():
    js = Path("trendscope/static/dashboard.js").read_text(encoding="utf-8")
    assert "function initTheme" in js
    assert "function renderMood" in js
    assert "/conversation" in js
    assert "ts_theme" in js


def test_editorial_not_neon_cyan_only():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert "#d4a054" in html or "#b45309" in html  # brass / terracotta


def test_dashboard_serves(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get("/dashboard")
    assert resp.status_code == 200
    assert "themeToggle" in resp.text
    assert "moodBox" in resp.text
