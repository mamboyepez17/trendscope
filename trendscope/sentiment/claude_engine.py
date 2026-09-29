# sentiment/claude_engine.py
# Motor premium de sentimiento + emociones con CUALQUIER proveedor de IA
# (Claude por defecto; también OpenAI, DeepSeek, OpenCode, Gemini, Groq…).
# Si falta la API key o falla un lote, ese lote cae al motor local: nunca se
# reporta "100% neutral" por un error silencioso.
import json
import re

from loguru import logger

from trendscope.sentiment.base import SentimentResult

_VALID_LABELS = {"positive", "negative", "neutral"}
_EMOTION_KEYS = ("joy", "anger", "sadness", "fear")

_PROMPT = (
    "Classify each text (any language, often with slang and emojis) "
    "by how the AUTHOR feels.\n"
    "Return ONLY a JSON array with exactly {n} objects, in the same order as the input, "
    "no markdown. Each object:\n"
    '{{"label":"positive|negative|neutral","score":0.5-1.0,'
    '"emotions":{{"joy":0-1,"anger":0-1,"sadness":0-1,"fear":0-1}}}}\n'
    "score = confidence in the label. Emotions are independent intensities; use 0 "
    "when absent. Sarcasm counts as its real intent.\n\n"
    "Texts:\n{texts}"
)


def _default_model(provider: str) -> str | None:
    """Claude conserva CLAUDE_SENTIMENT_MODEL (Haiku, barato); el resto, su modelo de .env."""
    if provider == "claude":
        from trendscope.settings import settings

        return getattr(settings, "claude_sentiment_model", "") or "claude-haiku-4-5"
    return None


def _local(texts: list[str], geo: str | None = None) -> list[SentimentResult]:
    from trendscope.sentiment.local_engine import analyze as local_analyze

    return local_analyze(texts, geo=geo)


def _parse(raw: str, expected: int) -> list[dict] | None:
    raw = (raw or "").strip()
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list) or len(parsed) != expected:
        return None
    return parsed


def _to_result(text: str, obj: dict, engine: str = "claude") -> SentimentResult | None:
    if not isinstance(obj, dict):
        return None
    label = str(obj.get("label", "")).lower().strip()
    if label not in _VALID_LABELS:
        return None
    try:
        score = max(0.5, min(1.0, float(obj.get("score", 0.7))))
    except (TypeError, ValueError):
        score = 0.7
    emotions = {}
    for k in _EMOTION_KEYS:
        try:
            emotions[k] = max(0.0, min(1.0, float((obj.get("emotions") or {}).get(k, 0))))
        except (TypeError, ValueError):
            emotions[k] = 0.0
    # Emoción "residual" neutral para que la mezcla con el léxico sea coherente
    emotions["others"] = max(0.0, 1.0 - max(emotions.values(), default=0.0))
    return SentimentResult(text=text[:100], label=label, score=score,
                           engine=engine, emotions=emotions)


def analyze(
    texts: list[str],
    batch_size: int = 20,
    provider: str | None = None,
    model: str | None = None,
    geo: str | None = None,
) -> list[SentimentResult]:
    """Sentimiento + emociones con el proveedor/modelo elegido; fallback local por lote."""
    from trendscope.llm import LLMError
    from trendscope.llm import chat as llm_chat
    from trendscope.llm.client import _require_key, resolve

    provider = provider or "claude"
    try:
        p, chosen = resolve(provider, model or _default_model(provider))
        _require_key(p)
    except LLMError as e:
        logger.warning(f"Sentimiento IA no disponible ({e}) → usando motor local")
        return _local(texts, geo)

    engine_tag = p.id if p.id == "claude" else f"llm:{p.id}"
    results: list[SentimentResult] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        idx = [j for j, t in enumerate(batch) if t and len(t.strip()) > 3]
        out: list[SentimentResult | None] = [None] * len(batch)

        if idx:
            prompt_texts = [batch[j][:400] for j in idx]
            parsed = None
            try:
                resp = llm_chat(
                    _PROMPT.format(n=len(prompt_texts),
                                   texts=json.dumps(prompt_texts, ensure_ascii=False)),
                    provider=p.id, model=chosen, max_tokens=4000, temperature=0,
                )
                parsed = _parse(resp.text, len(prompt_texts))
                if parsed is None:
                    logger.warning(f"{p.label}: respuesta no parseable → lote con motor local")
            except LLMError as e:
                logger.warning(f"{p.label}: {e} → lote con motor local")

            if parsed is not None:
                for j, obj in zip(idx, parsed):
                    out[j] = _to_result(batch[j], obj, engine_tag)

        # Lo que no se pudo con la IA (errores o ítems inválidos) → local
        missing = [j for j, r in enumerate(out) if r is None]
        if missing:
            local = _local([batch[j] for j in missing], geo)
            for j, r in zip(missing, local):
                out[j] = r
        results.extend(out)  # type: ignore[arg-type]

    logger.success(f"Sentimiento IA: {len(results)} textos ({p.id}/{chosen})")
    return results
