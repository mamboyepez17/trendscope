"""Capa única de IA: proveedores, elección de modelo, adaptación de parámetros."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from trendscope.llm import LLMError, chat, list_models, providers_status, resolve
from trendscope.llm import client as llm_client
from trendscope.llm.providers import PROVIDERS, get


class FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text or str(payload)

    def json(self):
        return self._payload


class FakeHttpx:
    """Sustituye httpx.Client: registra peticiones y devuelve respuestas en orden."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def Client(self, timeout=None):  # noqa: N802 — imita httpx.Client
        outer = self

        class _C:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def post(self, url, headers=None, json=None):
                outer.calls.append(("POST", url, headers, dict(json)))
                return outer.responses.pop(0)

            def get(self, url, headers=None):
                outer.calls.append(("GET", url, headers, None))
                return outer.responses.pop(0)

        return _C()


def _ok(text="Hola", model="m"):
    return FakeResp(200, {"model": model, "choices": [{"message": {"content": text}, "finish_reason": "stop"}]})


def test_all_expected_providers_registered():
    for pid in ("openai", "claude", "deepseek", "opencode", "openrouter", "gemini",
                "groq", "mistral", "xai", "ollama", "custom"):
        assert pid in PROVIDERS
    assert get("chatgpt").id == "openai" and get("anthropic").id == "claude"
    assert get("grok").id == "xai" and get("nope") is None


def test_model_is_required_when_provider_has_no_default():
    with patch("trendscope.settings.settings.openai_model", ""):
        with pytest.raises(LLMError, match="Elige un modelo"):
            resolve("openai")
    p, model = resolve("openai", "gpt-x")
    assert p.id == "openai" and model == "gpt-x"


def test_missing_key_message_names_env_var():
    with patch("trendscope.settings.settings.groq_api_key", ""):
        with pytest.raises(LLMError, match="GROQ_API_KEY"):
            chat("hola", provider="groq", model="llama-x")


def test_openai_uses_max_completion_tokens_and_bearer():
    fake = FakeHttpx([_ok("Resumen", "gpt-x")])
    with patch("trendscope.settings.settings.openai_api_key", "sk-1"), patch.dict("sys.modules", {"httpx": fake}):
        r = chat("hola", provider="openai", model="gpt-x", system="sys")
    method, url, headers, body = fake.calls[0]
    assert url == "https://api.openai.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer sk-1"
    assert body["max_completion_tokens"] == 2000 and "temperature" not in body
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert (r.text, r.provider, r.model) == ("Resumen", "openai", "gpt-x")


def test_adapts_to_rejected_parameters():
    fake = FakeHttpx([
        FakeResp(400, text="Unsupported parameter: 'temperature'"),
        FakeResp(400, text="'max_tokens' is not supported, use max_completion_tokens"),
        _ok("ok"),
    ])
    with patch("trendscope.settings.settings.groq_api_key", "g"), patch.dict("sys.modules", {"httpx": fake}):
        r = chat("hola", provider="groq", model="m1")
    last = fake.calls[-1][3]
    assert r.text == "ok" and "temperature" not in last and "max_completion_tokens" in last


def test_never_returns_reasoning_content():
    resp = FakeResp(200, {"choices": [{"message": {"content": "", "reasoning_content": "secreto"}}]})
    fake = FakeHttpx([resp])
    with patch("trendscope.settings.settings.deepseek_api_key", "d"), patch.dict("sys.modules", {"httpx": fake}):
        with pytest.raises(LLMError, match="vacía"):
            chat("hola", provider="deepseek", model="deepseek-x")


def test_ollama_and_opencode_urls():
    fake = FakeHttpx([_ok(), _ok()])
    with patch("trendscope.settings.settings.opencode_api_key", "oc"), patch.dict("sys.modules", {"httpx": fake}):
        chat("x", provider="opencode", model="some-model")
        chat("x", provider="ollama", model="qwen")
    assert fake.calls[0][1] == "https://opencode.ai/zen/v1/chat/completions"
    assert fake.calls[1][1].endswith(":11434/v1/chat/completions")
    assert "Authorization" not in fake.calls[1][2]


