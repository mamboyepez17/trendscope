# scrapers/reddit.py
# Reddit scraper — 100% gratuito, sin API key
# Estrategia: RSS de old.reddit.com (primario) + JSON publico (fallback si funciona)
import re
import time
import xml.etree.ElementTree as ET

import requests
from loguru import logger

from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from core.query import TrendQuery


def _get_praw_client():
    """Retorna cliente PRAW si hay credenciales, si no None."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        try:
            import praw
            return praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT,
            )
        except Exception as e:
            logger.warning(f"PRAW init fallido: {e}")
    return None


def _fetch_rss(subreddit: str, feed: str = "hot", limit: int = 20) -> list[dict]:
    """
    RSS publico de Reddit via old.reddit.com — sin API key, 100% gratuito.
    old.reddit.com aun sirve RSS sin rate limiting agresivo.
    Retorna posts con title, url, author y fecha.
    """
    # Mapear feed a URL de RSS
    feed_path = feed if feed in ("hot", "new", "top", "rising") else "hot"
    url = f"https://old.reddit.com/r/{subreddit}/{feed_path}.rss?limit={limit}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/atom+xml,application/xml,text/xml;q=0.9",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 429:
            logger.warning(f"Reddit RSS r/{subreddit}/{feed}: rate limited (429), reintentando en 8s...")
            time.sleep(8)
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 429:
                logger.warning(f"Reddit RSS r/{subreddit}/{feed}: sigue rate limited, saltando")
                return []
        resp.raise_for_status()

        if not resp.text or len(resp.text) < 100:
            logger.warning(f"Reddit RSS r/{subreddit}: respuesta vacia")
            return []

        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []

        for entry in root.findall(".//atom:entry", ns)[:limit]:
            title = entry.findtext("atom:title", "", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            author = entry.findtext("atom:author/atom:name", "", ns)
            updated = entry.findtext("atom:updated", "", ns)
            content = entry.findtext("atom:content", "", ns) or ""

            # Intentar extraer score del content HTML
            score_match = re.search(r"(\d[\d,]*)\s*points?", content, re.I)
            comments_match = re.search(r"(\d[\d,]*)\s*comments?", content, re.I)

            score = int(score_match.group(1).replace(",", "")) if score_match else 0
            comments = int(comments_match.group(1).replace(",", "")) if comments_match else 0

            # Convertir fecha ISO a timestamp
            created_utc = 0.0
            if updated:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    created_utc = dt.timestamp()
                except Exception:
                    pass

            # Estimar score basado en recencia si no hay score
            if score == 0 and created_utc:
                hours_old = (time.time() - created_utc) / 3600
                # Posts nuevos en hot suelen tener score creciente
                score = max(1, int(500 / max(1, hours_old)))

            if title:
                results.append({
                    "source": "reddit",
                    "subreddit": subreddit,
                    "title": title,
                    "score": score,
                    "comments": comments,
                    "upvote_ratio": 0.8,  # Estimado, RSS no lo da
                    "url": link,
                    "permalink": link,
                    "created_utc": created_utc,
                    "author": author,
                })

        logger.info(f"Reddit RSS r/{subreddit}/{feed_path}: {len(results)} posts")
        return results

    except Exception as e:
        logger.warning(f"Reddit RSS r/{subreddit}/{feed}: {e}")
        return []


def _fetch_search_rss(query_str: str, sort: str = "new", limit: int = 15) -> list[dict]:
    """
    Busqueda por keywords via RSS de Reddit — sin API key.
    Busca en todos los subreddits.
    """
    url = f"https://old.reddit.com/search.rss?q={requests.utils.quote(query_str)}&sort={sort}&limit={limit}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/atom+xml,application/xml,text/xml;q=0.9",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 429:
            time.sleep(5)
            return []
        resp.raise_for_status()

        if not resp.text or len(resp.text) < 100:
            return []

        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []

        for entry in root.findall(".//atom:entry", ns)[:limit]:
            title = entry.findtext("atom:title", "", ns)
            link_el = entry.find("atom:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            updated = entry.findtext("atom:updated", "", ns)
            content = entry.findtext("atom:content", "", ns) or ""

            # Extraer subreddit del link
            sub_match = re.search(r"/r/(\w+)", link)
            subreddit = sub_match.group(1) if sub_match else "unknown"

            # Intentar extraer score
            score_match = re.search(r"(\d[\d,]*)\s*points?", content, re.I)
            score = int(score_match.group(1).replace(",", "")) if score_match else 0

            created_utc = 0.0
            if updated:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    created_utc = dt.timestamp()
                except Exception:
                    pass

            if score == 0 and created_utc:
                hours_old = (time.time() - created_utc) / 3600
                score = max(1, int(300 / max(1, hours_old)))

            if title:
                results.append({
                    "source": "reddit",
                    "subreddit": subreddit,
                    "title": title,
                    "score": score,
                    "comments": 0,
                    "upvote_ratio": 0.8,
                    "url": link,
                    "permalink": link,
                    "created_utc": created_utc,
                    "author": "",
                })

        logger.info(f"Reddit search RSS '{query_str}': {len(results)} posts")
        return results

    except Exception as e:
        logger.warning(f"Reddit search RSS '{query_str}': {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Reddit. 100% gratuito, sin API key necesaria."""
    all_posts: list[dict] = []

    # Si hay credenciales PRAW, usarlas (mejor data: score, comments, upvote_ratio reales)
    reddit = _get_praw_client()

    if reddit:
        # --- Modo PRAW (con API key) ---
        for sub in query.subreddits:
            for feed in ["hot", "rising"]:
                try:
                    method = getattr(reddit.subreddit(sub), feed)
                    for post in method(limit=15):
                        all_posts.append({
                            "source": "reddit",
                            "subreddit": sub,
                            "title": post.title,
                            "score": post.score,
                            "comments": post.num_comments,
                            "upvote_ratio": post.upvote_ratio,
                            "url": post.url,
                            "permalink": f"https://reddit.com{post.permalink}",
                            "created_utc": post.created_utc,
                        })
                except Exception as e:
                    logger.warning(f"PRAW r/{sub} -> fallback RSS: {e}")
                    posts = _fetch_rss(sub, feed)
                    all_posts.extend(posts)
                time.sleep(1.5)
    else:
        # --- Modo RSS (sin API key, 100% gratis) ---
        # Usar hasta 3 subreddits con delay adaptativo
        top_subs = query.subreddits[:3]
        delay = 3  # delay inicial

        for sub in top_subs:
            posts = _fetch_rss(sub, "hot", limit=20)
            if posts:
                all_posts.extend(posts)
                delay = max(2, delay - 1)  # si funciona, reducir delay
            else:
                delay = min(10, delay + 4)  # si falla, aumentar delay
            time.sleep(delay)

        # Busqueda por keyword principal via RSS
        if query.keywords:
            for kw in query.keywords[:2]:
                search_results = _fetch_search_rss(kw, sort="new", limit=15)
                all_posts.extend(search_results)
                time.sleep(delay)

    # Filtrar por relevancia con las keywords de la query
    if query.keywords and all_posts:
        kws = [k.lower() for k in query.keywords]
        filtered = [p for p in all_posts if any(k in p["title"].lower() for k in kws)]
        # Si hay match, priorizar esos pero mantener algunos generales
        if filtered:
            # Top relevantes + algunos generales para contexto
            all_posts = filtered + [p for p in all_posts if p not in filtered][:5]

    logger.info(f"Reddit: {len(all_posts)} posts para '{query.display_name}'")
    return all_posts
