"""Alert evaluation and webhook delivery for watchlist runs."""

from __future__ import annotations

import ipaddress
import json
from urllib.parse import urlparse

import httpx
from loguru import logger

from trendscope.settings import settings


def _is_ssrf_blocked(url: str) -> bool:
    """Bloquea hosts de metadata / loopback / link-local / privados por defecto."""
    try:
        parsed = urlparse(url)
    except Exception:
        return True
    if parsed.scheme not in {"http", "https"}:
        return True
    host = parsed.hostname or ""
    if not host:
        return True
    if host in {"localhost", "metadata.google.internal"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True
    except ValueError:
        # hostname DNS — no resolvemos aquí (evitar SSRF vía DNS rebinding en MVP)
        # Permitimos hostnames públicos habituales; bloqueamos solo IP literals peligrosas
        if host.endswith(".internal") or host.endswith(".local"):
            return True
    return False


def evaluate_triggers(
    current: dict,
    previous: dict | None,
    *,
    min_score: float | None = None,
    min_volume: int | None = None,
    sentiment_flip: bool = False,
) -> list[str]:
    """Devuelve lista de triggers activados."""
    triggered: list[str] = []

    top_score = float(current.get("top_score") or 0)
    total = int(current.get("total_signals") or 0)
    positive = int(current.get("positive") or 0)
    negative = int(current.get("negative") or 0)

    if min_score is not None and top_score >= float(min_score):
        triggered.append("min_score")

    if min_volume is not None and total >= int(min_volume):
        triggered.append("min_volume")

    if sentiment_flip and previous:
        prev_pos = int(previous.get("positive") or 0)
        prev_neg = int(previous.get("negative") or 0)
        prev_overall = "positive" if prev_pos >= prev_neg else "negative"
        curr_overall = "positive" if positive >= negative else "negative"
        if prev_overall != curr_overall:
            triggered.append("sentiment_flip")

    return triggered


def send_webhook(url: str, payload: dict) -> bool:
    """POST JSON al webhook. Nunca lanza al caller."""
    if not settings.alerts_enabled:
        logger.debug("Alertas deshabilitadas — skip webhook")
        return False
    if _is_ssrf_blocked(url):
        logger.warning("Webhook bloqueado (SSRF/policy): {}", url)
        return False

    try:
        resp = httpx.post(
            url,
            json=payload,
            timeout=float(settings.alerts_timeout_seconds),
        )
        if resp.status_code >= 400:
            logger.warning("Webhook {} devolvió {}", url, resp.status_code)
            return False
        return True
    except Exception as e:
        logger.warning("Webhook falló ({}): {}", url, e)
        return False


def build_alert_payload(
    topic: str,
    geo: str,
    current: dict,
    previous: dict | None,
    triggered_by: list[str],
) -> dict:
    return {
        "topic": topic,
        "geo": geo,
        "top_score": current.get("top_score"),
        "previous_score": (previous or {}).get("top_score"),
        "total_signals": current.get("total_signals"),
        "positive": current.get("positive"),
        "negative": current.get("negative"),
        "neutral": current.get("neutral"),
        "triggered_by": triggered_by,
        "analyzed_at": current.get("analyzed_at"),
    }
