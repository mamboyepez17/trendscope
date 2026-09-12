"""Runtime health score per data source (success/failure/latency EMA)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from trendscope.settings import settings


@dataclass
class SourceStats:
    successes: int = 0
    failures: int = 0
    latency_ema: float = 0.0
    last_error: str | None = None
    last_ok_at: float | None = None

    @property
    def score(self) -> float:
        """0.0–1.0 health score."""
        total = self.successes + self.failures
        if total == 0:
            return 1.0  # desconocida = optimista
        success_rate = self.successes / total
        # Penalizar si lleva mucho sin éxito (más de 1h)
        if self.last_ok_at and time.time() - self.last_ok_at > 3600:
            success_rate *= 0.5
        return round(max(0.0, min(1.0, success_rate)), 3)


_registry: dict[str, SourceStats] = {}
_lock = threading.Lock()


def record_success(name: str, duration: float) -> None:
    with _lock:
        stats = _registry.setdefault(name, SourceStats())
        stats.successes += 1
        stats.last_ok_at = time.time()
        stats.last_error = None
        if stats.latency_ema == 0:
            stats.latency_ema = duration
        else:
            stats.latency_ema = 0.3 * duration + 0.7 * stats.latency_ema


def record_failure(name: str, error: str) -> None:
    with _lock:
        stats = _registry.setdefault(name, SourceStats())
        stats.failures += 1
        stats.last_error = error[:200]


def should_skip(name: str) -> bool:
    """Si la fuente está muy enferma y la feature está activa, saltarla."""
    if not settings.source_health_skip:
        return False
    with _lock:
        stats = _registry.get(name)
        if not stats:
            return False
        total = stats.successes + stats.failures
        if total < 3:
            return False
        return stats.score < 0.2


def snapshot() -> dict[str, dict]:
    with _lock:
        return {
            name: {
                "score": s.score,
                "successes": s.successes,
                "failures": s.failures,
                "latency_ema": round(s.latency_ema, 3),
                "last_error": s.last_error,
            }
            for name, s in _registry.items()
        }


def reset_for_tests() -> None:
    with _lock:
        _registry.clear()
