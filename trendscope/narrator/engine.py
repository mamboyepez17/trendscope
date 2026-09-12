"""Motor de narrativas para TrendScope."""

import json
from typing import Literal

from loguru import logger

from trendscope.settings import settings


NARRATIVE_STYLES = {
    "executive": (
        "Eres un analista senior de tendencias. Escribe 3 p\u00e1rrafos ejecutivos: "
        "resumen del panorama, oportunidades clave y recomendaci\u00f3n accionable."
    ),
    "creative": (
        "Eres un copywriter creativo. Crea un texto atractivo, viral y basado en datos "
        "que una marca pueda usar como post o idea de contenido."
    ),
    "technical": (
        "Eres un ingeniero de datos. S\u00e9 t\u00e9cnico, preciso y estructura el an\u00e1lisis "
        "por fuentes, vol\u00famenes y sentimiento."
    ),
    "alert": (
        "Eres un analista de riesgo. Destaca alertas, cambios bruscos de sentimiento "
        "y riesgos de reputaci\u00f3n o oportunidad."
    ),
}


def _build_context(payload: dict) -> str:
    top = payload.get("top_trends", [])[:10]
    meta = payload.get("meta", {})
    insights = payload.get("insights", {})
    sentiment = meta.get("sentiment_summary", {})

    context = {
        "topic": meta.get("query", {}).get("topic"),
        "geo": meta.get("query", {}).get("geo"),
        "total_signals": meta.get("total_analyzed"),
        "sentiment": {
            "positive": sentiment.get("positive", 0),
            "negative": sentiment.get("negative", 0),
            "neutral": sentiment.get("neutral", 0),
            "compound": sentiment.get("compound"),
        },
        "top_trends": [
            {
                "title": t.get("title"),
                "score": t.get("trend_score"),
                "source": t.get("source"),
                "sentiment": t.get("sentiment"),
            }
            for t in top
        ],
        "insights": {
            "executive_summary": insights.get("executive_summary"),
            "recommendations": insights.get("recommendations"),
        },
    }
    return json.dumps(context, ensure_ascii=False, indent=2)


def _build_prompt(payload: dict, style: str) -> str:
    system = NARRATIVE_STYLES.get(style, NARRATIVE_STYLES["executive"])
    context = _build_context(payload)
    return (
        f"{system}\n\n"
        "Analiza los siguientes datos de tendencias y genera un resumen en espa\u00f1ol. "
        "S\u00e9 concreto, accionable y basado estrictamente en los datos proporcionados.\n\n"
        f"{context}"
    )


