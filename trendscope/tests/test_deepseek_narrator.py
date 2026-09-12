"""DeepSeek narrator provider + model fallback."""

from unittest.mock import MagicMock, patch

from trendscope.narrator.engine import _call_deepseek, generate_summary


def test_deepseek_missing_key_message():
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", ""):
        msg = _call_deepseek("hola")
    assert "DEEPSEEK_API_KEY" in msg


def test_deepseek_default_model_is_v41_flash():
    from trendscope.settings import Settings

    s = Settings(_env_file=None)
    assert s.deepseek_model == "deepseek-v4.1-flash"


def test_deepseek_fallback_when_400():
    """Modelo inválido → intenta el siguiente de la cadena."""
    bad = MagicMock(status_code=400)
    bad.text = "invalid model"
    good = MagicMock(status_code=200)
    good.json = lambda: {
        "choices": [{"message": {"content": "ok fallback chat"}}]
    }
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", "sk-test"):
        with patch("trendscope.narrator.engine.settings.deepseek_model", "no-such-model"):
            with patch(
                "trendscope.narrator.engine._post_deepseek",
                side_effect=[bad, good],
            ):
                out = _call_deepseek("hola")
    assert "ok fallback chat" in out


def test_deepseek_ssl_retry_without_verify():
    """Si TLS falla (Kaspersky MITM), reintenta verify=False."""
    import httpx

    good = MagicMock(status_code=200)
    good.json = lambda: {
        "choices": [{"message": {"content": "ok tras TLS"}}]
    }

    def fake_post(url, headers, body):
        # primer intento verify=True → SSL error simulado vía cliente
        raise httpx.ConnectError("CERTIFICATE_VERIFY_FAILED")  # not used

    # Probar helper con side_effect de Client
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", "sk"):
        with patch("httpx.Client") as client_cls:
            # 1er client (verify=True) falla; 2º (verify=False) OK
            c1 = client_cls.return_value.__enter__.return_value
            # We call _post_deepseek which creates two clients on SSL fail
            # Simpler: patch _post_deepseek itself already covered above.
            # Here test the SSL branch of _post_deepseek:
            from trendscope.narrator import engine as eng

            calls = {"n": 0}

            class FakeClient:
                def __init__(self, *a, **k):
                    calls["n"] += 1
                    self.verify = k.get("verify", True)

                def __enter__(self):
                    return self

                def __exit__(self, *a):
                    return False

                def post(self, url, headers=None, json=None):
                    if self.verify:
                        raise httpx.HTTPError(
                            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed"
                        )
                    return good

            with patch("httpx.Client", FakeClient):
                resp = eng._post_deepseek("https://api.deepseek.com/chat/completions", {}, {})
    assert resp is good
    assert calls["n"] == 2


def test_deepseek_reasoner_content_fallback():
    """Si content vacío, usa reasoning_content."""
    resp = MagicMock(status_code=200)
    resp.json = lambda: {
        "choices": [
            {"message": {"content": "", "reasoning_content": "pensando... resultado"}}
        ]
    }
    with patch("trendscope.narrator.engine.settings.deepseek_api_key", "sk-test"):
        with patch("trendscope.narrator.engine.settings.deepseek_model", "deepseek-v4-pro"):
            with patch("httpx.Client") as client_cls:
                client = client_cls.return_value.__enter__.return_value
                client.post.return_value = resp
                out = _call_deepseek("hola")
    assert "resultado" in out


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
