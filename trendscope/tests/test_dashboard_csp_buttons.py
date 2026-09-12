"""Dashboard: no inline onclick (CSP) + narrative box."""

from pathlib import Path


def test_no_inline_onclick_in_dashboard_js():
    js = Path("trendscope/static/dashboard.js").read_text(encoding="utf-8")
    assert "onclick=" not in js
    assert "data-action" in js
    assert "deleteWatchItem" in js


def test_dashboard_has_narrative_box():
    html = Path("trendscope/dashboard.html").read_text(encoding="utf-8")
    assert 'id="narrativeBox"' in html


def test_load_narrative_defined():
    js = Path("trendscope/static/dashboard.js").read_text(encoding="utf-8")
    assert "function loadNarrative" in js
    assert "/narrate" in js
