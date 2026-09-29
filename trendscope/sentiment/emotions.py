"""Detector de emociones por comentario (ES/EN + jerga LatAm + emojis).

Clasifica cada texto en una distribución sobre cinco estados de ánimo:

    joy (alegría) · anger (enojo) · sadness (tristeza) · fear (miedo) · neutral

Es 100% local y determinista. Se usa:
  - como motor principal cuando pysentimiento/torch no están instalados;
  - como complemento del modelo (los emojis y la jerga colombiana los
    captura mejor un léxico que un modelo entrenado en tweets genéricos).

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


# ── Léxicos (se escriben con o sin tilde; se normalizan al importar) ─────────
# Cada entrada: palabra o raíz. Raíces ≥5 letras hacen match por prefijo.

_LEX_RAW: dict[str, set[str]] = {
    "joy": {
        # ES
        "feliz", "felices", "felicidad", "alegr", "contento", "contenta", "contentos", "encant",
        "amo", "amor", "genial", "excelente", "increible", "maravill", "fantastic",
        "hermos", "brillante", "perfecto", "perfecta", "bueno", "buena", "buenisim",
        "gracias", "agradec", "orgull", "celebr", "felicit", "exito",
        "logro", "victoria", "gano", "ganamos", "bravo", "espectacular",
        "recomiend", "satisfech", "emocion", "ilusion", "esperanz", "disfrut",
        # jerga LatAm / Colombia
        "chevere", "bacan", "chimba", "berraquera", "melo", "brutal", "crack",
        "top", "lindo", "linda", "divin", "jaja", "jajaja", "jeje", "xd",
        # EN
        "happy", "glad", "love", "loved", "great", "awesome", "amazing",
        "excellent", "wonderful", "fantastic", "best", "good", "nice", "thanks",
        "thank", "proud", "excited", "enjoy", "beautiful", "perfect", "win",
        "winning", "lol", "haha", "yay", "congrat",
    },
    "anger": {
        # ES
        "enojad", "enoja", "rabia", "furios", "odio", "odia",
        "odiar", "odian", "indign", "harto", "harta", "jarto", "hartera",
        "cansad", "fastid", "molest", "asco", "asquer", "verguenza", "vergonz",
        "ladron", "ladrones", "rata", "ratas", "corrupt", "estafa", "estafador",
        "robo", "robar", "roban", "mentir", "mentiros", "mentira", "abuso",
        "pesimo", "pesima", "horrible", "terrible", "basura", "porqueria",
        "inutil", "incompetent", "descarad", "sinverguenz", "cinic", "burla",
        "exijo", "exigimos", "renuncie", "protest",
        # insultos / jerga Colombia
        "hp", "hijueputa", "malparid", "gonorrea", "piedra", "emberracad",
        "mierda", "maldit", "idiota", "imbecil", "estupid", "payaso", "bruto",
        "bruta",
        # EN
        "angry", "anger", "mad", "furious", "rage", "hate", "hated", "pissed",
        "annoy", "outrage", "disgust", "disgusting", "sick", "scam", "fraud",
        "liar", "lie", "lies", "corrupt", "awful", "worst", "trash", "garbage",
        "stupid", "idiot", "pathetic", "ridiculous", "wtf", "shame",
    },
    "sadness": {
        # ES
        "triste", "tristeza", "entristec", "lament",
        "llora", "lloro", "llorar", "llorando", "dolor", "duele", "doloros", "deprim", "depresion", "decepcion",
        "decepcionad", "desilusion", "desanim", "perdimos", "perdida",
        "luto", "fallec", "murio", "muerte", "tragedia", "tragic", "sufre",
        "sufrir", "sufriendo", "soledad", "desesper", "rip", "guayabo", "achicopal",
        # EN
        "sad", "sadly", "sadness", "cry", "crying", "tears", "heartbroken",
        "depress", "disappoint", "miss", "lonely", "grief", "tragic",
        "unfortunately", "sorry", "loss", "died", "death",
    },
    "fear": {
        # ES
        "miedo", "temor", "asust", "susto", "panico", "aterr",
        "preocup", "angusti", "ansied", "ansios", "nervios", "insegur",
        "peligr", "riesgo", "amenaz", "alarm", "incertidumbre", "crisis",
        "colaps", "quiebra", "inflacion", "desempleo", "violencia",
        # EN
        "fear", "afraid", "scared", "scary", "terrified", "panic", "worried",
        "worry", "anxious", "anxiety", "nervous", "danger", "dangerous",
        "threat", "risk", "risky", "uncertain", "crisis", "collapse",
    },
}

# Evaluaciones positivas/negativas sin emoción específica: se asignan a
# alegría (positivas) o se reparten entre enojo/tristeza (negativas).
_NEG_GENERIC_RAW = {
    "malo", "mala", "malos", "malas", "mal", "peor", "peores", "fracaso", "fracas", "desastre", "error",
    "fallo", "falla", "problema", "caro", "carisimo", "lento", "bad", "poor",
    "fail", "failure", "broken", "problem", "expensive", "slow", "sucks",
}

_NEGATIONS_RAW = {
    "no", "ni", "nunca", "jamas", "tampoco", "sin", "nada", "not", "never",
    "no", "dont", "don", "isnt", "wasnt", "aint", "cant", "nobody", "without",
}

_INTENSIFIERS_RAW = {
    "muy", "demasiado", "super", "re", "tan", "tanto", "bastante", "sumamente",
    "extremadamente", "totalmente", "absolutamente", "completamente", "mega",
    "very", "so", "really", "extremely", "totally", "absolutely", "too",
}

# Emojis → emoción (peso fuerte: en comentarios son muy explícitos)
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


def _norm_set(words: set[str]) -> set[str]:
    return {normalize(w) for w in words}


LEXICON: dict[str, set[str]] = {k: _norm_set(v) for k, v in _LEX_RAW.items()}
NEG_GENERIC = _norm_set(_NEG_GENERIC_RAW)
NEGATIONS = _norm_set(_NEGATIONS_RAW)
INTENSIFIERS = _norm_set(_INTENSIFIERS_RAW)

# Separar exactas vs. raíces (prefijo) para matching rápido
_EXACT: dict[str, set[str]] = {k: {w for w in v if len(w) < 5} for k, v in LEXICON.items()}
_STEMS: dict[str, tuple[str, ...]] = {
    k: tuple(sorted(w for w in v if len(w) >= 5)) for k, v in LEXICON.items()
}
_NEG_EXACT = {w for w in NEG_GENERIC if len(w) < 5}
_NEG_STEMS = tuple(sorted(w for w in NEG_GENERIC if len(w) >= 5))


def _match(token: str, exact: set[str], stems: tuple[str, ...]) -> bool:
    if token in exact:
        return True
    return any(token.startswith(s) for s in stems)


def _token_emotion(token: str) -> str | None:
    """Emoción léxica de un token (o 'neg' genérico, o None)."""
    for emo in NEGATIVE_EMOTIONS + ("joy",):
        if _match(token, _EXACT[emo], _STEMS[emo]):
            return emo
    if _match(token, _NEG_EXACT, _NEG_STEMS):
        return "neg"
    return None


@dataclass
class EmotionResult:
    distribution: dict[str, float]
    dominant: str
    intensity: float          # 0–1: fuerza de la emoción no neutral
    polarity: float           # −1 (muy negativo) … +1 (muy positivo)
    hits: dict[str, float] = field(default_factory=dict)
    emojis: int = 0


def dominant_of(dist: dict[str, float], min_emotion: float = 0.45) -> str:
    """Emoción dominante: la mayor no-neutral si la carga emocional ≥ umbral."""
    if 1.0 - dist.get("neutral", 0.0) < min_emotion:
        return "neutral"
    return max(NEGATIVE_EMOTIONS + ("joy",), key=lambda e: dist.get(e, 0.0))


def analyze_text(text: str) -> EmotionResult:
    """Distribución de emociones de un texto (sin modelos, determinista)."""
    raw = text or ""
    tokens = tokenize(raw)
    scores = {"joy": 0.0, "anger": 0.0, "sadness": 0.0, "fear": 0.0}

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
        emo = _token_emotion(tok)
        if emo is None:
            continue
        weight = 1.0
        window = tokens[max(0, i - 3):i]
        if any(w in INTENSIFIERS for w in window):
            weight *= 1.5
        negated = any(w in NEGATIONS for w in window)

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
        return EmotionResult(dist, "neutral", 0.0, 0.0, {}, emoji_count)

    # Neutral decrece con la evidencia: 1 pista → 0.5, 2 → 0.33, 4 → 0.2
    neutral = 1.0 / (1.0 + total)
    dist = {k: (v / total) * (1.0 - neutral) for k, v in scores.items()}
    dist["neutral"] = neutral
    dist = {k: round(v, 4) for k, v in dist.items()}
    dominant = dominant_of(dist)
    neg = dist["anger"] + dist["sadness"] + dist["fear"]
    polarity = round(dist["joy"] - neg, 4)
    intensity = round(1.0 - neutral, 4)
    return EmotionResult(dist, dominant, intensity, polarity, scores, emoji_count)


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
