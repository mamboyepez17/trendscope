# scrapers/google_trends.py
import time
import xml.etree.ElementTree as ET

import requests
from loguru import logger

from core.query import TrendQuery


def _fetch_rss(geo: str) -> list[dict]:
    """
    RSS publico de Google Trends — primario.
    Sin JavaScript, sin captcha, sin autenticacion.
    """
    url = f"https://trends.google.com/trending/rss?geo={geo}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "TrendScope/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        ns = {"ht": "https://trends.google.com/trending/rss"}
        results = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            traffic = item.findtext("ht:approx_traffic", "N/A", ns)
            link = item.findtext("link", "")
            results.append({
                "source": "google_trends_rss",
                "keyword": title,
                "approx_traffic": traffic,
                "url": link,
                "geo": geo,
            })
        logger.info(f"Google Trends RSS ({geo}): {len(results)} tendencias")
        return results
    except Exception as e:
        logger.warning(f"Google Trends RSS fallo: {e} -> activando pytrends")
        return []


def _fetch_pytrends(keywords: list[str], geo: str) -> list[dict]:
    """
    Fallback pytrends para keywords especificas.
    Puede dar errores 429 — manejado con try/except por batch.
    """
    try:
        from pytrends.request import TrendReq
        pt = TrendReq(hl="es-CO", tz=-300, timeout=(10, 25))
        results = []

        for i in range(0, len(keywords), 5):
            batch = keywords[i:i + 5]
            try:
                pt.build_payload(batch, geo=geo, timeframe="now 7-d")
                df = pt.interest_over_time()
                if not df.empty:
                    for kw in batch:
                        if kw in df.columns:
                            results.append({
                                "source": "google_trends_pytrends",
                                "keyword": kw,
                                "avg_interest_7d": int(df[kw].mean()),
                                "geo": geo,
                            })
            except Exception as e:
                logger.warning(f"pytrends batch {batch}: {e}")
            time.sleep(3)

        logger.info(f"pytrends: {len(results)} keywords")
        return results

    except ImportError:
        logger.error("pytrends no instalado")
        return []
    except Exception as e:
        logger.error(f"pytrends completamente fallido: {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Google Trends."""
    # Intentar RSS primero, pytrends como fallback
    results = _fetch_rss(query.geo)
    if not results:
        results = _fetch_pytrends(query.keywords, query.geo)

    # Filtrar por relevancia si hay keywords y los resultados vienen del RSS
    if query.keywords and results:
        kws = [k.lower() for k in query.keywords]
        filtered = [
            r for r in results
            if any(k in r.get("keyword", "").lower() for k in kws)
        ]
        return filtered or results  # Si no hay match, devolver todo

    return results
