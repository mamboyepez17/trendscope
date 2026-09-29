"""Utilidades de texto compartidas: tokens del tema y menciones por palabra."""

from __future__ import annotations

from trendscope.sentiment.emotions import tokenize

_TOPIC_STOP = {"de", "del", "la", "el", "los", "las", "en", "y", "the", "of", "and", "in"}


def topic_tokens(topic: str | None) -> list[str]:
    """Tokens significativos del tema (sin tildes).

    Prefiere palabras de >3 letras; si el tema solo tiene palabras cortas
    ("IA", "5G", "ONU") usa esas mismas.
    """
    toks = [t for t in tokenize(topic or "") if t not in _TOPIC_STOP]
    long_toks = [t for t in toks if len(t) > 3]
    return long_toks or toks


def _hit(tok: str, words: list[str]) -> bool:
    return any(w == tok or (len(tok) >= 5 and w.startswith(tok)) for w in words)


def mentions_count(text: str, tokens: list[str]) -> int:
    """Cuántos tokens distintos del tema aparecen en el texto."""
    words = tokenize(text)
    return sum(1 for tok in set(tokens) if _hit(tok, words))


def mentions(text: str, tokens: list[str]) -> bool:
    """¿El texto menciona algún token? Palabra completa; ≥5 letras admite
    variantes por prefijo (colombia → colombiano). Nunca subcadenas internas:
    "ia" no coincide con "Colombia"."""
    if not tokens:
        return False
    words = tokenize(text)
    for tok in tokens:
        for w in words:
            if w == tok or (len(tok) >= 5 and w.startswith(tok)):
                return True
    return False
