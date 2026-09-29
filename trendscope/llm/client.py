"""Cliente único de IA: `chat()` y `list_models()` para cualquier proveedor.

    from trendscope.llm import chat
    r = chat("Resume esto…", provider="openai", model="gpt-…", system="Eres…")
    r.text, r.provider, r.model
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from loguru import logger

from trendscope.llm.providers import PROVIDERS, Provider, chat_base_url, get
from trendscope.settings import settings


class LLMError(RuntimeError):
    """Error de configuración o de la API del proveedor (mensaje apto para el usuario)."""


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    truncated: bool = False


def default_provider() -> str:
    """Proveedor por defecto: LLM_PROVIDER, o el NARRATOR_PROVIDER de siempre."""
    for candidate in (getattr(settings, "llm_provider", ""), getattr(settings, "narrator_provider", "")):
        p = get(candidate)
        if p:
            return p.id
    return "openrouter"


def resolve(provider: str | None = None, model: str | None = None) -> tuple[Provider, str]:
    p = get(provider or default_provider())
    if p is None:
        raise LLMError(
            f"Proveedor de IA '{provider}' no soportado. Opciones: {', '.join(PROVIDERS)}"
        )
    chosen = (model or "").strip() or p.default_model
    if not chosen:
        env = (p.model_setting or "").upper()
        raise LLMError(
            f"Elige un modelo para {p.label}: pásalo como llm_model o configura {env} en .env. "
            f"Lista de modelos: GET /llm/models?provider={p.id}"
        )
    return p, chosen


def _require_key(p: Provider) -> None:
    if p.key_setting and not p.api_key and p.id != "custom":
        env = p.key_setting.upper()
        hint = f" ({p.keys_url})" if p.keys_url else ""
        raise LLMError(f"Falta {env} en .env para usar {p.label}{hint}.")
    if p.id == "custom" and not p.url:
        raise LLMError("Configura LLM_BASE_URL (y LLM_API_KEY si hace falta) para el proveedor custom.")


# ── OpenAI-compatible ─────────────────────────────────────────────────────────

def _headers(p: Provider) -> dict:
    h = {"Content-Type": "application/json", **p.extra_headers}
    if p.api_key:
        h["Authorization"] = f"Bearer {p.api_key}"
    return h


def _openai_chat(p: Provider, model: str, system: str | None, prompt: str,
                 max_tokens: int, temperature: float | None, timeout: float) -> LLMResult:
    import httpx

    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    body: dict = {"model": model, "messages": messages, "stream": False}
    # OpenAI (modelos recientes) usa max_completion_tokens y solo temperatura por defecto
    if p.id == "openai":
        body["max_completion_tokens"] = max_tokens
    else:
        body["max_tokens"] = max_tokens
        if temperature is not None:
            body["temperature"] = temperature

    url = f"{chat_base_url(p)}/chat/completions"
    for attempt in range(3):
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(url, headers=_headers(p), json=body)
        if resp.status_code == 400 and attempt < 2:
            err = resp.text.lower()
            # Adaptarse a lo que el modelo no acepte y reintentar una vez por causa
            if "temperature" in err and "temperature" in body:
                body.pop("temperature")
                continue
            if "max_tokens" in err and "max_tokens" in body:
                body["max_completion_tokens"] = body.pop("max_tokens")
                continue
            if "max_completion_tokens" in err and "max_completion_tokens" in body:
                body["max_tokens"] = body.pop("max_completion_tokens")
                continue
        if resp.status_code >= 400:
            raise LLMError(f"{p.label} respondió HTTP {resp.status_code}: {resp.text[:240]}")
        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        # Solo el contenido visible: nunca reasoning_content / pensamiento
        text = ((choice.get("message") or {}).get("content") or "").strip()
        if not text:
            raise LLMError(f"{p.label} ({model}) devolvió una respuesta vacía")
        return LLMResult(text, p.id, data.get("model") or model,
                         truncated=choice.get("finish_reason") == "length")
    raise LLMError(f"{p.label}: no se pudo adaptar la petición al modelo {model}")


def _openai_models(p: Provider, timeout: float) -> list[str]:
    import httpx

    with httpx.Client(timeout=timeout) as client:
        resp = client.get(f"{chat_base_url(p)}/models", headers=_headers(p))
    if resp.status_code >= 400:
        raise LLMError(f"{p.label} respondió HTTP {resp.status_code} al listar modelos")
    data = resp.json()
    items = data.get("data") if isinstance(data, dict) else data
    ids = []
    for m in items or []:
        mid = m.get("id") if isinstance(m, dict) else str(m)
        if mid:
            ids.append(mid.removeprefix("models/"))  # Gemini antepone "models/"
    return sorted(set(ids))


# ── Anthropic (Claude) ───────────────────────────────────────────────────────

# Modelos que admiten el respaldo del lado del servidor si el modelo rechaza
_FALLBACK_MODELS = ("claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5")


def _anthropic_chat(p: Provider, model: str, system: str | None, prompt: str,
                    max_tokens: int, timeout: float) -> LLMResult:
    try:
        import anthropic
    except ImportError as e:
        raise LLMError("Instala el SDK de Anthropic: pip install anthropic") from e

    client = anthropic.Anthropic(api_key=p.api_key, timeout=timeout)
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    try:
        if model.startswith(_FALLBACK_MODELS):
            try:
                resp = client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"],
                    extra_body={"fallbacks": "default"},
                    **kwargs,
                )
            except anthropic.BadRequestError:
                resp = client.messages.create(**kwargs)
        else:
            resp = client.messages.create(**kwargs)
    except anthropic.AuthenticationError as e:
        raise LLMError("ANTHROPIC_API_KEY inválida") from e
    except anthropic.NotFoundError as e:
        raise LLMError(f"Modelo de Claude no encontrado: {model}") from e
    except anthropic.RateLimitError as e:
        raise LLMError("Claude: límite de uso alcanzado, reintenta en un momento") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"Claude respondió HTTP {e.status_code}: {str(e)[:200]}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("No se pudo conectar con la API de Claude") from e

    if resp.stop_reason == "refusal":
        raise LLMError("Claude declinó responder esta petición")
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    if not text:
        raise LLMError(f"Claude ({model}) devolvió una respuesta vacía")
    return LLMResult(text, p.id, getattr(resp, "model", model) or model,
                     truncated=resp.stop_reason == "max_tokens")


def _anthropic_models(p: Provider) -> list[str]:
    try:
        import anthropic
    except ImportError as e:
        raise LLMError("Instala el SDK de Anthropic: pip install anthropic") from e
    client = anthropic.Anthropic(api_key=p.api_key)
    try:
        return sorted(m.id for m in client.models.list())
    except anthropic.APIError as e:
        raise LLMError(f"Claude: no se pudieron listar los modelos ({e})") from e


# ── API pública ──────────────────────────────────────────────────────────────

def chat(prompt: str, provider: str | None = None, model: str | None = None,
         system: str | None = None, max_tokens: int = 2000,
         temperature: float | None = 0.7, timeout: float = 120.0) -> LLMResult:
    """Una respuesta de texto del proveedor/modelo elegido. Lanza LLMError."""
    p, chosen = resolve(provider, model)
    _require_key(p)
    try:
        if p.kind == "anthropic":
            return _anthropic_chat(p, chosen, system, prompt, max_tokens, timeout)
        return _openai_chat(p, chosen, system, prompt, max_tokens, temperature, timeout)
    except LLMError:
        raise
    except Exception as e:  # red, JSON, etc.
        logger.warning(f"LLM {p.id}/{chosen}: {e}")
        raise LLMError(f"{p.label}: {e}") from e


_MODELS_CACHE: dict[str, tuple[float, list[str]]] = {}
_MODELS_TTL = 600.0


def list_models(provider: str, timeout: float = 20.0) -> list[str]:
    """Modelos disponibles en el proveedor (cacheado 10 min)."""
    p = get(provider)
    if p is None:
        raise LLMError(f"Proveedor '{provider}' no soportado. Opciones: {', '.join(PROVIDERS)}")
    hit = _MODELS_CACHE.get(p.id)
    if hit and time.time() - hit[0] < _MODELS_TTL:
        return hit[1]
    if p.id != "openrouter":  # OpenRouter lista modelos sin key
        _require_key(p)
    models = _anthropic_models(p) if p.kind == "anthropic" else _openai_models(p, timeout)
    _MODELS_CACHE[p.id] = (time.time(), models)
    return models


def providers_status() -> list[dict]:
    """Proveedores con su estado (sin exponer claves)."""
    current = default_provider()
    return [
        {
            "id": p.id,
            "label": p.label,
            "configured": p.configured,
            "default": p.id == current,
            "default_model": p.default_model,
            "needs_key": bool(p.key_setting) and p.id != "custom",
            "key_env": (p.key_setting or "").upper(),
            "model_env": (p.model_setting or "").upper(),
            "keys_url": p.keys_url,
        }
        for p in PROVIDERS.values()
    ]
