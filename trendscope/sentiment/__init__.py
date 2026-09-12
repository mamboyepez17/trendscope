# sentiment/__init__.py
from loguru import logger

from trendscope.core.query import TrendQuery
from trendscope.sentiment.base import SentimentResult


def analyze_items(items: list[dict], query: TrendQuery) -> list[dict]:
    """
    Entry point unificado de sentimiento.
    Analiza todos los items y los enriquece con label, score y emotions.
    Si el engine falla, marca todos como neutral y continua.
    """
    engine = query.sentiment_engine
    texts = []
    for item in items:
        # Preferir texto completo si el title es corto (mejor sentimiento)
        title = (item.get("title") or "").strip()
        extra = (item.get("text") or "").strip()
        if len(title) < 40 and extra and extra != title:
            raw = f"{title} {extra}".strip()
        else:
            raw = title or extra or (item.get("keyword") or "")
        texts.append(raw[:300])

    logger.info(f"Analizando sentimiento: {len(texts)} items con motor '{engine}'")

    try:
        if engine == "claude":
            from trendscope.sentiment.claude_engine import analyze
        else:
            from trendscope.sentiment.local_engine import analyze

        results = analyze(texts)

        # Enriquecer items originales
        for i, result in enumerate(results):
            if i < len(items):
                items[i]["sentiment_label"] = result.label
                items[i]["sentiment_score"] = result.score
                items[i]["sentiment_engine"] = result.engine
                items[i]["emotions"] = result.emotions

        # Items sin resultado de sentimiento -> neutral
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

    return items
