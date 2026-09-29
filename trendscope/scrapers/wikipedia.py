"""Wikipedia search in the country's language — free, no API key."""

from __future__ import annotations

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery



def wiki_lang(query: TrendQuery) -> str:
    """Idioma de Wikipedia: el pedido (lang) o el del país; antes era siempre 'es'."""
    from trendscope.core.locale import SUPPORTED_LANGS, language_for

    lang = (query.lang or "").lower()
    return lang if lang in SUPPORTED_LANGS else language_for(query.geo)


def run(query: TrendQuery) -> list[dict]:
    session = get_session()
    base = f"https://{wiki_lang(query)}.wikipedia.org"
    results: list[dict] = []
    # Solo el keyword principal (Wikipedia no necesita 3 variantes)
    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []
    try:
        resp = session.get(
            f"{base}/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": keyword,
                "srlimit": 5,
                "format": "json",
                "utf8": 1,
            },
            timeout=12,
            headers={"User-Agent": "TrendScope/1.8 (trend intelligence)"},
        )
        resp.raise_for_status()
        hits = resp.json().get("query", {}).get("search", [])
        for h in hits:
            title = h.get("title", "")
            snippet = h.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
            results.append(
                {
                    "source": "wikipedia",
                    "keyword": keyword,
                    "title": title,
                    "text": snippet[:300],
                    "url": f"{base}/wiki/{title.replace(' ', '_')}",
                    "wordcount": h.get("wordcount", 0),
                }
            )
        logger.info(f"Wikipedia '{keyword}': {len(results)} pages")
    except Exception as e:
        logger.warning(f"Wikipedia '{keyword}': {e}")
    return results
