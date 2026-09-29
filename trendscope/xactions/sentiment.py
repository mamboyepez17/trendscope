"""
XActions-PY — Optional lightweight sentiment (lexicon).

No hard dependency. If `pysentimiento` is installed and
XACTIONS_SENTIMENT=transformer, it can be used later; default is lexicon.

Scores in [-1, 1] per tweet + batch summary.
"""

from __future__ import annotations

import re
from typing import Any

# Small bilingual lexicons (intentionally tiny — extendable via extra lists)
_POS_EN = {
    "good", "great", "love", "excellent", "amazing", "awesome", "happy",
    "win", "best", "cool", "nice", "fantastic", "brilliant", "success",
}
_NEG_EN = {
    "bad", "hate", "terrible", "awful", "worst", "sad", "fail", "ugly",
    "angry", "poor", "horrible", "disaster", "scam", "fraud",
}
_POS_ES = {
    "bueno", "buena", "genial", "excelente", "increible", "increíble",
    "amor", "feliz", "mejor", "ganar", "éxito", "exito", "cool", "nice",
}
_NEG_ES = {
    "malo", "mala", "odio", "terrible", "horrible", "triste", "fracaso",
    "peor", "feo", "estafa", "fraude", "basura",
}

_WORD_RE = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def _normalize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text or "")]


def score_text(
    text: str,
    *,
    extra_positive: set[str] | None = None,
    extra_negative: set[str] | None = None,
) -> dict[str, Any]:
    """
    Lexicon score in [-1, 1].
    Returns {score, label, hits_positive, hits_negative}.
    """
    pos = _POS_EN | _POS_ES | (extra_positive or set())
    neg = _NEG_EN | _NEG_ES | (extra_negative or set())
    words = _normalize(text)
    p = [w for w in words if w in pos]
    n = [w for w in words if w in neg]
    total = len(p) + len(n)
    if total == 0:
        score = 0.0
        label = "neutral"
    else:
        score = round((len(p) - len(n)) / total, 4)
        if score > 0.15:
            label = "positive"
        elif score < -0.15:
            label = "negative"
        else:
            label = "neutral"
    return {
        "score": score,
        "label": label,
        "hits_positive": p,
        "hits_negative": n,
    }


def score_tweets(tweets: list[dict[str, Any]], text_key: str = "text") -> list[dict[str, Any]]:
    """Attach sentiment to each tweet (new key 'sentiment')."""
    out = []
    for t in tweets:
        item = dict(t)
        item["sentiment"] = score_text(t.get(text_key) or "")
        out.append(item)
    return out


def summarize_sentiment(tweets: list[dict[str, Any]]) -> dict[str, Any]:
    """Batch summary over tweets (uses existing 'sentiment' or scores text)."""
    scored = []
    for t in tweets:
        s = t.get("sentiment")
        if not isinstance(s, dict):
            s = score_text(t.get("text") or "")
        scored.append(s)
    n = len(scored)
    if n == 0:
        return {
            "count": 0,
            "avg_score": 0.0,
            "positive": 0,
            "neutral": 0,
            "negative": 0,
        }
    avg = round(sum(s["score"] for s in scored) / n, 4)
    return {
        "count": n,
        "avg_score": avg,
        "positive": sum(1 for s in scored if s["label"] == "positive"),
        "neutral": sum(1 for s in scored if s["label"] == "neutral"),
        "negative": sum(1 for s in scored if s["label"] == "negative"),
    }
