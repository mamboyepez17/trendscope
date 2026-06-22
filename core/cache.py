# core/cache.py
"""Cache simple en memoria para resultados de scrapers.
Evita requests repetidos cuando se consulta el mismo tema en corto tiempo.
"""
import time
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 300  # 5 minutos


def get(key: str) -> Any | None:
    """Obtiene valor del cache si no ha expirado."""
    if key in _cache:
        ts, value = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return value
        del _cache[key]
    return None


def set(key: str, value: Any) -> None:
    """Guarda valor en cache con timestamp."""
    _cache[key] = (time.time(), value)


def clear() -> None:
    """Limpia todo el cache."""
    _cache.clear()


def stats() -> dict:
    """Retorna estadisticas del cache."""
    now = time.time()
    valid = sum(1 for ts, _ in _cache.values() if now - ts < CACHE_TTL)
    return {
        "total_entries": len(_cache),
        "valid_entries": valid,
        "ttl_seconds": CACHE_TTL,
    }
