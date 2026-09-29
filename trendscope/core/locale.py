"""País → idioma: una sola tabla para que TrendScope funcione en cualquier país.

Se usa para elegir la edición de Google News, el idioma de YouTube, los
paquetes de léxico (jerga regional) y el idioma de los textos del índice.
Países que no están en la tabla usan inglés.
"""

from __future__ import annotations

_SPANISH = "AR BO CL CO CR CU DO EC ES GQ GT HN MX NI PA PE PR PY SV UY VE"
_PORTUGUESE = "BR PT AO MZ CV"
_FRENCH = "FR BE LU MC SN CI CM ML BF NE TG BJ GA CD CG HT"
_GERMAN = "DE AT CH LI"
_ITALIAN = "IT SM VA"

COUNTRY_LANG: dict[str, str] = {}
for _codes, _lang in (
    (_SPANISH, "es"), (_PORTUGUESE, "pt"), (_FRENCH, "fr"),
    (_GERMAN, "de"), (_ITALIAN, "it"),
):
    for _cc in _codes.split():
        COUNTRY_LANG[_cc] = _lang

SUPPORTED_LANGS = ("es", "en", "pt", "fr", "de", "it")
# Idiomas con textos de interfaz/índice traducidos (el resto usa inglés)
UI_LANGS = ("es", "en", "pt")


def country(geo: str | None) -> str:
    g = (geo or "").strip().upper()
    return g if len(g) == 2 and g.isalpha() else "US"


def language_for(geo: str | None) -> str:
    return COUNTRY_LANG.get(country(geo), "en")


def ui_language(lang: str | None = None, geo: str | None = None) -> str:
    """Idioma para textos generados: el pedido si está traducido, si no el del país."""
    if lang:
        base = lang.lower().split("-")[0]
        if base in UI_LANGS:
            return base
    base = language_for(geo)
    return base if base in UI_LANGS else "en"


def google_news_edition(geo: str | None) -> dict[str, str]:
    """Parámetros hl / gl / ceid de Google News para el país."""
    cc = country(geo)
    lang = language_for(cc)
    if lang == "es":
        if cc == "ES":
            return {"hl": "es", "gl": cc, "ceid": f"{cc}:es"}
        return {"hl": "es-419", "gl": cc, "ceid": f"{cc}:es-419"}
    if lang == "pt":
        if cc == "BR":
            return {"hl": "pt-BR", "gl": cc, "ceid": "BR:pt-419"}
        return {"hl": "pt-PT", "gl": cc, "ceid": f"{cc}:pt-150"}
    if lang == "en":
        return {"hl": f"en-{cc}", "gl": cc, "ceid": f"{cc}:en"}
    return {"hl": lang, "gl": cc, "ceid": f"{cc}:{lang}"}


def youtube_client(geo: str | None) -> dict[str, str]:
    cc = country(geo)
    return {"hl": language_for(cc), "gl": cc}


# Subreddits de conversación local por país (opiniones en el idioma del país)
COUNTRY_SUBREDDITS: dict[str, list[str]] = {
    "CO": ["Colombia"], "MX": ["mexico"], "AR": ["argentina"], "CL": ["chile"],
    "PE": ["PERU"], "VE": ["vzla"], "EC": ["ecuador"], "UY": ["uruguay"],
    "BO": ["BOLIVIA"], "PY": ["Paraguay"], "CR": ["costa_rica"], "DO": ["Dominican"],
    "GT": ["guatemala"], "ES": ["spain", "es"], "BR": ["brasil"], "PT": ["portugal"],
    "US": ["news"], "GB": ["unitedkingdom"], "CA": ["canada"], "AU": ["australia"],
    "IN": ["india"], "FR": ["france"], "DE": ["de"], "IT": ["italy"],
}


def country_subreddits(geo: str | None) -> list[str]:
    return COUNTRY_SUBREDDITS.get(country(geo), [])
