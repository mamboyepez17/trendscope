# analyzer/insights.py
"""
Motor de análisis de TrendScope.
Toma los datos recolectados + scoring + sentimiento y genera insights
en lenguaje natural, sin necesidad de APIs externas.

Genera:
1. Resumen ejecutivo
2. Insights accionables (oportunidades, alertas)
3. Correlaciones entre fuentes
4. Detección de temas emergentes vs establecidos
5. Recomendaciones
"""
from collections import Counter
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from core.query import TrendQuery


def _source_breakdown(items: list[dict]) -> dict:
    """Cuenta items por fuente y calcula score promedio por fuente."""
    stats = {}
    for item in items:
        src = item.get("source", "unknown")
        if src not in stats:
            stats[src] = {"count": 0, "total_score": 0, "sentiments": []}
        stats[src]["count"] += 1
        stats[src]["total_score"] += item.get("trend_score", 0)
        stats[src]["sentiments"].append(item.get("sentiment_label", "neutral"))
    for src in stats:
        stats[src]["avg_score"] = round(stats[src]["total_score"] / max(1, stats[src]["count"]), 1)
        sent_counts = Counter(stats[src]["sentiments"])
        stats[src]["dominant_sentiment"] = sent_counts.most_common(1)[0][0] if sent_counts else "neutral"
    return stats


def _detect_emerging_vs_established(items: list[dict]) -> dict:
    """
    Clasifica tendencias en emergentes vs establecidas.
    Emergente: score alto pero pocas fuentes (<2) = está empezando a sonar.
    Establecido: score alto + muchas fuentes (>=2) = ya es mainstream.
    Fugaz: score medio + 1 fuente = puede ser ruido temporal.
    """
    emerging = []
    established = []
    fading = []

    for item in items:
        score = item.get("trend_score", 0)
        # Contar en cuántas fuentes aparece algo similar
        title = (item.get("title") or item.get("keyword") or item.get("text") or "").lower()
        source_count = sum(
            1 for other in items
            if other.get("source") != item.get("source")
            and _text_overlap(title, (other.get("title") or other.get("keyword") or other.get("text") or "").lower())
        )
        total_sources = 1 + source_count

        if score >= 65 and total_sources <= 1:
            emerging.append({**item, "_total_sources": total_sources})
        elif score >= 65 and total_sources >= 2:
            established.append({**item, "_total_sources": total_sources})
        elif score < 40:
            fading.append({**item, "_total_sources": total_sources})

    return {
        "emerging": emerging[:5],
        "established": established[:5],
        "fading": fading[:3],
    }


def _text_overlap(a: str, b: str) -> bool:
    """Check rápido si dos textos comparten palabras significativas."""
    if not a or not b or len(a) < 5 or len(b) < 5:
        return False
    a_words = set(a.split())
    b_words = set(b.split())
    overlap = len(a_words & b_words)
    return overlap >= 2


def _generate_summary(items: list[dict], query: TrendQuery, sentiment_summary: dict) -> str:
    """Genera resumen ejecutivo en lenguaje natural."""
    topic = query.free_topic or query.category or "el tema"
    total = len(items)
    top = items[0] if items else None
    ss = sentiment_summary

    parts = []
    parts.append(f"Análisis de '{topic}' — {total} señales recolectadas.")

    if top:
        top_title = (top.get("title") or top.get("keyword") or "N/A")[:80]
        parts.append(f"La tendencia más destacada es \"{top_title}\" con score {top.get('trend_score', 0)}/100.")

    # Sentimiento
    overall = ss.get("overall", "neutral")
    pos = ss.get("positive", 0)
    neg = ss.get("negative", 0)
    neu = ss.get("neutral", 0)

    if pos > neg and pos > neu:
        parts.append(f"El sentimiento general es POSITIVO ({pos} positivos vs {neg} negativos) — la conversación favorece el tema.")
    elif neg > pos and neg > neu:
        parts.append(f"El sentimiento general es NEGATIVO ({neg} negativos vs {pos} positivos) — hay preocupación o rechazo.")
    else:
        parts.append(f"El sentimiento general es NEUTRAL ({neu} neutrales, {pos} positivos, {neg} negativos) — la conversación es informativa sin polarización clara.")

    return " ".join(parts)


