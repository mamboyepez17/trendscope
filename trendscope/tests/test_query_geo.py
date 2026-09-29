"""Geo/year dynamic keywords and config consistency."""

from datetime import datetime

from trendscope.core.query import TrendQuery
from trendscope.settings import Settings


def test_free_topic_keywords_have_no_geo_or_year_noise():
    q = TrendQuery(mode="free", free_topic="cafe", geo="MX")
    assert q.keywords == ["cafe"]
    assert not any(str(datetime.now().year) in k for k in q.keywords)


def test_google_news_uses_query_geo_edition():
    from unittest.mock import MagicMock, patch

    from trendscope.scrapers import google_news

    session = MagicMock()
    session.get.return_value = MagicMock(text="<rss><channel></channel></rss>")
    with patch("trendscope.scrapers.google_news.get_session", return_value=session):
        google_news.run(TrendQuery(mode="free", free_topic="cafe", geo="MX"))
    url = session.get.call_args_list[0].args[0]
    assert "gl=MX" in url and "ceid=MX" in url


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
