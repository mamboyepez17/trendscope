"""MCP tools parity with REST (MCPServer 2.x)."""

import asyncio
from pathlib import Path
from unittest.mock import patch

from trendscope.server_mcp import (
    analyze_trends,
    compare_topics,
    doctor,
    get_categories,
    get_latest_report,
    history_get,
    narrate_trends,
    watchlist_add,
    watchlist_list,
    watchlist_run,
)
from trendscope.watchlist.store import WatchlistStore


def test_tool_functions_exist():
    for fn in (
        analyze_trends,
        get_categories,
        get_latest_report,
        narrate_trends,
        compare_topics,
        doctor,
        watchlist_add,
        watchlist_list,
        watchlist_run,
        history_get,
    ):
        assert callable(fn)


def test_get_categories():
    result = get_categories()
    assert "categories" in result
    assert "crypto" in result["categories"]


def test_watchlist_add_list_history(tmp_path):
    store = WatchlistStore(db_path=Path(tmp_path) / "mcp.db")
    with patch("trendscope.watchlist.store.get_store", return_value=store):
        added = watchlist_add(topic="ai", interval_minutes=30)
        assert added["topic"] == "ai"
        listed = watchlist_list()
        assert any(i["topic"] == "ai" for i in listed["items"])
        hist = history_get(topic="nonexistent")
        assert hist["count"] == 0


def test_doctor_mocked():
    with patch("trendscope.core.doctor.check_all", return_value={"ok": True}):
        assert doctor() == {"ok": True}


def test_get_latest_report_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("trendscope.config.DATA_DIR", str(tmp_path))
    out = get_latest_report("missing-topic")
    assert "No hay reportes" in out


def test_analyze_trends_mocked():
    payload = {"meta": {"query": {"topic": "ai"}}, "top_trends": []}
    with patch("trendscope.server_mcp.run_pipeline", return_value=(payload, "r")):
        result = asyncio.run(analyze_trends(topic="ai", top_n=5))
    assert result["meta"]["query"]["topic"] == "ai"


def test_compare_mocked():
    p = {"meta": {}, "top_trends": []}
    with patch("trendscope.server_mcp.run_pipeline", return_value=(p, "r")):
        result = asyncio.run(compare_topics("a", "b"))
    assert "topic1" in result and "topic2" in result


def test_watchlist_run_not_found(tmp_path):
    store = WatchlistStore(db_path=Path(tmp_path) / "mcp2.db")
    with patch("trendscope.watchlist.store.get_store", return_value=store):
        result = watchlist_run(999)
    assert "error" in result


def test_mcp_server_registers_tools():
    from trendscope.server_mcp import app

    tools = asyncio.run(app.list_tools())
    names = {t.name for t in tools}
    expected = {
        "analyze_trends",
        "get_categories",
        "get_latest_report",
        "narrate_trends",
        "compare_topics",
        "doctor",
        "watchlist_add",
        "watchlist_list",
        "watchlist_run",
        "history_get",
    }
    assert expected.issubset(names)
