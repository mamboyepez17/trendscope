"""Wikipedia search (es) — free, no API key."""

from __future__ import annotations

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery

API = "https://es.wikipedia.org/w/api.php"


def run(query: TrendQuery) -> list[dict]:
    session = get_session()
    results: list[dict] = []
    # Solo el keyword principal (Wikipedia no necesita 3 variantes)
    keyword = (query.keywords[0] if query.keywords else query.free_topic or "").strip()
    if not keyword:
        return []
    try:
        resp = session.get(
            API,
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
                    "url": f"https://es.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    "wordcount": h.get("wordcount", 0),
                }
            )
        logger.info(f"Wikipedia '{keyword}': {len(results)} pages")
    except Exception as e:
        logger.warning(f"Wikipedia '{keyword}': {e}")
    return results
