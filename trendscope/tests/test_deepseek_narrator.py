"""DeepSeek narrator provider."""

from unittest.mock import MagicMock, patch

from trendscope.narrator.engine import _call_deepseek, generate_summary


def test_deepseek_missing_key_message():
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", ""):
        msg = _call_deepseek("hola")
    assert "DEEPSEEK_API_KEY" in msg


def test_deepseek_default_model_is_v4_flash():
    from trendscope.settings import Settings

    s = Settings(_env_file=None)
    assert s.deepseek_model == "deepseek-v4.1-flash"
    assert s.deepseek_model != "deepseek-chat"


def test_deepseek_http_call():
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", "sk-test"):
        with patch(
            "trendscope.narrator.engine.settings.deepseek_model",
            "deepseek-v4.1-flash",
        ):
            resp = MagicMock()
            resp.raise_for_status = lambda: None
            resp.json = lambda: {
                "choices": [{"message": {"content": "Narrativa DeepSeek OK"}}]
            }
            with patch("httpx.Client") as client_cls:
                client = client_cls.return_value.__enter__.return_value
                client.post.return_value = resp
                out = _call_deepseek("analiza esto")
            _, kwargs = client.post.call_args
            assert kwargs["json"]["model"] == "deepseek-v4.1-flash"
    assert "DeepSeek OK" in out


def test_generate_summary_dispatch_deepseek():
    payload = {
        "meta": {
            "query": {"topic": "ai", "geo": "CO"},
            "total_analyzed": 1,
            "sentiment_summary": {"positive": 1, "negative": 0, "neutral": 0},
        },
        "top_trends": [],
    }
    with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
        with patch("trendscope.narrator.engine.settings.narrator_provider", "deepseek"):
            with patch(
                "trendscope.narrator.engine._call_deepseek",
                return_value="ok deepseek",
            ):
                result = generate_summary(payload, style="executive")
    assert result["provider"] == "deepseek"
    assert result["model"] == "deepseek-v4.1-flash"
    assert result["narrative"] == "ok deepseek"
