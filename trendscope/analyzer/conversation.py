"""Conversation intelligence: acceptance, toxicity, mood + emoji.

Focus: what people say in **comments**, not only the post headline.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

# Toxic / heated lexicons (substring-friendly roots ≥4 chars)
_TOXIC_ES = {
    "imbécil", "imbecil", "idiota", "estúpido", "estupido", "basura", "mierda",
    "maldito", "hijueputa", "malparido", "gonorrea", "cerote", "estafador",
    "corrupto", "ladrón", "ladron", "payaso", "inútil", "inutil", "desastre",
    "asco", "odio", "matar", "violencia", "groser", "insulto",
}

_TOXIC_EN = {
    "stupid", "idiot", "moron", "trash", "garbage", "scam", "fraud",
    "liar", "hate", "kill", "damn", "crap", "suck", "loser", "pathetic",
    "useless", "disgusting", "corrupt",
}

_SUPPORT_ES = {
    "apoyo", "apoya", "excelente", "genial", "felicit", "orgullo", "admir",
    "victoria", "mejor", "bravo", "celebro", "respaldo", "defiende",
}

_AGAINST_ES = {
    "crític", "critic", "rechaz", "desastre", "fracas", "renuncia", "corrup",
    "mentir", "protest", "vergüenz", "verguenz", "indign", "hundi",
}

_SUPPORT_EN = {"support", "great", "excellent", "love", "proud", "win", "applaud"}
_AGAINST_EN = {"against", "critic", "reject", "fail", "scandal", "protest", "hate"}


@dataclass
class MoodSummary:
    mood: str
    emoji: str
    label: str
    acceptance_score: float
    support: int
    against: int
    mixed: int
    neutral: int
    toxic: int
    hot: int
    total: int
    dominant_emotion: str
    top_phrases: list[str]


_MOOD_EMOJI = {
    "calm": ("😌", "Calmado"),
    "supportive": ("😊", "A favor"),
    "mixed": ("😐", "Mixto"),
    "hot": ("😠", "Caliente"),
    "toxic": ("🤬", "Candente / tóxico"),
    "polarized": ("⚠️", "Polarizado"),
    "quiet": ("😶", "Sin conversación"),
}


def _lex_count(text: str, lex: set[str]) -> int:
    t = text.lower()
    words = set(re.findall(r"[a-záéíóúñü]+", t))
    n = 0
    for w in words:
        if w in lex:
            n += 1
            continue
        for root in lex:
            if len(root) >= 4 and root in w:
                n += 1
                break
    return n


def classify_comment(text: str, sentiment_label: str = "neutral") -> dict:
    """Heuristic stance/toxicity for one comment."""
    if not text or len(text.strip()) < 3:
        return {"stance": "unknown", "toxic": False, "hot": False}

    sup = _lex_count(text, _SUPPORT_ES) + _lex_count(text, _SUPPORT_EN)
    ag = _lex_count(text, _AGAINST_ES) + _lex_count(text, _AGAINST_EN)
    tox = _lex_count(text, _TOXIC_ES) + _lex_count(text, _TOXIC_EN)

    words = text.lower().split()
    negations = {"no", "ni", "nunca", "not", "never", "sin"}
    for i, w in enumerate(words):
        if w in negations and i + 1 < len(words):
            nxt = words[i + 1]
            if any(r in nxt for r in _SUPPORT_ES | _SUPPORT_EN):
                sup = max(0, sup - 1)
                ag += 1
            elif any(r in nxt for r in _AGAINST_ES | _AGAINST_EN):
                ag = max(0, ag - 1)
                sup += 1

    is_hot = tox >= 1 or text.isupper() and len(text) > 20
    if sup > ag:
        stance = "support"
    elif ag > sup:
        stance = "against"
    elif sup and ag:
        stance = "mixed"
    elif sentiment_label == "positive":
        stance = "support"
    elif sentiment_label == "negative":
        stance = "against"
    else:
        stance = "neutral"

    return {"stance": stance, "toxic": tox >= 2 or (tox >= 1 and is_hot), "hot": is_hot}


def top_phrases(texts: list[str], limit: int = 5) -> list[str]:
    """Simple distinctive bigrams / short lines from comments."""
    freq: dict[str, int] = {}
    for t in texts:
        clean = re.sub(r"\s+", " ", (t or "").strip())
        if 20 <= len(clean) <= 80:
            freq[clean[:80]] = freq.get(clean[:80], 0) + 1
        words = re.findall(r"[a-záéíóúñü]{4,}", clean.lower())
        for i in range(len(words) - 1):
            bg = f"{words[i]} {words[i+1]}"
            if len(bg) >= 10:
                freq[bg] = freq.get(bg, 0) + 1
    ranked = sorted(freq.items(), key=lambda x: (-x[1], x[0]))
    return [p for p, c in ranked if c >= 1][:limit]


def analyze_conversation(comments: list[dict], posts: list[dict] | None = None) -> dict:
    """
    Aggregate mood from comments (primary) + posts (context).
    Returns JSON-serializable summary for API/dashboard.
    """
    posts = posts or []
    bodies = [
        (c.get("text") or c.get("title") or "")
        for c in comments
        if c.get("kind") in (None, "comment") or c.get("source") == "reddit_comment"
    ]
    # If empty markers, treat all as comments
    if not bodies:
        bodies = [(c.get("text") or c.get("title") or "") for c in comments]

    # Prefer explicit comment lists
    if comments and all(c.get("kind") == "post" for c in comments if c.get("kind")):
        bodies = []

    support = against = mixed = neutral = toxic_n = hot_n = 0
    emotion_fallback = {"positive": 0, "negative": 0, "neutral": 0}

    for c in comments:
        kind = c.get("kind") or ("post" if c.get("source") in {"reddit", "google_news", "twitter"} and not c.get("post_id") else "comment")
        text = c.get("text") or c.get("title") or ""
        label = (c.get("sentiment_label") or "neutral").lower()
        info = classify_comment(text, sentiment_label=label)
        st = info["stance"]
        if st == "support":
            support += 1
        elif st == "against":
            against += 1
        elif st == "mixed":
            mixed += 1
        else:
            neutral += 1
        if info["toxic"]:
            toxic_n += 1
        if info["hot"]:
            hot_n += 1
        if label in emotion_fallback:
            emotion_fallback[label] += 1

    total = max(1, support + against + mixed + neutral)
    # Comments weigh more: if we have real comments, use all classified rows
    acceptance = round((support - against) / total, 3)

    polarized = support >= 3 and against >= 3 and abs(support - against) <= max(2, total * 0.2)
    toxic_ratio = toxic_n / total
    hot_ratio = (hot_n + toxic_n) / total

    if total <= 1 and neutral >= total:
        mood = "quiet"
    elif toxic_ratio >= 0.25 or (toxic_n >= 2 and hot_ratio >= 0.4):
        mood = "toxic"
    elif polarized and (support + against) / total >= 0.7:
        mood = "polarized"
    elif hot_ratio >= 0.35 or against > support * 1.5:
        mood = "hot"
    elif acceptance >= 0.25:
        mood = "supportive"
    elif acceptance <= -0.25:
        mood = "hot"
    elif mixed > max(support, against):
        mood = "mixed"
    elif neutral / total >= 0.7:
        mood = "calm"
    else:
        mood = "mixed"

    emoji, label = _MOOD_EMOJI.get(mood, ("🤔", mood))
    dominant = max(emotion_fallback, key=emotion_fallback.get)
    if toxic_n and dominant == "neutral":
        dominant = "anger"

    phrases = top_phrases(bodies or [c.get("text") or "" for c in comments])

    summary = MoodSummary(
        mood=mood,
        emoji=emoji,
        label=label,
        acceptance_score=acceptance,
        support=support,
        against=against,
        mixed=mixed,
        neutral=neutral,
        toxic=toxic_n,
        hot=hot_n,
        total=support + against + mixed + neutral,
        dominant_emotion=dominant,
        top_phrases=phrases,
    )
    return asdict(summary)
