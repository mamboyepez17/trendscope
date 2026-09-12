"""GDELT free news source (no API key)."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from urllib.parse import quote

from loguru import logger

from trendscope.core.http import get_session
from trendscope.core.query import TrendQuery

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"


def run(query: TrendQuery) -> list[dict]:
    """GDELT DOC API 2.0 — artículos de noticias globales por keyword."""
    session = get_session()
    results: list[dict] = []

    for keyword in query.keywords[:2]:
        try:
            params = {
                "query": keyword,
                "mode": "ArtList",
                "maxrecords": 15,
                "format": "json",
                "timespan": "24h",
            }
            resp = session.get(GDELT_DOC_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles") or []
            for art in articles:
                title = art.get("title") or ""
                if not title:
                    continue
                ts = art.get("seendate") or ""
                results.append(
                    {
                        "source": "gdelt",
                        "keyword": keyword,
                        "title": title[:250],
                        "text": title[:250],
                        "url": art.get("url", ""),
                        "domain": art.get("domain", ""),
                        "language": art.get("language", ""),
                        "published_at": ts,
                        "social_image": art.get("socialimage", ""),
                    }
                )
            logger.info(f"GDELT '{keyword}': {len(articles)} articles")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"GDELT '{keyword}': {e}")

    return results