def _generate_actionable_insights(items: list[dict], source_stats: dict, query: TrendQuery) -> list[dict]:
    """Genera insights accionables basados en los datos."""
    insights = []
    topic = query.free_topic or query.category or "el tema"

    # 1. Fuente con más engagement
    best_source = max(source_stats.items(), key=lambda x: x[1]["avg_score"]) if source_stats else None
    if best_source and best_source[1]["count"] > 0:
        src_name = best_source[0].replace("_", " ").title()
        insights.append({
            "type": "opportunity",
            "priority": "high",
            "title": f"{src_name} es la fuente con mayor engagement promedio ({best_source[1]['avg_score']}/100)",
            "description": f"La conversación sobre '{topic}' está más activa en {src_name}. Considera enfocar esfuerzos de contenido o monitoreo en esta plataforma.",
        })

    # 2. Sentimiento negativo dominante en alguna fuente
    for src, stats in source_stats.items():
        if stats["dominant_sentiment"] == "negative" and stats["count"] >= 3:
            src_name = src.replace("_", " ").title()
            insights.append({
                "type": "alert",
                "priority": "high",
                "title": f"Sentimiento negativo dominante en {src_name}",
                "description": f"La mayoría de las {stats['count']} señales en {src_name} tienen sentimiento negativo. Posible crisis de reputación o controversia detectada.",
            })

    # 3. Tema presente en Twitter pero no en Reddit/HN
    has_twitter = any(item["source"] == "twitter" for item in items)
    has_reddit = any(item["source"] == "reddit" for item in items)
    if has_twitter and not has_reddit:
        insights.append({
            "type": "opportunity",
            "priority": "medium",
            "title": "Tema viral en Twitter pero ausente en Reddit",
            "description": f"'{topic}' está generando conversación en Twitter/X pero no aparece en Reddit o Hacker News. Puede ser una tendencia incipiente que aún no ha llegado a comunidades técnicas.",
        })

    # 4. Score muy alto pero pocas fuentes
    emerging = [i for i in items if i.get("trend_score", 0) >= 70]
    if emerging:
        top_emerging = emerging[0]
        title = (top_emerging.get("title") or "N/A")[:60]
        insights.append({
            "type": "opportunity",
            "priority": "high",
            "title": f"Tendencia hot detectada: \"{title}\"",
            "description": f"Score {top_emerging.get('trend_score', 0)}/100 con engagement significativo. Esta señal merece atención inmediata.",
        })

    # 5. Diversidad de fuentes
    num_sources = len(source_stats)
    if num_sources >= 4:
        insights.append({
            "type": "info",
            "priority": "low",
            "title": f"Alta diversidad de fuentes ({num_sources} plataformas)",
            "description": f"El tema '{topic}' aparece en {num_sources} fuentes diferentes, indicando que es una tendencia consolidada y multi-plataforma.",
        })
    elif num_sources <= 2:
        insights.append({
            "type": "info",
            "priority": "medium",
            "title": f"Baja diversidad de fuentes ({num_sources} plataformas)",
            "description": f"El tema solo aparece en {num_sources} fuente(s). La tendencia puede ser de nicho o premature.",
        })

    return insights


def _generate_correlations(items: list[dict], source_stats: dict) -> list[dict]:
    """Detecta correlaciones entre fuentes."""
    correlations = []

    # Comparar sentimientos entre fuentes
    sources_with_sentiment = {
        src: stats["dominant_sentiment"]
        for src, stats in source_stats.items()
        if stats["count"] >= 3
    }

    # Si todas las fuentes coinciden en sentimiento
    unique_sentiments = set(sources_with_sentiment.values())
    if len(sources_with_sentiment) >= 3 and len(unique_sentiments) == 1:
        sentiment = unique_sentiments.pop()
        correlations.append({
            "type": "consensus",
            "description": f"Consenso total: todas las fuentes ({', '.join(sources_with_sentiment.keys())}) muestran sentimiento {sentiment}.",
        })

    # Si hay disparidad
    if len(unique_sentiments) >= 2:
        positive_sources = [s for s, sent in sources_with_sentiment.items() if sent == "positive"]
        negative_sources = [s for s, sent in sources_with_sentiment.items() if sent == "negative"]
        if positive_sources and negative_sources:
            correlations.append({
                "type": "divergence",
                "description": f"Divergencia de sentimiento: {', '.join(positive_sources)} es positivo mientras {', '.join(negative_sources)} es negativo. Audiencias diferentes reaccionan distinto.",
            })

    # Comparar scores entre fuentes
    if len(source_stats) >= 2:
        sorted_sources = sorted(source_stats.items(), key=lambda x: x[1]["avg_score"], reverse=True)
        top_src = sorted_sources[0]
        bottom_src = sorted_sources[-1]
        diff = top_src[1]["avg_score"] - bottom_src[1]["avg_score"]
        if diff > 25:
            correlations.append({
                "type": "score_gap",
                "description": f"Brecha de engagement: {top_src[0]} promedia {top_src[1]['avg_score']} vs {bottom_src[0]} con {bottom_src[1]['avg_score']}. La conversación es más intensa en {top_src[0]}.",
            })

    return correlations


