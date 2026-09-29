"""Paquetes de léxico: idioma base + jerga del país + léxico propio (JSON).

    pack = BASE[idioma] ∪ BASE["en"] (préstamos de internet)
           ∪ REGIONAL[país] (si el país habla ese idioma)
           ∪ léxico propio de CUSTOM_LEXICON_PATH

Formato del JSON propio (todas las claves opcionales):

    {
      "*":  {"joy": ["..."], "anger": [...], "sadness": [...], "fear": [...],
             "neg": [...], "negations": [...], "intensifiers": [...]},
      "es": {...},          # solo para textos en español
      "CO": {...}           # solo cuando el país del análisis es CO
    }
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from loguru import logger

from trendscope.sentiment.lexicons.base import BASE
from trendscope.sentiment.lexicons.regional import REGIONAL

CATEGORIES = ("joy", "anger", "sadness", "fear", "neg", "negations", "intensifiers")


def _normalize(word: str) -> str:
    from trendscope.sentiment.emotions import normalize

    return normalize(word).strip()


def _merge(dst: dict[str, set[str]], src: dict) -> None:
    for cat in CATEGORIES:
        for w in src.get(cat, ()) or ():
            n = _normalize(str(w))
            if n:
                dst[cat].add(n)


@lru_cache(maxsize=8)
def _custom() -> dict:
    try:
        from trendscope.settings import settings

        path = getattr(settings, "custom_lexicon_path", "") or ""
    except Exception:
        path = ""
    if not path:
        return {}
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"Léxico propio ({path}) no se pudo leer: {e}")
        return {}


@lru_cache(maxsize=128)
def build_pack(lang: str, geo: str | None = None) -> dict[str, frozenset[str]]:
    from trendscope.core.locale import country, language_for

    lang = lang if lang in BASE else "en"
    pack: dict[str, set[str]] = {cat: set() for cat in CATEGORIES}
    _merge(pack, BASE[lang])
    if lang != "en":
        _merge(pack, {k: v for k, v in BASE["en"].items() if k not in ("negations", "intensifiers")})
    cc = country(geo) if geo else None
    if cc and cc in REGIONAL and language_for(cc) == lang:
        _merge(pack, REGIONAL[cc])
    custom = _custom()
    for key in ("*", lang, cc or ""):
        if key and isinstance(custom.get(key), dict):
            _merge(pack, custom[key])
    return {k: frozenset(v) for k, v in pack.items()}


def clear_cache() -> None:
    build_pack.cache_clear()
    _custom.cache_clear()
