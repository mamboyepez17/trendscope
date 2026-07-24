# sentiment/base.py
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SentimentResult:
    """Resultado estandar de analisis de sentimiento."""
    text: str
    label: Literal["positive", "negative", "neutral"]
    score: float           # 0.0 a 1.0 — confianza
    engine: str            # "local" | "claude" | "failed"
    emotions: dict = field(default_factory=dict)


SENTIMENT_EMOJI: dict[str, str] = {
    "positive": "+",
    "negative": "-",
    "neutral": "~",
}


def format_sentiment(result: SentimentResult) -> str:
    """Formatea resultado de sentimiento para display."""
    symbol = SENTIMENT_EMOJI.get(result.label, "?")
    return f"[{symbol}] {result.label} ({result.score:.0%})"
