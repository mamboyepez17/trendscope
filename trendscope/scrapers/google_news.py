"""Google News RSS — topic-specific news, free, no API key."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

from loguru import logger

from trendscope.core.dates import parse_date
from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery

_RSS = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={gl}:{lang}"

# Idioma de la edición según el país (por defecto español latinoamericano)
_EDITION = {
    "ES": ("es", "es"), "US": ("en-US", "en"), "GB": ("en-GB", "en"),
    "BR": ("pt-BR", "pt-419"), "PT": ("pt-PT", "pt-150"),
}


def _edition(geo: str) -> tuple[str, str, str]:
    gl = (geo or "CO").upper()
    hl, lang = _EDITION.get(gl, ("es-419", "es-419"))
    return hl, gl, lang


def _split_title(title: str) -> tuple[str, str]:
    """Google News añade " - Medio" al final del titular; lo separa."""
    if " - " in title:
        head, _, src = title.rpartition(" - ")
        if head and len(src) <= 60:
            return head.strip(), src.strip()
    return title, ""


def run(query: TrendQuery) -> list[dict]:
    """Busca noticias de Google News por cada keyword del tema."""
    session = get_session()
    results: list[dict] = []

    hl, gl, lang = _edition(query.geo)
    for keyword in query.search_phrases[:3]:
        # Frase exacta + when:Nd → solo artículos del tema de los últimos N días
        q = f"{keyword} when:{max(1, int(query.max_age_days))}d"
        url = _RSS.format(q=quote(q), hl=hl, gl=gl, lang=lang)
        try:
            resp = session.get(url, timeout=15, headers={"User-Agent": "TrendScope/1.8"})
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            for item in items[:20]:
                title, media = _split_title((item.findtext("title") or "").strip())
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                source_el = item.find("{https://news.google.com}source")
                source_name = (
                    (source_el.text or "").strip()
                    if source_el is not None
                    else (item.findtext("source") or media or "google_news")
                )
                if not title:
                    continue
                results.append(
                    {
                        "source": "google_news",
                        "keyword": keyword,
                        "title": title[:250],
                        "text": title[:250],
                        "url": link,
                        "published_at": pub,
                        "created_utc": parse_date(pub),
                        "domain": source_name,
                    }
                )
            logger.info(f"GoogleNews '{keyword}': {len(items)} items")
        except Exception as e:
            logger.warning(f"GoogleNews '{keyword}': {e}")

    return results