def _call_openrouter(prompt: str) -> str:
    try:
        import httpx
    except ImportError:
        return "Error: httpx no instalado."

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_site_url,
        "X-Title": settings.openrouter_site_name,
    }

    body = {
        "model": settings.openrouter_model,
        "messages": [
            {"role": "system", "content": "Eres un experto en an\u00e1lisis de tendencias."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 800,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"OpenRouter error: {e}")
        return f"Error al contactar OpenRouter: {e}"


def _call_claude(prompt: str) -> str:
    try:
        import anthropic
    except ImportError:
        return "Error: anthropic no instalado."

    if not settings.anthropic_api_key:
        return "Error: ANTHROPIC_API_KEY no configurada."

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        resp = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=800,
            system="Eres un experto en an\u00e1lisis de tendencias.",
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        logger.error(f"Claude error: {e}")
        return f"Error al contactar Claude: {e}"


def _call_ollama(prompt: str) -> str:
    try:
        import ollama
    except ImportError:
        return "Error: ollama no instalado."

    try:
        client = ollama.Client(host=settings.ollama_host)
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": "Eres un experto en an\u00e1lisis de tendencias."},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.7, "num_predict": 800},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error al contactar Ollama: {e}"


_DEEPSEEK_MODEL_FALLBACKS = (
    "deepseek-v4.1-flash",
    "deepseek-flash",
    "deepseek-v4-pro",
    "deepseek-chat",
)


def _post_deepseek(url: str, headers: dict, body: dict):
    """POST con fallback TLS si hay MITM (Kaspersky, corporate proxy)."""
    import httpx

    try:
        with httpx.Client(timeout=90.0, verify=True) as client:
            return client.post(url, headers=headers, json=body)
    except httpx.HTTPError as e:
        msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in msg or "SSL" in msg.upper():
            logger.warning(
                "DeepSeek TLS falló (¿Kaspersky / proxy MITM?). "
                "Reintentando sin verificar certificado. "
                "Mejor: excluye api.deepseek.com en el antivirus."
            )
            with httpx.Client(timeout=90.0, verify=False) as client:
                return client.post(url, headers=headers, json=body)
        raise


def _call_deepseek(prompt: str) -> str:
    """DeepSeek Chat — API oficial compatible con OpenAI."""
    try:
        import httpx  # noqa: F401
    except ImportError:
        return "Error: httpx no instalado."

    if not settings.deepseek_api_key:
        return (
            "DeepSeek API key no configurada. "
            "Añade DEEPSEEK_API_KEY a .env (https://platform.deepseek.com)."
        )

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    models: list[str] = []
    for m in (settings.deepseek_model, *_DEEPSEEK_MODEL_FALLBACKS):
        if m and m not in models:
            models.append(m)

    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    last_err = ""
    for model in models:
        body = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "Eres un experto en análisis de tendencias.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 800,
        }
        try:
            resp = _post_deepseek(url, headers, body)
            if resp.status_code >= 400:
                last_err = f"{model}: HTTP {resp.status_code} {resp.text[:200]}"
                logger.warning(f"DeepSeek {last_err}")
                continue
            data = resp.json()
            msg = (data.get("choices") or [{}])[0].get("message") or {}
            content = (msg.get("content") or "").strip()
            if not content:
                content = (msg.get("reasoning_content") or "").strip()
            if content:
                return content
            last_err = f"{model}: empty completion"
        except Exception as e:
            last_err = f"{model}: {e}"
            logger.warning(f"DeepSeek {last_err}")

    logger.error(f"DeepSeek agotó modelos: {last_err}")
    hint = ""
    if "CERTIFICATE" in last_err or "SSL" in last_err.upper():
        hint = (
            " | TLS interceptado (Kaspersky/proxy). "
            "Excluye api.deepseek.com en el antivirus o desactiva "
            "el análisis de conexiones cifradas."
        )
    return f"Error DeepSeek: {last_err}{hint}"


def _statistical_summary(payload: dict) -> str:
    """Fallback 100% local cuando no hay proveedor configurado."""
    meta = payload.get("meta", {})
    top = payload.get("top_trends", [])[:5]
    sentiment = meta.get("sentiment_summary", {})
    lines = [
        "## Resumen estad\u00edstico",
        "",
        f"**Tema:** {meta.get('query', {}).get('topic', 'N/A')}",
        f"**Regi\u00f3n:** {meta.get('query', {}).get('geo', 'N/A')}",
        f"**Se\u00f1ales analizadas:** {meta.get('total_analyzed', 0)}",
        "",
        "**Sentimiento:**",
        f"- Positivo: {sentiment.get('positive', 0)}",
        f"- Negativo: {sentiment.get('negative', 0)}",
        f"- Neutral: {sentiment.get('neutral', 0)}",
        "",
        "**Top tendencias:**",
    ]
    for i, t in enumerate(top, 1):
        lines.append(
            f"{i}. {t.get('title', 'N/A')} (score: {t.get('trend_score', 0)}, "
            f"fuente: {t.get('source', 'N/A')})"
        )
    lines.append("")
    lines.append(
        "*Para narrativas generadas por IA, configura OPENROUTER_API_KEY, "
        "ANTHROPIC_API_KEY o Ollama.*"
    )
    return "\n".join(lines)


def generate_summary(
    payload: dict,
    style: Literal["executive", "creative", "technical", "alert"] = "executive",
) -> dict:
    """Genera una narrativa usando el proveedor configurado."""

    if not settings.narrative_enabled:
        return {"narrative": "Narrador deshabilitado.", "provider": "none", "style": style}

    provider = settings.narrator_provider
    prompt = _build_prompt(payload, style)

    if provider == "openrouter":
        if not settings.openrouter_api_key:
            return {
                "narrative": "OpenRouter API key no configurada. "
                "Ve a https://openrouter.ai/keys y a\u00f1ade OPENROUTER_API_KEY a .env",
                "provider": "openrouter",
                "style": style,
                "error": True,
            }
        narrative = _call_openrouter(prompt)
    elif provider == "deepseek":
        narrative = _call_deepseek(prompt)
    elif provider == "claude":
        narrative = _call_claude(prompt)
    elif provider == "ollama":
        narrative = _call_ollama(prompt)
    elif provider == "none":
        narrative = _statistical_summary(payload)
    else:
        narrative = (
            f"Proveedor '{provider}' no soportado. "
            "Usa openrouter, deepseek, claude, ollama o none."
        )

    return {
        "narrative": narrative,
        "provider": provider,
        "style": style,
        "model": (
            settings.openrouter_model
            if provider == "openrouter"
            else settings.deepseek_model
            if provider == "deepseek"
            else settings.ollama_model
            if provider == "ollama"
            else "claude-3-haiku"
            if provider == "claude"
            else "local"
        ),
    }
