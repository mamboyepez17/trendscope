"""Bing News RSS — free, no API key."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote

from loguru import logger

from trendscope.core.dates import parse_date
from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    session = get_session()
    results: list[dict] = []
    for keyword in query.search_phrases[:2]:
        # qft interval: 4 = 24 h, 7 = semana, 8 = mes
        days = query.max_age_days
        interval = "4" if days <= 1 else "7" if days <= 7 else "8"
        qft = quote('interval="' + interval + '"')
        url = f"https://www.bing.com/news/search?q={quote(keyword)}&format=rss&qft={qft}"
        try:
            resp = session.get(url, timeout=12, headers={"User-Agent": "TrendScope/1.8"})
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:10]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()
                if not title:
                    continue
                results.append(
                    {
                        "source": "bing_news",
                        "keyword": keyword,
                        "title": title[:250],
                        "text": title[:250],
                        "url": link,
                        "published_at": pub,
                        "created_utc": parse_date(pub),
                    }
                )
            logger.info(f"BingNews '{keyword}': {len(results)} total")
        except Exception as e:
            logger.warning(f"BingNews '{keyword}': {e}")
    return results
