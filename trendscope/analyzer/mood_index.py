"""Índice de Ánimo — cómo se siente la GENTE frente a un tema.

El medidor sale de lo que opina la gente (comentarios, respuestas, posts
sociales), no de titulares de prensa. Los titulares se reportan aparte como
"tono de medios".

Algoritmo (por cada opinión i):
  1. Emociones: distribución sobre alegría/enojo/tristeza/miedo/neutral
     (modelo + léxico + emojis, ver ``sentiment/emotions.py``).
  2. Polaridad p_i ∈ [−1, 1]: alegría − (enojo + tristeza + miedo), mezclada
     con el sentimiento del modelo cuando existe.
  3. Peso w_i = tipo × engagement × autor × calidad
       - tipo: comentario 1.0 · post social 0.7 · noticias 0 (excluidas)
       - engagement: 1 + min(3, log10(1 + likes)) → un comentario viral pesa
         hasta 4×, nunca 1000×
       - autor: 1 / (nº de opiniones del mismo autor) → una cuenta = un voto
       - calidad: textos de < 3 palabras sin emoji pesan la mitad

Agregados:
  - Emociones (%) = Σ w_i·dist_i / Σ w_i
  - Índice neto (−100…+100) = 100 · Σ w_i·p_i / Σ w_i
  - Margen ±95%: 1.96 · √(var_w / n_eff), n_eff = (Σw)² / Σw²
  - Polarización (0–1): cuánto conviven opiniones muy positivas y muy negativas
  - Ánimo: Contentos / Enojados / Tristes / Preocupados / Divididos / Neutrales
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

from trendscope.sentiment.emotions import EMOTIONS, NEGATIVE_EMOTIONS, normalize, tokenize

COMMENT_SOURCES = {
    "reddit_comment", "hackernews_comment", "twitter_comment", "x_reply",
    "youtube_comment", "bluesky_reply",
}
SOCIAL_POST_SOURCES = {"twitter", "tweetclaw", "bluesky", "reddit"}
NEWS_SOURCES = {"google_news", "bing_news", "gdelt"}

MOOD_EMOJI = {
    "happy": "😊", "angry": "😠", "sad": "😢", "afraid": "😨",
    "divided": "⚖️", "neutral": "😐", "quiet": "😶",
}

# Textos por idioma (es / en / pt). Idiomas sin traducción usan inglés.
TEXTS: dict[str, dict] = {
    "es": {
        "moods": {
            "happy": ("Contentos", "La gente habla con alegría y aprobación"),
            "angry": ("Enojados", "Predomina el enojo, la indignación o el rechazo"),
            "sad": ("Tristes", "Predomina la tristeza, la decepción o el pesar"),
            "afraid": ("Preocupados", "Predomina el miedo o la incertidumbre"),
            "divided": ("Divididos", "Opiniones fuertes a favor y en contra a la vez"),
            "neutral": ("Neutrales", "Conversación informativa, sin emoción marcada"),
            "quiet": ("Sin datos", "No hay suficientes opiniones para medir"),
        },
        "emotions": {"joy": "alegría", "anger": "enojo", "sadness": "tristeza",
                     "fear": "miedo", "neutral": "neutral"},
        "adj": {"happy": "contenta", "angry": "enojada", "sad": "triste", "afraid": "preocupada"},
        "the_topic": "el tema",
        "empty": "Aún no hay opiniones suficientes para medir el ánimo.",
        "quiet": "Todavía hay muy pocas opiniones sobre {t} para medir el ánimo.",
        "base": "Índice neto {net} (±{m}) con {n} opiniones de {s} fuente(s).",
        "neutral": "La gente habla de {t} sin emoción marcada ({p}% neutral). {base}",
        "divided": "La opinión sobre {t} está dividida: {joy}% alegría vs {neg}% emociones negativas. {base}",
        "mood": "La gente se siente mayormente {adj} con {t} ({p}% {emo}). {base}",
    },
    "en": {
        "moods": {
            "happy": ("Happy", "People talk with joy and approval"),
            "angry": ("Angry", "Anger, outrage or rejection dominate"),
            "sad": ("Sad", "Sadness, disappointment or grief dominate"),
            "afraid": ("Worried", "Fear or uncertainty dominate"),
            "divided": ("Divided", "Strong opinions for and against at the same time"),
            "neutral": ("Neutral", "Informative conversation, no strong emotion"),
            "quiet": ("No data", "Not enough opinions to measure"),
        },
        "emotions": {"joy": "joy", "anger": "anger", "sadness": "sadness",
                     "fear": "fear", "neutral": "neutral"},
        "adj": {"happy": "happy", "angry": "angry", "sad": "sad", "afraid": "worried"},
        "the_topic": "the topic",
        "empty": "Not enough opinions yet to measure the mood.",
        "quiet": "There are still very few opinions about {t} to measure the mood.",
        "base": "Net index {net} (±{m}) from {n} opinions across {s} source(s).",
        "neutral": "People talk about {t} without strong emotion ({p}% neutral). {base}",
        "divided": "Opinion on {t} is divided: {joy}% joy vs {neg}% negative emotions. {base}",
        "mood": "People feel mostly {adj} about {t} ({p}% {emo}). {base}",
    },
    "pt": {
        "moods": {
            "happy": ("Contentes", "As pessoas falam com alegria e aprovação"),
            "angry": ("Irritados", "Predominam a raiva, a indignação ou a rejeição"),
            "sad": ("Tristes", "Predominam a tristeza, a decepção ou o pesar"),
            "afraid": ("Preocupados", "Predominam o medo ou a incerteza"),
            "divided": ("Divididos", "Opiniões fortes a favor e contra ao mesmo tempo"),
            "neutral": ("Neutros", "Conversa informativa, sem emoção marcante"),
            "quiet": ("Sem dados", "Não há opiniões suficientes para medir"),
        },
        "emotions": {"joy": "alegria", "anger": "raiva", "sadness": "tristeza",
                     "fear": "medo", "neutral": "neutro"},
        "adj": {"happy": "contentes", "angry": "irritadas", "sad": "tristes", "afraid": "preocupadas"},
        "the_topic": "o tema",
        "empty": "Ainda não há opiniões suficientes para medir o humor.",
        "quiet": "Ainda há muito poucas opiniões sobre {t} para medir o humor.",
        "base": "Índice líquido {net} (±{m}) com {n} opiniões de {s} fonte(s).",
        "neutral": "As pessoas falam de {t} sem emoção marcante ({p}% neutro). {base}",
        "divided": "A opinião sobre {t} está dividida: {joy}% alegria vs {neg}% emoções negativas. {base}",
        "mood": "As pessoas estão principalmente {adj} com {t} ({p}% {emo}). {base}",
    },
}


def _texts(lang: str | None) -> dict:
    return TEXTS.get((lang or "es").lower().split("-")[0], TEXTS["en"])


# Compatibilidad: etiquetas en español (antes MOODS / EMOTION_LABELS_ES)
MOODS: dict[str, tuple[str, str, str]] = {
    k: (MOOD_EMOJI[k], *v) for k, v in TEXTS["es"]["moods"].items()
}
EMOTION_LABELS_ES = {k: v.capitalize() for k, v in TEXTS["es"]["emotions"].items()}

_EMOTION_TO_MOOD = {"joy": "happy", "anger": "angry", "sadness": "sad", "fear": "afraid"}

_STOPWORDS = set(
    normalize(w) for w in """
    el la los las un una unos unas de del al a en y o u que se su sus por para con
    sin sobre como mas pero es son fue ser esta este esto estos estas eso esa ese
    lo le les me mi mis te tu tus nos ya muy hay han ha he tiene tienen tener
    todo todos toda todas cuando donde quien porque pues asi tambien solo ahora
    hoy ayer va van vamos ir hace hacer bien mal si no ni the and for that this
    with are was were have has had you your they them their its it's not but
    what who how can will just from about all out more one would there been
    https http www com html amp quot gt lt
    """.split()
)


def is_opinion(item: dict) -> bool:
    return _type_weight(item) > 0


def _type_weight(item: dict) -> float:
    src = (item.get("source") or "").lower()
    kind = (item.get("kind") or "").lower()
    if src in NEWS_SOURCES:
        return 0.0
    if kind == "comment" or src in COMMENT_SOURCES:
        return 1.0
    if src in SOCIAL_POST_SOURCES:
        return 0.7
    return 0.0


def _engagement(item: dict) -> float:
    raw = 0.0
    for key in ("likes", "score", "points", "reposts", "retweets"):
        try:
            raw = max(raw, float(item.get(key) or 0))
        except (TypeError, ValueError):
            continue
    return 1.0 + min(3.0, math.log10(1.0 + max(0.0, raw)))


def _text(item: dict) -> str:
    return (item.get("text") or item.get("title") or "").strip()


def _item_dist(item: dict) -> dict[str, float]:
    dist = item.get("emotion_dist")
    if isinstance(dist, dict) and dist:
        return {e: float(dist.get(e, 0.0)) for e in EMOTIONS}
    # Ítem sin enriquecer: calcular al vuelo
    from trendscope.sentiment.emotions import analyze_text

    return analyze_text(_text(item)).distribution


def _item_polarity(item: dict, dist: dict[str, float]) -> float:
    if isinstance(item.get("polarity"), (int, float)):
        return max(-1.0, min(1.0, float(item["polarity"])))
    return dist.get("joy", 0.0) - sum(dist.get(e, 0.0) for e in NEGATIVE_EMOTIONS)


def _weights(items: list[dict]) -> list[float]:
    by_author = Counter(
        (i.get("author") or "").strip().lower() for i in items if (i.get("author") or "").strip()
    )
    out = []
    for it in items:
        w = _type_weight(it) * _engagement(it)
        author = (it.get("author") or "").strip().lower()
        if author and by_author[author] > 1:
            w /= by_author[author]
        txt = _text(it)
        if len(txt.split()) < 3 and not re.search(r"[^\w\s,.;:!?¿¡'\"()-]", txt):
            w *= 0.5
        out.append(w)
    return out


def _drivers(texts_by_emotion: dict[str, list[str]], all_texts: list[str],
             topic: str | None, limit: int = 5) -> dict[str, list[str]]:
    """Palabras que más distinguen a cada emoción (lift vs. el total)."""
    topic_toks = set(tokenize(topic or ""))
    total = Counter()
    for t in all_texts:
        total.update(set(tokenize(t)))
    n_all = max(1, len(all_texts))
    out: dict[str, list[str]] = {}
    for emo, texts in texts_by_emotion.items():
        if not texts:
            continue
        cnt = Counter()
        for t in texts:
            cnt.update(set(tokenize(t)))
        n = len(texts)
        scored = []
        for tok, c in cnt.items():
            if c < 2 or len(tok) < 4 or tok in _STOPWORDS or tok in topic_toks or tok.isdigit():
                continue
            lift = (c / n) / (total[tok] / n_all)
            scored.append((lift * math.log1p(c), tok))
        scored.sort(reverse=True)
        out[emo] = [tok for _, tok in scored[:limit]]
    return out


def compute_mood_index(items: list[dict], topic: str | None = None,
                       quotes_per_emotion: int = 2, lang: str = "es") -> dict:
    """Agrega las opiniones en un Índice de Ánimo serializable a JSON.

    lang: idioma de las etiquetas y del titular (es / en / pt; otros → en).
    """
    tx = _texts(lang)
    opinions = [i for i in items if is_opinion(i) and len(_text(i)) >= 3]
    weights = _weights(opinions)
    pairs = [(it, w) for it, w in zip(opinions, weights) if w > 0]

    if not pairs:
        label, desc = tx["moods"]["quiet"]
        return {
            "mood": "quiet", "emoji": MOOD_EMOJI["quiet"], "label": label, "description": desc,
            "net_score": 0.0, "margin": None, "confidence": "low",
            "sample_size": 0, "effective_n": 0.0, "authors": 0,
            "emotions": {e: 0.0 for e in EMOTIONS}, "dominant_emotion": "neutral",
            "polarization": 0.0, "intensity": 0.0, "by_source": {},
            "quotes": {}, "drivers": {}, "headline": tx["empty"], "lang": lang,
            "method": "mood_index_v1",
        }

    sum_w = sum(w for _, w in pairs)
    sum_w2 = sum(w * w for _, w in pairs)
    n_eff = (sum_w ** 2) / sum_w2 if sum_w2 else 0.0

    emo_acc = defaultdict(float)
    pols: list[tuple[float, float]] = []
    by_source: dict[str, dict] = defaultdict(lambda: {"n": 0, "w": 0.0, "pol": 0.0})
    per_item = []
    for it, w in pairs:
        dist = _item_dist(it)
        pol = _item_polarity(it, dist)
        for e in EMOTIONS:
            emo_acc[e] += w * dist.get(e, 0.0)
        pols.append((pol, w))
        src = it.get("source") or "otro"
        by_source[src]["n"] += 1
        by_source[src]["w"] += w
        by_source[src]["pol"] += w * pol
        per_item.append((it, w, dist, pol))

    emotions = {e: round(emo_acc[e] / sum_w, 4) for e in EMOTIONS}
    mean_pol = sum(p * w for p, w in pols) / sum_w
    var = sum(w * (p - mean_pol) ** 2 for p, w in pols) / sum_w
    se = math.sqrt(var / n_eff) if n_eff > 1 else 1.0
    net = round(100 * mean_pol, 1)
    margin = round(min(100.0, 196 * se), 1)

    strong_pos = sum(w for p, w in pols if p >= 0.3) / sum_w
    strong_neg = sum(w for p, w in pols if p <= -0.3) / sum_w
    # 0 = todos opinan igual · 1 = mitad muy a favor, mitad muy en contra
    polarization = round(min(1.0, 2 * min(strong_pos, strong_neg)), 3)
    intensity = round(1.0 - emotions["neutral"], 3)

    # Ánimo: el signo del índice manda. Con índice negativo la etiqueta es la
    # emoción negativa dominante (aunque la alegría sola sea la mayor
    # porción, las negativas juntas pesan más).
    neg_share = sum(emotions[e] for e in NEGATIVE_EMOTIONS)
    top_neg = max(NEGATIVE_EMOTIONS, key=lambda e: emotions[e])
    if len(pairs) < 3:
        mood = "quiet"
    elif intensity < 0.25:
        mood = "neutral"
    elif (abs(net) < 15 and emotions["joy"] >= 0.15 and neg_share >= 0.15
          and min(emotions["joy"], neg_share) >= 0.6 * max(emotions["joy"], neg_share)):
        mood = "divided"
    elif net < 0 or (net < 15 and neg_share > emotions["joy"]):
        mood = _EMOTION_TO_MOOD[top_neg]
    else:
        mood = "happy"
    top_emo = {"happy": "joy", "angry": "anger", "sad": "sadness", "afraid": "fear"}.get(mood, "neutral")

    if n_eff >= 50 and margin <= 15:
        confidence = "high"
    elif n_eff >= 15 and margin <= 30:
        confidence = "medium"
    else:
        confidence = "low"

    # Citas representativas y "de qué hablan" por emoción
    quotes: dict[str, list[dict]] = {}
    texts_by_emo: dict[str, list[str]] = defaultdict(list)
    for emo in ("joy",) + NEGATIVE_EMOTIONS:
        ranked = sorted(
            (x for x in per_item if max(x[2], key=x[2].get) == emo or
             (x[2].get(emo, 0) >= 0.3 and x[2].get("neutral", 1) < 0.6)),
            key=lambda x: x[1] * x[2].get(emo, 0.0),
            reverse=True,
        )
        texts_by_emo[emo] = [_text(x[0]) for x in ranked]
        seen: set[str] = set()
        picked = []
        for it, w, dist, pol in ranked:
            txt = re.sub(r"\s+", " ", _text(it))[:220]
            key = normalize(txt)[:60]
            if key in seen:
                continue
            seen.add(key)
            picked.append({
                "text": txt,
                "source": it.get("source"),
                "author": it.get("author") or "",
                "url": it.get("permalink") or it.get("url") or "",
                "weight": round(w, 2),
                "strength": round(dist.get(emo, 0.0), 2),
            })
            if len(picked) >= quotes_per_emotion:
                break
        if picked:
            quotes[emo] = picked

    drivers = _drivers(texts_by_emo, [_text(x[0]) for x in per_item], topic)

    src_out = {
        s: {"n": v["n"], "net_score": round(100 * v["pol"] / v["w"], 1) if v["w"] else 0.0}
        for s, v in sorted(by_source.items(), key=lambda kv: -kv[1]["n"])
    }
    authors = len({(it.get("author") or "").lower() for it, *_ in per_item if it.get("author")})

    label, desc = tx["moods"][mood]
    emoji = MOOD_EMOJI[mood]
    headline = _headline(tx, mood, emotions, net, margin, len(pairs), len(src_out), topic)

    return {
        "mood": mood,
        "emoji": emoji,
        "label": label,
        "description": desc,
        "net_score": net,
        "margin": margin,
        "confidence": confidence,
        "sample_size": len(pairs),
        "effective_n": round(n_eff, 1),
        "authors": authors,
        "emotions": emotions,
        "dominant_emotion": top_emo,
        "polarization": polarization,
        "intensity": intensity,
        "by_source": src_out,
        "quotes": quotes,
        "drivers": drivers,
        "headline": headline,
        "method": "mood_index_v1",
        "lang": lang,
    }


def _headline(tx: dict, mood: str, emotions: dict, net: float, margin: float,
              n: int, n_sources: int, topic: str | None) -> str:
    t = f"«{topic}»" if topic else tx["the_topic"]
    if mood == "quiet":
        return tx["quiet"].format(t=t)
    pct = {e: round(100 * v) for e, v in emotions.items()}
    base = tx["base"].format(
        net=f"{'+' if net > 0 else ''}{net:.0f}", m=f"{margin:.0f}", n=n, s=n_sources
    )
    if mood == "neutral":
        return tx["neutral"].format(t=t, p=pct["neutral"], base=base)
    if mood == "divided":
        neg = pct["anger"] + pct["sadness"] + pct["fear"]
        return tx["divided"].format(t=t, joy=pct["joy"], neg=neg, base=base)
    emo = {"happy": "joy", "angry": "anger", "sad": "sadness", "afraid": "fear"}[mood]
    return tx["mood"].format(adj=tx["adj"][mood], t=t, p=pct[emo], emo=tx["emotions"][emo], base=base)


def media_tone(items: list[dict]) -> dict:
    """Tono de los titulares de prensa (separado del ánimo de la gente)."""
    news = [i for i in items if (i.get("source") or "") in NEWS_SOURCES]
    if not news:
        return {"n": 0, "net_score": 0.0, "label": "sin noticias"}
    pols = []
    for it in news:
        dist = _item_dist(it)
        pols.append(_item_polarity(it, dist))
    net = round(100 * sum(pols) / len(pols), 1)
    label = "positivo" if net >= 10 else "negativo" if net <= -10 else "neutral"
    return {"n": len(news), "net_score": net, "label": label}


def overall_label(net_score: float, threshold: float = 10.0) -> str:
    if net_score >= threshold:
        return "positive"
    if net_score <= -threshold:
        return "negative"
    return "neutral"
