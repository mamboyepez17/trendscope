"""Stance toward the analyzed topic: support / against / mixed / unknown.

Heurística léxica ES/EN + señal del sentimiento del texto.
No es NLI perfecto; suficiente para dashboards de trend intel.
"""

from __future__ import annotations

from dataclasses import dataclass

# Verbos/adj que suelen indicar apoyo al sujeto del texto
_SUPPORT_ES = {
    "apoya", "apoyar", "apoyo", "respalda", "respaldo", "elogia", "elogio",
    "felicita", "felicidades", "reconoce", "reconocimiento", "defiende",
    "defensa", "elogiado", "destaca", "destacó", "impulsa", "impulso",
    "vota", "votará", "aprueba", "aprobación", "celebra", "celebración",
    "bravo", "excelente", "gran", "héroe", "heroe", "victoria", "ganó",
    "ganador", "mejor", "aplaude", "admiración", "admirado", "orgullo",
}

_AGAINST_ES = {
    "critica", "criticó", "criticar", "rechaza", "rechazo", "condena",
    "condena", "ataca", "ataque", "denuncia", "denuncia", "exige",
    "renuncia", "dimite", "dimisión", "fracaso", "fracasó", "mentiroso",
    "mentira", "corrupto", "corrupción", "desastre", "hundir", "hundió",
    "oposición", "opositor", "contra", "rechazó", "protesta", "protestan",
    "indigna", "indignación", "vergüenza", "penoso", "inútil", "inutil",
    "destituir", "destitución", "impugna", "impugnación", "fraude",
}

_SUPPORT_EN = {
    "supports", "support", "praises", "praise", "endorses", "endorse",
    "backs", "back", "defends", "defend", "celebrates", "celebrate",
    "applauds", "applaud", "wins", "win", "victory", "excellent", "great",
    "hero", "proud", "admire", "approval", "approves", "boost",
}

_AGAINST_EN = {
    "criticizes", "criticize", "criticism", "rejects", "reject",
    "condemns", "condemn", "attacks", "attack", "demands", "demand",
    "resign", "resignation", "failure", "failed", "liar", "lie",
    "corrupt", "corruption", "disaster", "protest", "protests",
    "outrage", "shame", "useless", "remove", "impeach", "scandal",
}

_NEGATION = {"no", "ni", "nunca", "jamás", "nunca", "not", "never", "without", "sin"}


@dataclass
class StanceResult:
    label: str  # support | against | mixed | unknown
    confidence: float
    support_hits: int
    against_hits: int


def _hits(text: str, lexicon: set[str]) -> int:
    words = set(text.lower().split())
    # También match simple de substrings para conjugaciones
    count = sum(1 for w in words if w in lexicon)
    # fallback substring para "criticó" vs "critica"
    for lex in lexicon:
        if len(lex) >= 5 and lex in text.lower() and lex not in words:
            count += 1
    return count


def analyze_stance(
    text: str,
    topic: str | None = None,
    sentiment_label: str | None = None,
) -> StanceResult:
    """Estima stance del texto hacia el tema (o sujeto principal)."""
    if not text or len(text.strip()) < 8:
        return StanceResult("unknown", 0.0, 0, 0)

    t = text.lower()
    sup = _hits(t, _SUPPORT_ES) + _hits(t, _SUPPORT_EN)
    ag = _hits(t, _AGAINST_ES) + _hits(t, _AGAINST_EN)

    # Negación simple: "no apoya" / "no apoyan" cuenta como against
    words = t.split()
    support_words = _SUPPORT_ES | _SUPPORT_EN
    against_words = _AGAINST_ES | _AGAINST_EN

    def _lex_match(word: str, lex: set[str]) -> bool:
        if word in lex:
            return True
        return any(len(root) >= 5 and root in word for root in lex)

    for i, w in enumerate(words):
        if w in _NEGATION and i + 1 < len(words):
            nxt = words[i + 1]
            if _lex_match(nxt, support_words):
                sup = max(0, sup - 1)
                ag += 1
            elif _lex_match(nxt, against_words):
                ag = max(0, ag - 1)
                sup += 1

    # Señal débil del sentimiento si el tema aparece en el texto
    if topic:
        topic_tokens = [x for x in topic.lower().split() if len(x) > 3]
        mentions_topic = any(tok in t for tok in topic_tokens) if topic_tokens else False
    else:
        mentions_topic = True

    if sup > ag:
        label = "support"
        conf = min(0.95, 0.55 + 0.15 * (sup - ag))
    elif ag > sup:
        label = "against"
        conf = min(0.95, 0.55 + 0.15 * (ag - sup))
    elif sup and ag:
        label = "mixed"
        conf = 0.5
    elif mentions_topic and sentiment_label == "positive":
        label = "support"
        conf = 0.4
    elif mentions_topic and sentiment_label == "negative":
        label = "against"
        conf = 0.4
    else:
        label = "unknown"
        conf = 0.0

    if not mentions_topic and label != "unknown":
        # baja confianza si no se menciona el tema
        conf = round(conf * 0.5, 3)

    return StanceResult(label, round(conf, 3), sup, ag)


def summarize_stances(items: list[dict]) -> dict:
    counts = {"support": 0, "against": 0, "mixed": 0, "unknown": 0}
    for item in items:
        lab = item.get("stance") or "unknown"
        if lab not in counts:
            lab = "unknown"
        counts[lab] += 1
    total = sum(counts.values()) or 1
    dominant = max(counts, key=counts.get)
    if counts["unknown"] == total:
        dominant = "unknown"
    return {
        **counts,
        "total": sum(counts.values()),
        "dominant": dominant,
        "support_ratio": round(counts["support"] / total, 3),
        "against_ratio": round(counts["against"] / total, 3),
    }


def enrich_stance(items: list[dict], topic: str | None) -> list[dict]:
    for item in items:
        text = (
            item.get("title")
            or item.get("text")
            or item.get("keyword")
            or ""
        )
        result = analyze_stance(
            text, topic=topic, sentiment_label=item.get("sentiment_label")
        )
        item["stance"] = result.label
        item["stance_confidence"] = result.confidence
    return items
