"""Detector de emociones por comentario (6 idiomas + jerga por país + emojis).

Clasifica cada texto en una distribución sobre cinco estados de ánimo:

    joy (alegría) · anger (enojo) · sadness (tristeza) · fear (miedo) · neutral

Es 100% local y determinista. Se usa:
  - como motor principal cuando pysentimiento/torch no están instalados;
  - como complemento del modelo (los emojis y la jerga local los captura
    mejor un léxico que un modelo entrenado en tweets genéricos).

Los léxicos viven en sentiment/lexicons: idioma base (es, en, pt, fr, de, it)
+ jerga del país del análisis + léxico propio (CUSTOM_LEXICON_PATH).

Reglas:
  - Texto normalizado (minúsculas, sin tildes) y tokenizado por palabra,
    así "increíble!" y "INCREIBLE" cuentan igual.
  - Raíces ≥5 letras se comparan como prefijo de palabra ("enojad" → enojado,
    enojada); raíces cortas solo por palabra exacta. Nunca subcadenas en medio
    de otra palabra (evita "contra" dentro de "encontrar").
  - Negación en las 3 palabras previas ("no estoy feliz") invierte alegría a
    tristeza y apaga emociones negativas ("no tengo miedo").
  - Intensificadores ("muy", "demasiado", "!!!", MAYÚSCULAS) suben el peso.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache

EMOTIONS: tuple[str, ...] = ("joy", "anger", "sadness", "fear", "neutral")
NEGATIVE_EMOTIONS: tuple[str, ...] = ("anger", "sadness", "fear")


def normalize(text: str) -> str:
    """Minúsculas y sin tildes (ñ → n)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", (text or "").lower())
        if unicodedata.category(c) != "Mn"
    )


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


# Emojis → emoción (universales; peso fuerte: en comentarios son muy explícitos)
EMOJI_EMOTION: dict[str, str] = {
    "😀": "joy", "😃": "joy", "😄": "joy", "😁": "joy", "😆": "joy", "😂": "joy",
    "🤣": "joy", "😊": "joy", "😍": "joy", "🥰": "joy", "😘": "joy", "🤩": "joy",
    "🥳": "joy", "👏": "joy", "🙌": "joy", "💪": "joy", "🎉": "joy", "❤": "joy",
    "💙": "joy", "💚": "joy", "💛": "joy", "🔥": "joy", "👍": "joy", "✨": "joy",
    "🙏": "joy", "😎": "joy", "💯": "joy",
    "😠": "anger", "😡": "anger", "🤬": "anger", "👎": "anger", "🖕": "anger",
    "💩": "anger", "🤮": "anger", "🤢": "anger", "😤": "anger", "🙄": "anger",
    "😒": "anger", "🤡": "anger",
    "😢": "sadness", "😭": "sadness", "😞": "sadness", "😔": "sadness",
    "😟": "sadness", "🥺": "sadness", "💔": "sadness", "😿": "sadness",
    "😥": "sadness", "😓": "sadness", "🖤": "sadness",
    "😨": "fear", "😰": "fear", "😱": "fear", "😧": "fear", "😬": "fear",
    "🫣": "fear", "😖": "fear", "⚠": "fear",
}


@lru_cache(maxsize=128)
def _compile(lang: str, geo: str | None):
    """Léxico del idioma/país separado en exactas y raíces (cacheado)."""
    from trendscope.sentiment.lexicons import build_pack

    pack = build_pack(lang, geo)
    words = {k: {w for w in v if " " not in w} for k, v in pack.items()}
    exact = {k: {w for w in v if len(w) < 5} for k, v in words.items()}
    stems = {k: tuple(sorted(w for w in v if len(w) >= 5)) for k, v in words.items()}
    # Frases de varias palabras ("poca madre", "saco cheio"): coincidencia exacta
    phrases = {
        k: tuple(re.compile(r"\b" + re.escape(p) + r"\b") for p in v if " " in p)
        for k, v in pack.items()
        if k in ("joy", "anger", "sadness", "fear", "neg")
    }
    return exact, stems, pack["negations"], pack["intensifiers"], phrases


def clear_cache() -> None:
    from trendscope.sentiment.lexicons import clear_cache as _clear_packs

    _compile.cache_clear()
    _clear_packs()


def _match(token: str, exact: set[str], stems: tuple[str, ...]) -> bool:
    if token in exact:
        return True
    return any(token.startswith(s) for s in stems)


def _token_emotion(token: str, exact, stems) -> str | None:
    """Emoción léxica de un token (o 'neg' genérico, o None)."""
    for emo in NEGATIVE_EMOTIONS + ("joy", "neg"):
        if _match(token, exact[emo], stems[emo]):
            return emo
    return None


@dataclass
class EmotionResult:
    distribution: dict[str, float]
    dominant: str
    intensity: float          # 0–1: fuerza de la emoción no neutral
    polarity: float           # −1 (muy negativo) … +1 (muy positivo)
    hits: dict[str, float] = field(default_factory=dict)
    emojis: int = 0
    lang: str = "es"


def dominant_of(dist: dict[str, float], min_emotion: float = 0.45) -> str:
    """Emoción dominante: la mayor no-neutral si la carga emocional ≥ umbral."""
    if 1.0 - dist.get("neutral", 0.0) < min_emotion:
        return "neutral"
    return max(NEGATIVE_EMOTIONS + ("joy",), key=lambda e: dist.get(e, 0.0))


