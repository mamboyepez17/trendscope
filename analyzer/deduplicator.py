# analyzer/deduplicator.py
import hashlib
from difflib import SequenceMatcher

from loguru import logger


def _normalize_text(text: str) -> str:
    """Normaliza texto para comparacion: lowercase, sin espacios extra."""
    return " ".join(text.lower().split())


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
    Mantiene el primero (mayor score al llegar ordenado por fuente).

    Optimizacion: primero checa hash exacto (O(1)), luego similarity (O(n)).
    """
    seen_hashes: set[str] = set()
    seen_texts: list[str] = []
    result: list[dict] = []

    for item in items:
        text = (
            item.get("title") or
            item.get("keyword") or
            item.get("text") or
            ""
        ).strip()

        if not text or len(text) < 3:
            continue

        normalized = _normalize_text(text)
        h = _text_hash(text)

        # Check exacto primero (rapido)
        if h in seen_hashes:
            continue

        # Check por similitud (mas lento pero necesario para near-duplicates)
        is_duplicate = any(_similarity(normalized, s) > threshold for s in seen_texts)
        if not is_duplicate:
            seen_hashes.add(h)
            seen_texts.append(normalized)
            result.append(item)

    removed = len(items) - len(result)
    if removed > 0:
        logger.info(f"Deduplicacion: {removed} duplicados removidos -> {len(result)} unicos")
    else:
        logger.info(f"Deduplicacion: 0 duplicados, {len(result)} items unicos")
    return result
