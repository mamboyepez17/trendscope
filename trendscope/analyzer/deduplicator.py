# analyzer/deduplicator.py
import hashlib
from difflib import SequenceMatcher

from loguru import logger


def _normalize_text(text: str) -> str:
    """Normaliza texto para comparacion: lowercase, sin espacios extra."""
    return " ".join(text.lower().split())


def _tokens(text: str) -> set[str]:
    return {t for t in _normalize_text(text).split() if len(t) > 2}


def _similarity(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (0.0 a 1.0)."""
    return SequenceMatcher(None, a, b).ratio()


def _text_hash(text: str) -> str:
    """Hash normalizado para deduplicacion exacta rapida."""
    return hashlib.md5(_normalize_text(text).encode()).hexdigest()


def deduplicate(items: list[dict], threshold: float = 0.72) -> list[dict]:
    """
    Elimina items con texto muy similar entre fuentes.
    Threshold 0.72 = 72% de similitud para considerar duplicado.
    Mantiene el primero.

    Optimizacion:
    1. Hash exacto O(1)
    2. Pre-filtro por tokens compartidos (evita SequenceMatcher O(n^2) completo)
    3. SequenceMatcher solo sobre candidatos que comparten >=2 tokens o longitud similar
    """
    seen_hashes: set[str] = set()
    seen_texts: list[str] = []
    seen_token_sets: list[set[str]] = []
    result: list[dict] = []

    for item in items:
        text = (
            item.get("title")
            or item.get("keyword")
            or item.get("text")
            or ""
        ).strip()

        if not text or len(text) < 3:
            continue

        normalized = _normalize_text(text)
        h = _text_hash(text)

        if h in seen_hashes:
            continue

        tokens = _tokens(normalized)
        is_duplicate = False

        # Solo comparar SequenceMatcher contra candidatos plausibles
        for i, prev in enumerate(seen_texts):
            prev_tokens = seen_token_sets[i]
            if tokens and prev_tokens:
                shared = len(tokens & prev_tokens)
                # Necesitan overlap real; si no, saltar SequenceMatcher
                if shared < 2:
                    # Length filter: textos muy distintos en longitud rara vez son dups
                    if abs(len(normalized) - len(prev)) > max(len(normalized), len(prev)) * 0.5:
                        continue
            if _similarity(normalized, prev) > threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            seen_hashes.add(h)
            seen_texts.append(normalized)
            seen_token_sets.append(tokens)
            result.append(item)

    removed = len(items) - len(result)
    if removed > 0:
        logger.info(f"Deduplicacion: {removed} duplicados removidos -> {len(result)} unicos")
    else:
        logger.info(f"Deduplicacion: 0 duplicados, {len(result)} items unicos")
    return result
