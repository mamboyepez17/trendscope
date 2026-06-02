# analyzer/deduplicator.py
from difflib import SequenceMatcher

from loguru import logger


def _similarity(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (0.0 a 1.0)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(items: list[dict], threshold: float = 0.72) -> list[dict]:
    """
    Elimina items con texto muy similar entre fuentes.
    Threshold 0.72 = 72% de similitud para considerar duplicado.
    Mantiene el primero (mayor score al llegar ordenado por fuente).
    """
    seen: list[str] = []
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

        is_duplicate = any(_similarity(text, s) > threshold for s in seen)
        if not is_duplicate:
            seen.append(text)
            result.append(item)

    removed = len(items) - len(result)
    if removed > 0:
        logger.info(f"Deduplicacion: {removed} duplicados removidos -> {len(result)} unicos")
    else:
        logger.info(f"Deduplicacion: 0 duplicados, {len(result)} items unicos")
    return result
