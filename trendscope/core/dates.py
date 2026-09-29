"""Fechas: parseo tolerante y ventana de frescura común a todas las fuentes."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime


def parse_date(value) -> float | None:
    """Convierte fechas de cualquier fuente a timestamp UTC (o None).

    Soporta: unix (int/float/str), RFC 822 de RSS ("Tue, 29 Sep 2026 10:00:00 GMT"),
    ISO 8601 ("2026-09-29T10:00:00Z") y GDELT ("20260929T100000Z").
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    s = str(value).strip()
    if not s:
        return None
    if s.replace(".", "", 1).isdigit():
        v = float(s)
        return v if v > 0 else None
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).timestamp()
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        return None


def cutoff_ts(days: float) -> float:
    return time.time() - float(days) * 86400


def since_iso(days: float) -> str:
    """ISO 8601 UTC del inicio de la ventana (Bluesky `since`)."""
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def since_day(days: float) -> str:
    """YYYY-MM-DD del inicio de la ventana (operador `since:` de X)."""
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def reddit_time_filter(days: float) -> str:
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"


def age_hours(ts: float | None) -> float | None:
    if not ts:
        return None
    return max(0.0, (time.time() - ts) / 3600)
