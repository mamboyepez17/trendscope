# sentiment/__init__.py
from loguru import logger

from core.query import TrendQuery
from sentiment.base import SentimentResult


def analyze_items(items: list[dict], query: TrendQuery) -> list[dict]:
    """
    Entry point unificado de sentimiento.
    Analiza todos los items y los enriquece con label, score y emotions.
    Si el engine falla, marca todos como neutral y continua.
    """
    engine = query.sentiment_engine
    texts = [
        (item.get("title") or item.get("keyword") or item.get("text") or "")[:300]
        for item in items
    ]

    logger.info(f"Analizando sentimiento: {len(texts)} items con motor '{engine}'")

    try:
        if engine == "claude":
            from sentiment.claude_engine import analyze
        else:
            from sentiment.local_engine import analyze

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
