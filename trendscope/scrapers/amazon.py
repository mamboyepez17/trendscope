# scrapers/amazon.py
"""Amazon — productos del tema con estrellas y reseñas (satisfacción real).

- Tema libre: búsqueda `/s?k=tema` en el Amazon del país (amazon.com.mx,
  amazon.com.br, amazon.es…; países sin tienda usan amazon.com).
- Categoría: más vendidos (`/gp/bestsellers/<nodo>`) de esa tienda.

Descarga en dos pasos (Scrapling, `pip install "scrapling[fetchers]"`):
  1. `Fetcher` (HTTP con huella de Chrome, sin navegador, rápido).
  2. Si Amazon responde con captcha/bloqueo: `StealthyFetcher` (navegador
     sigiloso; requiere haber corrido una vez `scrapling install`).
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from urllib.parse import quote_plus

from loguru import logger

from trendscope.core.query import TrendQuery

_FETCH_TIMEOUT_SECONDS = 45
_MAX_PRODUCTS = 15

# Nodos de "más vendidos" (mismo slug en casi todas las tiendas de Amazon)
BESTSELLER_NODES: dict[str, str] = {
    "tecnologia": "electronics",
    "salud": "hpc",
    "deportes": "sporting-goods",
    "moda": "fashion",
    "emprendimiento": "books",
}

_BLOCK_MARKERS = (
    "captcha", "api-services-support@amazon.com", "/errors/validatecaptcha",
    "robot check", "sorry, we just need to make sure",
)


def build_url(query: TrendQuery) -> tuple[str, str]:
    """(url, modo) según el tipo de consulta y el país."""
    from trendscope.core.locale import amazon_domain

    domain = amazon_domain(query.geo)
    if query.mode == "category":
        node = BESTSELLER_NODES.get(query.category or "", "")
        return f"https://www.{domain}/gp/bestsellers/{node}".rstrip("/") + "/", "bestsellers"
    topic = (query.free_topic or (query.keywords[0] if query.keywords else "")).strip()
    return f"https://www.{domain}/s?k={quote_plus(topic)}", "search"


def is_blocked(html: str, status: int | None = None) -> bool:
    if status in (429, 503):
        return True
    low = (html or "").lower()
    return any(m in low for m in _BLOCK_MARKERS)


def parse_rating(text: str) -> float | None:
    """'4.5 out of 5 stars' · '4,5 de 5 estrellas' · '5つ星のうち4.5' → 4.5"""
    nums = [float(n.replace(",", ".")) for n in re.findall(r"\d+(?:[.,]\d+)?", text or "")]
    if not nums:
        return None
    if len(nums) >= 2 and nums[0] == 5 and "のうち" in text:
        nums = nums[1:]
    value = nums[0]
    return value if 0 < value <= 5 else None


def parse_count(text: str) -> int:
    """'1,234' · '1.234' · '(1.2K)' · '2 mil' → entero."""
    t = (text or "").lower().replace("\xa0", " ")
    m = re.search(r"(\d+(?:[.,]\d+)*)\s*(k|mil)?\b", t)
    if not m:
        return 0
    raw, suffix = m.group(1), m.group(2)
    if suffix:
        return int(float(raw.replace(",", ".")) * 1000)
    return int(re.sub(r"[.,]", "", raw))


def _first_text(el, selectors: str) -> str:
    """Primer texto no vacío entre los elementos que coinciden (en orden)."""
    for node in el.css(selectors):
        text = (node.text or "").strip()
        if not text and hasattr(node, "get_all_text"):
            text = (node.get_all_text(strip=True) or "").strip()
        if text:
            return text
    return ""


def parse_search(page, domain_url: str) -> list[dict]:
    """Productos de una página de búsqueda de Amazon."""
    base = re.match(r"https://[^/]+", domain_url).group(0)
    out: list[dict] = []
    for el in page.css('div[data-component-type="s-search-result"]'):
        asin = el.attrib.get("data-asin", "")
        title = _first_text(el, "h2 span, h2 a span, h2")
        if not asin or not title:
            continue
        if el.css(".puis-sponsored-label-text, .s-sponsored-label-text"):
            continue  # anuncios: no son señal orgánica
        rating = parse_rating(_first_text(el, ".a-icon-alt"))
        reviews = parse_count(
            _first_text(el, 'a[href*="customerReviews"] span, span.s-underline-text')
        )
        out.append({
            "source": "amazon",
            "asin": asin,
            "title": title[:250],
            "price": _first_text(el, ".a-price .a-offscreen") or "N/A",
            "rating": rating,
            "reviews": reviews,
            "url": f"{base}/dp/{asin}",
        })
        if len(out) >= _MAX_PRODUCTS:
            break
    return out


def parse_bestsellers(page, url: str, category: str) -> list[dict]:
    out: list[dict] = []
    for item in page.css(".zg-grid-general-faceout, [id^='gridItemRoot']")[:_MAX_PRODUCTS]:
        title = _first_text(
            item,
            "._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, .p13n-sc-truncated, "
            "[class*='p13n-sc-truncate'], [class*='line-clamp'], .a-size-base",
        )
        if not title:
            continue
        out.append({
            "source": "amazon_bestsellers",
            "category": category,
            "title": title[:250],
            "price": _first_text(item, ".p13n-sc-price, .a-price .a-offscreen") or "N/A",
            "rank": _first_text(item, ".zg-bdg-text") or "N/A",
            "rating": parse_rating(_first_text(item, ".a-icon-alt")),
            "url": url,
        })
    return out


def _fetch_page(url: str, locale: str | None = None):
    """Página parseable (Scrapling). HTTP primero; navegador si hay bloqueo."""
    from scrapling.fetchers import Fetcher

    page = Fetcher.get(url, impersonate="chrome", stealthy_headers=True, timeout=20)
    if not is_blocked(getattr(page, "html_content", "") or str(page), getattr(page, "status", None)):
        return page
    logger.info("Amazon bloqueó la petición HTTP → navegador sigiloso")
    from scrapling.fetchers import StealthyFetcher

    kwargs = {"headless": True, "network_idle": True, "timeout": 40000}
    if locale:
        kwargs["locale"] = locale
    page = StealthyFetcher.fetch(url, **kwargs)
    if is_blocked(getattr(page, "html_content", "") or str(page), getattr(page, "status", None)):
        raise RuntimeError("Amazon sigue mostrando captcha (prueba más tarde o con otra IP)")
    return page


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Amazon."""
    from trendscope.core.locale import language_for

    url, mode = build_url(query)
    locale = f"{language_for(query.geo)}-{(query.geo or 'US').upper()}"
    results: list[dict] = []

    def _job() -> list[dict]:
        page = _fetch_page(url, locale)
        if mode == "search":
            return parse_search(page, url)
        return parse_bestsellers(page, url, query.category or "default")

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            results = pool.submit(_job).result(timeout=_FETCH_TIMEOUT_SECONDS)
    except ImportError:
        logger.error('Amazon: falta Scrapling con fetchers → pip install "scrapling[fetchers]"')
    except FuturesTimeout:
        logger.error(f"Amazon: timeout {_FETCH_TIMEOUT_SECONDS}s — saltando fuente")
    except Exception as e:
        msg = str(e)
        if "Executable doesn't exist" in msg or "playwright install" in msg or "camoufox" in msg.lower():
            logger.error("Amazon: falta el navegador de Scrapling → ejecuta una vez: scrapling install")
        else:
            logger.error(f"Amazon ({mode}): {e}")

    logger.info(f"Amazon ({mode}): {len(results)} productos")
    return results
