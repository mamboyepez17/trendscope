# scrapers/tiktok.py
# TikTok Creative Center — trending hashtags
# Primario: API JSON interna del Creative Center
# Fallback: Scrapling DynamicFetcher para scraping del HTML
import requests
from loguru import logger

from core.query import TrendQuery

# API interna del TikTok Creative Center (no requiere auth)
TIKTOK_API_URL = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
TIKTOK_PAGE_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/en"


def _fetch_api(country_code: str = "CO", count: int = 20) -> list[dict]:
    """
    API JSON interna del TikTok Creative Center.
    No requiere autenticacion — endpoint publico.
    """
    params = {
        "page": 1,
        "limit": count,
        "period": 7,  # ultimos 7 dias
        "country_code": country_code,
        "sort_by": "popular",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": TIKTOK_PAGE_URL,
    }

    try:
        resp = requests.get(TIKTOK_API_URL, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        items = data.get("data", {}).get("list", [])
        for item in items:
            hashtag = item.get("hashtag_name", "").strip()
            if hashtag:
                results.append({
                    "source": "tiktok_trending",
                    "keyword": hashtag,
                    "type": "hashtag",
                    "video_count": item.get("video_count", 0),
                    "trend_change": item.get("trend", 0),
                })
        return results

    except Exception as e:
        logger.warning(f"TikTok API fallback: {e}")
        return []


def _fetch_scraping() -> list[dict]:
    """
    Fallback: Scrapling DynamicFetcher para scraping del HTML.
    Requiere camoufox o playwright instalado para JS rendering.
    """
    results: list[dict] = []
    seen: set[str] = set()

    try:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(
            TIKTOK_PAGE_URL,
            headless=True,
            network_idle=True,
            timeout=40000,
        )

        selectors = [
            "[class*='hashtagName']",
            "[class*='trend-name']",
            "[class*='TopicName']",
            "[class*='hashtag']",
            "[class*='CardPc_title']",
        ]

        for selector in selectors:
            for el in page.css(selector):
                text = el.text.strip()
                if text and text not in seen and len(text) > 2:
                    seen.add(text)
                    results.append({
                        "source": "tiktok_trending",
                        "keyword": text,
                        "type": "hashtag",
                    })

    except ImportError:
        logger.warning("Scrapling DynamicFetcher no disponible para TikTok fallback")
    except Exception as e:
        logger.warning(f"TikTok scraping fallback: {e}")

    return results


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de TikTok trending hashtags."""
    # Mapear geo a codigo de pais TikTok
    country = query.geo if query.geo else "CO"

    # Primario: API JSON
    results = _fetch_api(country_code=country)

    # Fallback: scraping con DynamicFetcher
    if not results:
        results = _fetch_scraping()

    logger.info(f"TikTok: {len(results)} hashtags trending")
    return results
