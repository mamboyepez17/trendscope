# sentiment/__init__.py
from loguru import logger

from trendscope.core.query import TrendQuery
from trendscope.sentiment.base import SentimentResult


def _item_text(item: dict) -> str:
    title = (item.get("title") or "").strip()
    extra = (item.get("text") or "").strip()
    if len(title) < 40 and extra and extra != title:
        raw = f"{title} {extra}".strip()
    else:
        raw = title or extra or (item.get("keyword") or "")
    return raw[:300]


def analyze_items(items: list[dict], query: TrendQuery) -> list[dict]:
    """
    Entry point unificado de sentimiento.
    Enriquece label, score, emotions y stance.
    Si el engine falla, marca todos como neutral y continua.
    """
    engine = query.sentiment_engine
    texts = [_item_text(item) for item in items]

    logger.info(f"Analizando sentimiento: {len(texts)} items con motor '{engine}'")

    try:
        if engine in ("claude", "llm"):
            from trendscope.sentiment.claude_engine import analyze as ai_analyze

            # "claude" = Claude; "llm" = el proveedor elegido (llm_provider)
            ai_provider = "claude" if engine == "claude" else (query.llm_provider or None)
            if ai_provider is None:
                from trendscope.llm import default_provider

                ai_provider = default_provider()
            results = ai_analyze(texts, provider=ai_provider, model=query.llm_model or None,
                                 geo=query.geo)
        else:
            from trendscope.sentiment.local_engine import analyze

            results = analyze(texts, geo=query.geo)

        for i, result in enumerate(results):
            if i < len(items):
                items[i]["sentiment_label"] = result.label
                items[i]["sentiment_score"] = result.score
                items[i]["sentiment_engine"] = result.engine
                items[i]["emotions"] = result.emotions

        for item in items:
            if "sentiment_label" not in item:
                item["sentiment_label"] = "neutral"
                item["sentiment_score"] = 0.5
                item["sentiment_engine"] = engine
                item["emotions"] = {}

    except Exception as e:
        logger.error(f"Sentimiento fallo completamente: {e} -> marcando todo neutral")
        for item in items:
            item["sentiment_label"] = "neutral"
            item["sentiment_score"] = 0.5
            item["sentiment_engine"] = "failed"
            item["emotions"] = {}

    # Emociones por ítem (alegría / enojo / tristeza / miedo / neutral)
    try:
        enrich_emotions(items, geo=query.geo)
    except Exception as e:
        logger.warning(f"Emociones fallo: {e}")

    # Stance hacia el tema (siempre, aunque el engine falle)
    try:
        from trendscope.sentiment.stance import enrich_stance

        topic = query.free_topic or query.category
        enrich_stance(items, topic)
    except Exception as e:
        logger.warning(f"Stance fallo: {e}")
        for item in items:
            item.setdefault("stance", "unknown")
            item.setdefault("stance_confidence", 0.0)

    return items


# Motores cuyo sentimiento viene de un modelo real (no del léxico)
_MODEL_ENGINES = ("local_es", "local_en", "claude", "llm:")


def enrich_emotions(items: list[dict], geo: str | None = None) -> list[dict]:
    """Añade emotion, emotion_dist, polarity (−1…+1) y lang a cada ítem.

    Mezcla la salida del modelo (si existe) con el léxico del idioma del
    texto + la jerga del país (geo) + emojis.
    """
    from trendscope.sentiment.emotions import (
        NEGATIVE_EMOTIONS,
        analyze_text,
        blend,
        dominant_of,
        from_model_probas,
    )

    for item in items:
        text = _item_text(item) if not item.get("text") else (item.get("text") or "")
        lex = analyze_text(text, geo=geo)
        item["lang"] = item.get("lang") or lex.lang
        model = from_model_probas(item.get("emotions"))
        dist = blend(lex.distribution, model)
        emo_pol = dist.get("joy", 0.0) - sum(dist.get(e, 0.0) for e in NEGATIVE_EMOTIONS)

        engine = str(item.get("sentiment_engine") or "")
        label = item.get("sentiment_label", "neutral")
        if engine.startswith(_MODEL_ENGINES) and label in ("positive", "negative"):
            conf = float(item.get("sentiment_score", 0.5) or 0.5)
            model_pol = conf if label == "positive" else -conf
            polarity = 0.6 * model_pol + 0.4 * emo_pol
        elif engine.startswith(_MODEL_ENGINES):
            polarity = 0.5 * emo_pol
        else:
            polarity = emo_pol

        item["emotion_dist"] = {k: round(v, 4) for k, v in dist.items()}
        item["emotion"] = dominant_of(dist)
        item["polarity"] = round(max(-1.0, min(1.0, polarity)), 4)
    return items
