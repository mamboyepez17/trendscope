# sentiment/claude_engine.py
# Claude (Haiku por defecto) — análisis premium de sentimiento + emociones.
# Si falta la API key o falla un lote, ese lote cae al motor local: nunca se
# reporta "100% neutral" por un error silencioso.
import json
import re

from loguru import logger

from trendscope.config import ANTHROPIC_API_KEY
from trendscope.sentiment.base import SentimentResult

_VALID_LABELS = {"positive", "negative", "neutral"}
_EMOTION_KEYS = ("joy", "anger", "sadness", "fear")

_PROMPT = (
    "Classify each text (Spanish or English, often Latin-American slang and emojis) "
    "by how the AUTHOR feels.\n"
    "Return ONLY a JSON array with exactly {n} objects, in the same order as the input, "
    "no markdown. Each object:\n"
    '{{"label":"positive|negative|neutral","score":0.5-1.0,'
    '"emotions":{{"joy":0-1,"anger":0-1,"sadness":0-1,"fear":0-1}}}}\n'
    "score = confidence in the label. Emotions are independent intensities; use 0 "
    "when absent. Sarcasm counts as its real intent.\n\n"
    "Texts:\n{texts}"
)


def _model() -> str:
    try:
        from trendscope.settings import settings

        return getattr(settings, "claude_sentiment_model", "") or "claude-haiku-4-5"
    except Exception:
        return "claude-haiku-4-5"


def _local(texts: list[str]) -> list[SentimentResult]:
    from trendscope.sentiment.local_engine import analyze as local_analyze

    return local_analyze(texts)


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


def _to_result(text: str, obj: dict) -> SentimentResult | None:
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
                           engine="claude", emotions=emotions)


def analyze(texts: list[str], batch_size: int = 20) -> list[SentimentResult]:
    """Sentimiento + emociones con Claude; fallback local por lote."""
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY no configurada → usando motor local")
        return _local(texts)

    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic no instalado → usando motor local")
        return _local(texts)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    model = _model()
    results: list[SentimentResult] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        idx = [j for j, t in enumerate(batch) if t and len(t.strip()) > 3]
        out: list[SentimentResult | None] = [None] * len(batch)

        if idx:
            prompt_texts = [batch[j][:400] for j in idx]
            parsed = None
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=4000,
                    messages=[{"role": "user", "content": _PROMPT.format(
                        n=len(prompt_texts),
                        texts=json.dumps(prompt_texts, ensure_ascii=False),
                    )}],
                )
                text_out = "".join(b.text for b in response.content if b.type == "text")
                parsed = _parse(text_out, len(prompt_texts))
                if parsed is None:
                    logger.warning("Claude: respuesta no parseable → lote con motor local")
            except anthropic.RateLimitError:
                logger.warning("Claude: rate limit → lote con motor local")
            except anthropic.APIStatusError as e:
                logger.warning(f"Claude: error API {e.status_code} → lote con motor local")
            except anthropic.APIConnectionError:
                logger.warning("Claude: sin conexión → lote con motor local")

            if parsed is not None:
                for j, obj in zip(idx, parsed):
                    out[j] = _to_result(batch[j], obj)

        # Lo que no se pudo con Claude (errores o ítems inválidos) → local
        missing = [j for j, r in enumerate(out) if r is None]
        if missing:
            local = _local([batch[j] for j in missing])
            for j, r in zip(missing, local):
                out[j] = r
        results.extend(out)  # type: ignore[arg-type]

    logger.success(f"Claude sentiment: {len(results)} textos analizados ({model})")
    return results
