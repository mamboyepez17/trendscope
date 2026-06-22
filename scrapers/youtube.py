# scrapers/youtube.py
# YouTube Trends — gratis, sin auth, via API publica de search
# Usa el endpoint publico de YouTube que devuelve videos trending
import re
import time
import json

import requests
from loguru import logger

from core.query import TrendQuery


def _search_youtube(keyword: str, limit: int = 15) -> list[dict]:
    """
    Busca videos en YouTube usando el endpoint interno publico.
    No requiere API key — usa el mismo endpoint que usa la pagina de busqueda.
    """
    url = "https://www.youtube.com/youtubei/v1/search"
    params = {}  # API key publica embebida
    payload = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240601.00.00",
                "hl": "es",
                "gl": "CO",
            }
        },
        "query": keyword,
        "params": "EgIQAQ%3D%3D",  # Ordenar por relevance
    }

    try:
        resp = requests.post(url, params=params, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        # Navegar la estructura JSON de YouTube (es compleja y anidada)
        contents = (
            data.get("contents", {})
            .get("twoColumnSearchResultsRenderer", {})
            .get("primaryContents", {})
            .get("sectionListRenderer", {})
            .get("contents", [])
        )

        for section in contents:
            items = (
                section.get("itemSectionRenderer", {})
                .get("contents", [])
            )
            for item in items:
                video = item.get("videoRenderer", {})
                if not video or not video.get("videoId"):
                    continue

                title = (
                    video.get("title", {})
                    .get("runs", [{}])[0]
                    .get("text", "")
                )

                channel = (
                    video.get("ownerText", {})
                    .get("runs", [{}])[0]
                    .get("text", "")
                )

                # Views: "1.2M views" -> extraer numero
                view_text = (
                    video.get("viewCount", {})
                    .get("simpleText", "")
                )
                views = _parse_views(view_text)

                # Tiempo: "Hace 2 dias"
                published = (
                    video.get("publishedTimeText", {})
                    .get("simpleText", "")
                )

                video_id = video.get("videoId", "")
                results.append({
                    "source": "youtube",
                    "keyword": keyword,
                    "title": title,
                    "channel": channel,
                    "views": views,
                    "published": published,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "video_id": video_id,
                })

                if len(results) >= limit:
                    break

        logger.info(f"YouTube search '{keyword}': {len(results)} videos")
        return results

    except Exception as e:
        logger.warning(f"YouTube search '{keyword}': {e}")
        return []


def _parse_views(view_text: str) -> int:
    """Convierte '1.2M views' o '15K views' a entero."""
    if not view_text:
        return 0
    # Extraer numero
    match = re.search(r"([\d.]+)\s*([KM]?)", view_text, re.I)
    if not match:
        return 0
    num = float(match.group(1))
    suffix = match.group(2).upper()
    if suffix == "M":
        return int(num * 1_000_000)
    elif suffix == "K":
        return int(num * 1_000)
    return int(num)


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de YouTube."""
    all_videos: list[dict] = []

    for kw in query.keywords[:3]:
        videos = _search_youtube(kw, limit=15)
        all_videos.extend(videos)
        time.sleep(0.5)

    logger.info(f"YouTube: {len(all_videos)} videos para '{query.display_name}'")
    return all_videos
