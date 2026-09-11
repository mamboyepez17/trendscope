"""Lightweight operational metrics for TrendScope."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

_lock = threading.Lock()
_counters: dict[str, int] = defaultdict(int)
_timings: dict[str, list[float]] = defaultdict(list)
_started_at = time.time()


def incr(name: str, value: int = 1) -> None:
    with _lock:
        _counters[name] += value


def observe(name: str, seconds: float) -> None:
    with _lock:
        bucket = _timings[name]
        bucket.append(seconds)
        # Cap para no crecer sin fin
        if len(bucket) > 500:
            del bucket[: len(bucket) - 500]


def snapshot() -> dict[str, Any]:
    with _lock:
        timings = {}
        for name, values in _timings.items():
            if not values:
                continue
            timings[name] = {
                "count": len(values),
                "avg_seconds": round(sum(values) / len(values), 4),
                "max_seconds": round(max(values), 4),
            }
        return {
            "uptime_seconds": round(time.time() - _started_at, 1),
            "counters": dict(_counters),
            "timings": timings,
        }


def render_prometheus() -> str:
    """Texto simple estilo Prometheus (sin dependencia de prometheus_client)."""
    snap = snapshot()
    lines = [
        f"# TYPE trendscope_uptime_seconds gauge",
        f"trendscope_uptime_seconds {snap['uptime_seconds']}",
    ]
    for key, val in sorted(snap["counters"].items()):
        metric = f"trendscope_{key}"
        lines.append(f"# TYPE {metric} counter")
        lines.append(f"{metric} {val}")
    for key, stats in sorted(snap["timings"].items()):
        base = f"trendscope_{key}"
        lines.append(f"# TYPE {base}_seconds summary")
        lines.append(f'{base}_seconds_count{{}} {stats["count"]}')
        lines.append(f'{base}_seconds_sum{{}} {stats["avg_seconds"] * stats["count"]}')
    return "\n".join(lines) + "\n"


def reset_for_tests() -> None:
    with _lock:
        _counters.clear()
        _timings.clear()
