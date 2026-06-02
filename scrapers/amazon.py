# scrapers/amazon.py
# Usa Scrapling StealthyFetcher — bypassa anti-bot de Amazon
import random
import time

from loguru import logger

from config import AMAZON_URLS_BY_CATEGORY
from core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Amazon Best Sellers."""
    cat = query.category if query.category in AMAZON_URLS_BY_CATEGORY else "default"
    url = AMAZON_URLS_BY_CATEGORY[cat]
    results: list[dict] = []

    try:
        from scrapling.fetchers import StealthyFetcher

        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            auto_match=True,  # Scrapling aprende de cambios en el DOM
        )

        # Scrapling usa css() que retorna lista de Selectors
        items = page.css(".zg-grid-general-faceout")

        for item in items[:15]:
            # css() retorna lista, tomamos el primero si existe
            title_els = item.css(
                "._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, .p13n-sc-truncated, "
                "[class*='p13n-sc-truncate'], .a-size-base"
            )
            price_els = item.css(".p13n-sc-price, .a-price .a-offscreen, ._cDEzb_p13n-sc-price_3mJ9Z")
            rank_els = item.css(".zg-bdg-text")

            title_el = title_els[0] if title_els else None
            price_el = price_els[0] if price_els else None
            rank_el = rank_els[0] if rank_els else None

            if title_el:
                results.append({
                    "source": "amazon_bestsellers",
                    "category": cat,
                    "title": title_el.text.strip(),
                    "price": price_el.text.strip() if price_el else "N/A",
                    "rank": rank_el.text.strip() if rank_el else "N/A",
                    "url": url,
                })

        time.sleep(random.uniform(2, 4))

    except ImportError:
        logger.error("Scrapling no instalado. Ejecuta: pip install scrapling")
    except Exception as e:
        logger.error(f"Amazon '{cat}': {e}")

    logger.info(f"Amazon '{cat}': {len(results)} productos")
    return results
