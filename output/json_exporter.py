# output/json_exporter.py
import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from config import DATA_DIR
from core.query import TrendQuery


def export(items: list[dict], query: TrendQuery) -> dict:
    """
    Exporta items puntuados como JSON estructurado para agentes.
    Genera archivo en data/ y retorna el payload como dict.
    """
    top = items[:query.top_n]
    now = datetime.now(timezone.utc)

    # Resumen de sentimiento
    labels = [i.get("sentiment_label", "neutral") for i in top]
    sentiment_summary = {
        "positive": labels.count("positive"),
        "negative": labels.count("negative"),
        "neutral": labels.count("neutral"),
        "engine": query.sentiment_engine,
        "overall": max(set(labels), key=labels.count) if labels else "neutral",
    }

    payload = {
        "meta": {
            "tool": "TrendScope",
            "version": "1.0.0",
            "generated_at": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "query": {
                "mode": query.mode,
                "topic": query.free_topic or query.category,
                "geo": query.geo,
                "keywords_used": query.keywords,
            },
            "total_analyzed": len(items),
            "top_n_exported": len(top),
            "sources_used": list(set(i["source"] for i in items)),
            "sentiment_summary": sentiment_summary,
        },
        "top_trends": [
            {
                "rank": idx + 1,
                "title": (i.get("title") or i.get("keyword") or i.get("text", ""))[:150],
                "source": i["source"],
                "trend_score": i["trend_score"],
                "url": i.get("url") or i.get("permalink", ""),
                "category": i.get("category") or i.get("subreddit") or "general",
                "sentiment": {
                    "label": i.get("sentiment_label", "neutral"),
                    "score": i.get("sentiment_score", 0.5),
                    "emotions": i.get("emotions", {}),
                },
                "signals": {
                    "reddit_score": i.get("score"),
                    "upvote_ratio": i.get("upvote_ratio"),
                    "comments": i.get("comments"),
                    "likes": i.get("likes"),
                    "retweets": i.get("retweets"),
                    "google_traffic": i.get("approx_traffic"),
                    "amazon_rank": i.get("rank"),
                    "price": i.get("price"),
                },
            }
            for idx, i in enumerate(top)
        ],
        "agent_prompt": (
            f"Analiza estas {len(top)} tendencias sobre "
            f"'{query.free_topic or query.category}'. "
            f"El sentimiento general es '{sentiment_summary['overall']}' "
            f"({sentiment_summary['positive']} positivos, "
            f"{sentiment_summary['negative']} negativos). "
            "Identifica los 3 insights mas accionables para tomar decisiones. "
            "Considera el contexto colombiano y el momento actual (2026). "
            "Se especifico, concreto y practico."
        ),
    }

    Path(DATA_DIR).mkdir(exist_ok=True)
    filepath = Path(DATA_DIR) / f"trends_{now.strftime('%Y-%m-%d')}_{query.topic_slug}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.success(f"JSON exportado: {filepath}")
    return payload
