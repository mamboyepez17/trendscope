# scrapers/hackernews.py
# Hacker News — 100% gratis, sin auth, API publica de Algolia
# Busca historias por keywords y tambien trae top/trending stories
import requests
from loguru import logger

from core.query import TrendQuery


def _search_stories(keyword: str, limit: int = 15) -> list[dict]:
    """
    API de busqueda de Hacker News (Algolia).
    https://hn.algolia.com/api/v1/search?query=keyword
    """
    url = "https://hn.algolia.com/api/v1/search"
    params = {
        "query": keyword,
        "tags": "story",
        "hitsPerPage": limit,
        "numericFilters": "points>5",
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 400:
            # Algolia a veces rechaza numericFilters, reintentar sin eso
            params.pop("numericFilters", None)
            resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for hit in data.get("hits", []):
            results.append({
                "source": "hackernews",
                "title": hit.get("title") or hit.get("story_title") or "",
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "permalink": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "score": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "created_utc": hit.get("created_at_i", 0),
                "hn_id": hit.get("objectID", ""),
            })
        logger.info(f"HackerNews search '{keyword}': {len(results)} stories")
        return results
    except Exception as e:
        logger.warning(f"HackerNews search '{keyword}': {e}")
        return []


def _fetch_top_stories(limit: int = 15) -> list[dict]:
    """
    Top stories de Hacker News via Firebase API.
    https://hacker-news.firebaseio.com/v0/topstories.json
    """
    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10,
        )
        resp.raise_for_status()
        story_ids = resp.json()[:limit]
        results = []
        for sid in story_ids:
            try:
                story_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=5,
                )
                story = story_resp.json()
                if story and story.get("type") == "story":
                    results.append({
                        "source": "hackernews",
                        "title": story.get("title", ""),
                        "url": story.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                        "permalink": f"https://news.ycombinator.com/item?id={sid}",
                        "score": story.get("score", 0),
                        "comments": story.get("descendants", 0),
                        "author": story.get("by", ""),
                        "created_utc": story.get("time", 0),
                        "hn_id": str(sid),
                    })
            except Exception:
                continue
        logger.info(f"HackerNews top stories: {len(results)}")
        return results
    except Exception as e:
        logger.warning(f"HackerNews top stories: {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Hacker News."""
    all_stories: list[dict] = []

    # Buscar por keywords
    for kw in query.keywords[:3]:
        stories = _search_stories(kw, limit=15)
        all_stories.extend(stories)

    # Si hay pocos resultados, traer top stories para contexto tech
    if len(all_stories) < 10:
        top = _fetch_top_stories(limit=15)
        all_stories.extend(top)

    logger.info(f"HackerNews: {len(all_stories)} stories para '{query.display_name}'")
    return all_stories