def _generate_recommendations(items: list[dict], insights: list[dict], emerging_vs_est: dict, query: TrendQuery) -> list[str]:
    """Genera recomendaciones accionables."""
    recs = []
    topic = query.free_topic or query.category or "el tema"

    # Basado en emergentes
    if emerging_vs_est["emerging"]:
        top_emerging = emerging_vs_est["emerging"][0]
        title = (top_emerging.get("title") or "N/A")[:50]
        recs.append(f"⚡ Seguir de cerca \"{title}\" — es una tendencia emergente que aún no ha llegado a todas las plataformas.")

    # Basado en alertas
    alerts = [i for i in insights if i["type"] == "alert"]
    if alerts:
        recs.append(f"⚠️ Atender alerta de reputación: {alerts[0]['title']}. Monitorear evolución en las próximas 24-48h.")

    # Basado en oportunidades
    opportunities = [i for i in insights if i["type"] == "opportunity" and i["priority"] == "high"]
    if opportunities:
        recs.append(f"🎯 Aprovechar: {opportunities[0]['title']}.")

    # Basado en establecidos
    if emerging_vs_est["established"]:
        recs.append(f"✅ Tendencia consolidada detectada — '{topic}' ya es mainstream en múltiples fuentes.")

    # Basado en diversidad
    if not recs:
        recs.append(f"📊 Continuar monitoreando '{topic}' — los datos son insuficientes para una recomendación fuerte.")

    return recs


def generate_insights(scored_items: list[dict], query: TrendQuery, sentiment_summary: dict) -> dict:
    """
    Punto de entrada del motor de análisis.
    Toma los items puntuados + sentimiento y genera un análisis completo.
    """
    logger.info(f"Generando insights para {len(scored_items)} items...")

    top_items = scored_items[:25] if scored_items else []
    source_stats = _source_breakdown(top_items)
    emerging_vs_est = _detect_emerging_vs_established(top_items)

    summary = _generate_summary(top_items, query, sentiment_summary)
    actionable = _generate_actionable_insights(top_items, source_stats, query)
    correlations = _generate_correlations(top_items, source_stats)
    recommendations = _generate_recommendations(top_items, actionable, emerging_vs_est, query)

    result = {
        "executive_summary": summary,
        "actionable_insights": actionable,
        "correlations": correlations,
        "emerging_vs_established": {
            "emerging": [
                {
                    "title": (i.get("title") or i.get("keyword") or "N/A")[:100],
                    "score": i.get("trend_score", 0),
                    "source": i.get("source", ""),
                    "sources_count": i.get("_total_sources", 1),
                }
                for i in emerging_vs_est["emerging"]
            ],
            "established": [
                {
                    "title": (i.get("title") or i.get("keyword") or "N/A")[:100],
                    "score": i.get("trend_score", 0),
                    "source": i.get("source", ""),
                    "sources_count": i.get("_total_sources", 1),
                }
                for i in emerging_vs_est["established"]
            ],
        },
        "recommendations": recommendations,
        "source_stats": {
            src: {
                "count": s["count"],
                "avg_score": s["avg_score"],
                "dominant_sentiment": s["dominant_sentiment"],
            }
            for src, s in source_stats.items()
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.success(f"Insights generados: {len(actionable)} insights, {len(correlations)} correlaciones, {len(recommendations)} recomendaciones")
    return result