def test_list_models_strips_gemini_prefix_and_caches():
    llm_client._MODELS_CACHE.clear()
    fake = FakeHttpx([FakeResp(200, {"data": [{"id": "models/gemini-a"}, {"id": "models/gemini-b"}]})])
    with patch("trendscope.settings.settings.gemini_api_key", "k"), patch.dict("sys.modules", {"httpx": fake}):
        assert list_models("gemini") == ["gemini-a", "gemini-b"]
        assert list_models("gemini") == ["gemini-a", "gemini-b"]  # desde caché
    assert len(fake.calls) == 1
    llm_client._MODELS_CACHE.clear()


def test_claude_returns_only_text_blocks_and_handles_refusal():
    blocks = [SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text="Análisis")]
    ok = SimpleNamespace(content=blocks, stop_reason="end_turn", model="claude-x")
    refused = SimpleNamespace(content=[], stop_reason="refusal", model="claude-x")
    fake_sdk = MagicMock()
    fake_sdk.Anthropic.return_value.messages.create.side_effect = [ok, refused]
    with patch("trendscope.settings.settings.anthropic_api_key", "a"), patch.dict("sys.modules", {"anthropic": fake_sdk}):
        r = chat("hola", provider="claude", model="claude-x")
        assert r.text == "Análisis" and r.provider == "claude"
        with pytest.raises(LLMError, match="declinó"):
            chat("hola", provider="claude", model="claude-x")


def test_providers_status_never_exposes_keys():
    with patch("trendscope.settings.settings.openai_api_key", "sk-secret"):
        status = providers_status()
    assert "sk-secret" not in str(status)
    openai = next(p for p in status if p["id"] == "openai")
    assert openai["configured"] is True and openai["key_env"] == "OPENAI_API_KEY"


def test_narrator_uses_requested_provider_and_model():
    from trendscope.narrator.engine import generate_summary

    payload = {"meta": {"query": {"topic": "x", "geo": "US"}}, "top_trends": [], "insights": {}}
    fake = MagicMock(return_value=llm_client.LLMResult("Texto", "openai", "gpt-x"))
    with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
        with patch("trendscope.llm.chat", fake):
            r = generate_summary(payload, provider="openai", model="gpt-x")
    assert r == {"narrative": "Texto", "provider": "openai", "style": "executive", "model": "gpt-x"}
    assert fake.call_args.kwargs["provider"] == "openai" and fake.call_args.kwargs["model"] == "gpt-x"


def test_narrator_reports_config_errors_cleanly():
    from trendscope.narrator.engine import generate_summary

    payload = {"meta": {"query": {}}, "top_trends": []}
    with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
        with patch("trendscope.settings.settings.mistral_api_key", ""):
            r = generate_summary(payload, provider="mistral", model="m")
    assert r["error"] and "MISTRAL_API_KEY" in r["narrative"]


def test_llm_sentiment_engine_falls_back_locally_without_key():
    from trendscope.core.query import TrendQuery
    from trendscope.sentiment import analyze_items

    items = [{"source": "reddit_comment", "text": "Qué rabia con esto 😡"}]
    q = TrendQuery(mode="free", free_topic="x", sentiment_engine="llm",
                   llm_provider="openai", llm_model="gpt-x")
    with patch("trendscope.settings.settings.openai_api_key", ""):
        out = analyze_items(items, q)
    assert out[0]["sentiment_label"] == "negative"  # motor local, no "neutral" silencioso


def test_llm_sentiment_engine_uses_chosen_provider():
    from trendscope.sentiment.claude_engine import analyze

    fake = MagicMock(return_value=llm_client.LLMResult(
        '[{"label":"positive","score":0.9,"emotions":{"joy":0.8}}]', "groq", "m"))
    with patch("trendscope.settings.settings.groq_api_key", "g"), patch("trendscope.llm.chat", fake):
        res = analyze(["Me encanta este producto"], provider="groq", model="m")
    assert res[0].label == "positive" and res[0].engine == "llm:groq"


def test_api_endpoints(isolated_app):
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        r = client.get("/llm/providers")
        assert r.status_code == 200 and any(p["id"] == "opencode" for p in r.json()["providers"])
        with patch("trendscope.llm.list_models", return_value=["m1", "m2"]):
            r = client.get("/llm/models", params={"provider": "openai"})
        assert r.json() == {"provider": "openai", "models": ["m1", "m2"]}
        r = client.get("/llm/models", params={"provider": "nope"})
        assert r.status_code == 400
        r = client.get("/trends", params={"topic": "x", "sentiment_engine": "bogus"})
        assert r.status_code == 400
