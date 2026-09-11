"""Regression: sentiment engines must import from trendscope.sentiment, not bare sentiment."""

from trendscope.core.query import TrendQuery
from trendscope.sentiment import analyze_items


def test_local_engine_does_not_fail_silently():
    items = [{"source": "t", "title": "Me encanta este producto increíble"}]
    query = TrendQuery(mode="free", free_topic="test", sentiment_engine="local")
    result = analyze_items(items, query)
    assert result[0]["sentiment_engine"] != "failed"
    assert result[0]["sentiment_label"] in {"positive", "negative", "neutral"}


def test_import_paths_are_package_relative():
    import inspect

    import trendscope.sentiment as pkg

    src = inspect.getsource(pkg)
    assert "from sentiment." not in src
    assert "from trendscope.sentiment." in src or "from ." in src


def test_claude_engine_module_imports():
    from trendscope.sentiment import claude_engine

    assert hasattr(claude_engine, "analyze")


def test_local_engine_module_imports():
    from trendscope.sentiment import local_engine

    assert hasattr(local_engine, "analyze")


def test_requests_is_declared_dependency():
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = " ".join(pyproject["project"]["dependencies"]).lower()
    assert "requests" in deps


def test_requirements_includes_core_runtime_deps():
    from pathlib import Path

    req = Path("requirements.txt").read_text(encoding="utf-8").lower()
    for pkg in (
        "requests",
        "pydantic-settings",
        "httpx",
        "tenacity",
        "apscheduler",
        "websockets",
        "ollama",
        "openpyxl",
    ):
        assert pkg in req, f"requirements.txt missing {pkg}"
