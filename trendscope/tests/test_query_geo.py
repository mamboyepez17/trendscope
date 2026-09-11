"""Geo/year dynamic keywords and config consistency."""

from datetime import datetime

from trendscope.core.query import TrendQuery
from trendscope.settings import Settings


def test_free_topic_uses_geo_not_hardcoded_colombia():
    q = TrendQuery(mode="free", free_topic="cafe", geo="MX")
    kws = q.keywords
    assert any("MX" in k for k in kws)
    assert not any("Colombia" in k for k in kws)


def test_free_topic_uses_current_year():
    q = TrendQuery(mode="free", free_topic="ai", geo="CO")
    year = str(datetime.now().year)
    assert any(year in k for k in q.keywords)


def test_ollama_default_false():
    s = Settings(_env_file=None)
    assert s.ollama_enabled is False


def test_api_host_default_localhost():
    s = Settings(_env_file=None)
    assert s.api_host == "127.0.0.1"


def test_env_example_has_data_dir():
    from pathlib import Path

    text = Path(".env.example").read_text(encoding="utf-8")
    assert "DATA_DIR=" in text
    assert "TRUST_PROXY_HEADERS=" in text
    assert "OLLAMA_ENABLED=false" in text


def test_cache_ttl_export_name():
    from trendscope import config

    assert hasattr(config, "CACHE_TTL_SECONDS")
