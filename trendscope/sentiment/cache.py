"""Score calibration and in-memory LRU cache for sentiment."""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict

from trendscope.sentiment.base import SentimentResult

# ── Calibración ───────────────────────────────────────────────────────────────


def calibrate_score(label: str, raw_prob: float) -> float:
    """
    Mapea la prob del modelo ganador a un score usable 0–1.
    - NEU → cerca de 0.5
    - POS/NEG → 0.5–1.0 según confianza
    """
    p = max(0.0, min(1.0, float(raw_prob)))
    if label == "neutral":
        # 0.5 ± desviación pequeña por incertidumbre
        return round(0.45 + 0.1 * p, 3)
    # positivo/negativo: 0.5 + (p-0.5) escalado
    return round(0.5 + (p - 0.5) * 1.0, 3)


# ── Cache LRU ─────────────────────────────────────────────────────────────────

_lock = threading.Lock()
_cache: OrderedDict[str, tuple[float, SentimentResult]] = OrderedDict()
_MAX = 2000
_TTL = 600.0  # 10 min


def _key(text: str, engine: str) -> str:
    h = hashlib.sha1(f"{engine}|{text}".encode("utf-8")).hexdigest()
    return h


def cache_get(text: str, engine: str) -> SentimentResult | None:
    k = _key(text, engine)
    with _lock:
        hit = _cache.get(k)
        if not hit:
            return None
        ts, result = hit
        if time.time() - ts > _TTL:
            _cache.pop(k, None)
            return None
        _cache.move_to_end(k)
        return result


def cache_set(text: str, engine: str, result: SentimentResult) -> None:
    k = _key(text, engine)
    with _lock:
        _cache[k] = (time.time(), result)
        _cache.move_to_end(k)
        while len(_cache) > _MAX:
            _cache.popitem(last=False)


def cache_stats() -> dict:
    with _lock:
        return {"entries": len(_cache), "max": _MAX, "ttl_seconds": _TTL}


def cache_clear() -> None:
    with _lock:
        _cache.clear()
