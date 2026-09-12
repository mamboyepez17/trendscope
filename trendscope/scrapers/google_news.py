"""Google News RSS — topic-specific news, free, no API key."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery

# Feeds por keyword (es/CO)
_RSS = "https://news.google.com/rss/search?q={q}&hl=es-419&gl=CO&ceid=CO:es-419"


def run(query: TrendQuery) -> list[dict]:
    """Busca noticias de Google News por cada keyword del tema."""
    session = get_session()
    results: list[dict] = []

    for keyword in query.keywords[:3]:
        url = _RSS.format(q=quote(keyword))
        try:
            resp = session.get(url, timeout=15, headers={"User-Agent": "TrendScope/1.8"})
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            for item in items[:12]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                source_el = item.find("{https://news.google.com}source")
                source_name = (
                    (source_el.text or "").strip()
                    if source_el is not None
                    else (item.findtext("source") or "google_news")
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
                        "domain": source_name,
                    }
                )
            logger.info(f"GoogleNews '{keyword}': {len(items)} items")
        except Exception as e:
            logger.warning(f"GoogleNews '{keyword}': {e}")

    return results