def analyze_text(text: str, lang: str | None = None, geo: str | None = None) -> EmotionResult:
    """Distribución de emociones de un texto (sin modelos, determinista).

    lang: idioma del texto (se detecta si no se pasa; por defecto el del país).
    geo:  país del análisis → activa su jerga regional.
    """
    raw = text or ""
    tokens = tokenize(raw)
    geo = (geo or "").upper() or None
    if lang is None:
        from trendscope.core.locale import language_for
        from trendscope.sentiment.lang import detect

        lang = detect(raw, default=language_for(geo) if geo else "es")
    exact, stems, negations, intensifiers, phrases = _compile(lang, geo)
    scores = {"joy": 0.0, "anger": 0.0, "sadness": 0.0, "fear": 0.0}

    norm_text = " ".join(tokens)
    for emo, pats in phrases.items():
        for pat in pats:
            if pat.search(norm_text):
                if emo == "neg":
                    scores["anger"] += 0.6
                    scores["sadness"] += 0.4
                else:
                    scores[emo] += 1.0

    # Emojis (peso 1.2 cada uno, máx. 3 por tipo para no saturar)
    emoji_count = 0
    per_emoji: dict[str, int] = {}
    for ch in raw:
        emo = EMOJI_EMOTION.get(ch)
        if emo:
            per_emoji[ch] = per_emoji.get(ch, 0) + 1
            if per_emoji[ch] <= 3:
                scores[emo] += 1.2
                emoji_count += 1

    # Intensidad global por signos y mayúsculas
    shout = 1.0
    if "!!" in raw:
        shout += 0.25
    letters = [c for c in raw if c.isalpha()]
    if len(letters) >= 12 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        shout += 0.35

    for i, tok in enumerate(tokens):
        emo = _token_emotion(tok, exact, stems)
        if emo is None:
            continue
        weight = 1.0
        window = tokens[max(0, i - 3):i]
        if any(w in intensifiers for w in window):
            weight *= 1.5
        negated = any(w in negations for w in window)

        if emo == "neg":
            if negated:  # "no es malo" → leve positivo
                scores["joy"] += 0.4 * weight
            else:
                scores["anger"] += 0.6 * weight
                scores["sadness"] += 0.4 * weight
            continue
        if negated:
            if emo == "joy":  # "no estoy feliz" → tristeza/enojo
                scores["sadness"] += 0.6 * weight
                scores["anger"] += 0.3 * weight
            # "no tengo miedo", "no me enoja" → se apaga la emoción
            continue
        scores[emo] += weight

    scores = {k: v * shout for k, v in scores.items()}
    total = sum(scores.values())
    if total <= 0:
        dist = {e: 0.0 for e in EMOTIONS}
        dist["neutral"] = 1.0
        return EmotionResult(dist, "neutral", 0.0, 0.0, {}, emoji_count, lang)

    # Neutral decrece con la evidencia: 1 pista → 0.5, 2 → 0.33, 4 → 0.2
    neutral = 1.0 / (1.0 + total)
    dist = {k: (v / total) * (1.0 - neutral) for k, v in scores.items()}
    dist["neutral"] = neutral
    dist = {k: round(v, 4) for k, v in dist.items()}
    dominant = dominant_of(dist)
    neg = dist["anger"] + dist["sadness"] + dist["fear"]
    polarity = round(dist["joy"] - neg, 4)
    intensity = round(1.0 - neutral, 4)
    return EmotionResult(dist, dominant, intensity, polarity, scores, emoji_count, lang)


# ── Mezcla con salidas de modelos (pysentimiento / Claude) ────────────────────

# pysentimiento emotion: joy, sadness, anger, fear, surprise, disgust, others
_MODEL_MAP = {
    "joy": "joy", "alegria": "joy", "happiness": "joy",
    "anger": "anger", "enojo": "anger", "disgust": "anger",
    "sadness": "sadness", "tristeza": "sadness",
    "fear": "fear", "miedo": "fear",
    "others": "neutral", "neutral": "neutral", "surprise": "neutral",
}


def from_model_probas(probas: dict | None) -> dict[str, float] | None:
    """Convierte probas de un modelo externo a las 5 emociones TrendScope."""
    if not probas or not isinstance(probas, dict):
        return None
    dist = {e: 0.0 for e in EMOTIONS}
    for k, v in probas.items():
        target = _MODEL_MAP.get(str(k).lower())
        try:
            val = float(v)
        except (TypeError, ValueError):
            continue
        if target and val > 0:
            dist[target] += val
    total = sum(dist.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in dist.items()}


def blend(lexical: dict[str, float], model: dict[str, float] | None,
          model_weight: float = 0.65) -> dict[str, float]:
    """Mezcla ponderada; si el léxico es neutro puro confía más en el modelo."""
    if not model:
        return dict(lexical)
    if lexical.get("neutral", 1.0) >= 0.999:
        model_weight = max(model_weight, 0.85)
    out = {
        e: model_weight * model.get(e, 0.0) + (1 - model_weight) * lexical.get(e, 0.0)
        for e in EMOTIONS
    }
    total = sum(out.values()) or 1.0
    return {k: v / total for k, v in out.items()}
