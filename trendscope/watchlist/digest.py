"""Periodic digest: send a summary of recent history to a webhook."""

from __future__ import annotations

from typing import Any

from loguru import logger

from trendscope.watchlist.alerts import send_webhook


def build_digest_payload(
    topic: str,
    geo: str,
    records: list,
    forecast: dict[str, Any] | None = None,
    top_n: int = 10,
) -> dict[str, Any]:
    """Resumen compacto de history (records DESC: más reciente primero)."""
    if not records:
        return {
            "type": "digest",
            "topic": topic,
            "geo": geo,
            "points": 0,
            "message": "No recent history",
        }

    latest = records[0]
    scores = [r.top_score or 0.0 for r in records]
    return {
        "type": "digest",
        "topic": topic,
        "geo": geo,
        "points": len(records),
        "latest": {
            "analyzed_at": latest.analyzed_at.isoformat(),
            "top_score": latest.top_score,
            "total_signals": latest.total_signals,
            "positive": latest.positive,
            "negative": latest.negative,
            "neutral": latest.neutral,
        },
        "score_min": min(scores),
        "score_max": max(scores),
        "score_avg": round(sum(scores) / len(scores), 2),
        "forecast": forecast,
    }


def send_digest(store, item, top_n: int = 10) -> bool:
    """Construye y envía digest del topic del item al digest_webhook."""
    webhook = item.digest_webhook or item.alert_webhook
    if not webhook:
        return False

    from trendscope.analyzer.forecast import forecast_topic

    records = store.get_history(topic=item.topic, days=7, limit=top_n, org_id=item.org_id)
    forecast = forecast_topic(store, item.topic, days=30, org_id=item.org_id)
    payload = build_digest_payload(item.topic, item.geo, records, forecast=forecast)
    ok = send_webhook(webhook, payload)
    if ok:
        logger.info("Digest sent for {}", item.topic)
    return ok
