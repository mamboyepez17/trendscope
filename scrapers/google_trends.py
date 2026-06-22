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
            # Extraer noticias relacionadas si existen
            news_items = []
            for news in item.findall(".//ht:news_item", ns)[:3]:
                news_title = news.findtext("ht:news_item_title", "", ns)
                news_source = news.findtext("ht:news_item_source", "", ns)
                if news_title:
                    news_items.append({"title": news_title, "source": news_source})
            results.append({
                "source": "google_trends_rss",
                "keyword": title,
                "approx_traffic": traffic,
                "url": link,
                "geo": geo,
                "related_news": news_items,
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


def _score_relevance(keyword: str, query_keywords: list[str]) -> int:
    """
    Puntua relevancia de un trending topic vs las keywords de la query.
    Mayor = mas relevante.
    """
    kw_lower = keyword.lower()
    score = 0
    for qk in query_keywords:
        qk_lower = qk.lower()
        if qk_lower in kw_lower:
            score += 10
        elif kw_lower in qk_lower:
            score += 5
        # Match parcial por palabras
        else:
            qk_words = set(qk_lower.split())
            kw_words = set(kw_lower.split())
            overlap = len(qk_words & kw_words)
            score += overlap * 3
    return score


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Google Trends."""
    # Intentar RSS primero, pytrends como fallback
    results = _fetch_rss(query.geo)

    # Si el RSS da resultados, intentar pytrends para keywords especificas
    # (combinar ambas fuentes para mayor cobertura)
    pt_results = _fetch_pytrends(query.keywords, query.geo) if query.keywords else []
    if pt_results:
        results.extend(pt_results)

    # Si no hay nada de RSS ni pytrends, devolver vacio
    if not results:
        return []

    # Filtrar y rankear por relevancia con las keywords de la query
    if query.keywords and results:
        # Asignar score de relevancia a cada resultado
        for r in results:
            r["_relevance"] = _score_relevance(r.get("keyword", ""), query.keywords)

        # Ordenar por relevancia (descendente)
        results.sort(key=lambda x: x.get("_relevance", 0), reverse=True)

        # Si hay resultados con relevancia > 0, priorizar esos
        relevant = [r for r in results if r.get("_relevance", 0) > 0]
        if relevant:
            # Tomar los relevantes + algunos generales para contexto
            top_relevant = relevant[:20]
            general = [r for r in results if r.get("_relevance", 0) == 0][:5]
            results = top_relevant + general
        else:
            # Si ninguno es relevante, devolver los top generales
            results = results[:25]

        # Limpiar campo temporal
        for r in results:
            r.pop("_relevance", None)

    return results
