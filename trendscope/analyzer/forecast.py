"""Basic forecasting over watchlist history: EMA, velocity, breakout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence


@dataclass
class Forecast:
    topic: str
    points: int
    ema: float
    last_score: float
    velocity: float
    breakout: bool
    trend: str  # rising | falling | stable


def ema_series(values: Sequence[float], alpha: float = 0.3) -> list[float]:
    """EMA secuencial. alpha en (0,1]; mayor = más peso al reciente."""
    if not values:
        return []
    out = [float(values[0])]
    for v in values[1:]:
        out.append(alpha * float(v) + (1 - alpha) * out[-1])
    return out


def velocity(values: Sequence[float]) -> float:
    """Δscore por punto temporal (asumiendo series equiespaciadas)."""
    if len(values) < 2:
        return 0.0
    return (float(values[-1]) - float(values[0])) / (len(values) - 1)


def is_breakout(values: Sequence[float], z_threshold: float = 2.0) -> bool:
    """Breakout si el último valor está z_threshold desviaciones sobre la media."""
    if len(values) < 3:
        return False
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = var**0.5
    if std == 0:
        return float(values[-1]) > mean
    z = (float(values[-1]) - mean) / std
    return z >= z_threshold


def classify_trend(vel: float, eps: float = 0.5) -> str:
    if vel >= eps:
        return "rising"
    if vel <= -eps:
        return "falling"
    return "stable"


def forecast_from_scores(
    topic: str,
    scores_chronological: Sequence[float],
    alpha: float = 0.3,
    z_threshold: float = 2.0,
) -> Forecast:
    # history suele venir DESC (más reciente primero) → invertir
    values = [float(s) for s in scores_chronological]
    ema = ema_series(values, alpha=alpha)
    vel = velocity(values)
    return Forecast(
        topic=topic,
        points=len(values),
        ema=round(ema[-1], 3) if ema else 0.0,
        last_score=round(values[-1], 3) if values else 0.0,
        velocity=round(vel, 4),
        breakout=is_breakout(values, z_threshold=z_threshold),
        trend=classify_trend(vel),
    )


def forecast_topic(store, topic: str, days: int = 30) -> dict[str, Any] | None:
    """Calcula forecast desde el store de watchlist/history."""
    records = store.get_history(topic=topic, days=days, limit=200)
    if not records:
        return None
    # get_history devuelve DESC (más reciente primero) → invertir a chronological
    scores = [r.top_score or 0.0 for r in reversed(records)]
    fc = forecast_from_scores(topic, scores)
    return {
        "topic": fc.topic,
        "points": fc.points,
        "ema": fc.ema,
        "last_score": fc.last_score,
        "velocity": fc.velocity,
        "breakout": fc.breakout,
        "trend": fc.trend,
    }
