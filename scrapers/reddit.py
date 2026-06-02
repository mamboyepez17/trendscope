# scrapers/reddit.py
import time

import praw
import requests
from loguru import logger

from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from core.query import TrendQuery


def _get_praw_client() -> praw.Reddit | None:
    """Retorna cliente PRAW si hay credenciales, si no None."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        try:
            return praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT,
            )
        except Exception as e:
            logger.warning(f"PRAW init fallido: {e}")
    return None


def _fetch_public(subreddit: str, feed: str = "hot", limit: int = 20) -> list[dict]:
    """
    Endpoint JSON publico de Reddit — sin API key.
    Funciona sin credenciales, 100% gratuito.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{feed}.json?limit={limit}&raw_json=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return [
            {
                "source": "reddit",
                "subreddit": subreddit,
                "title": p["data"].get("title", ""),
                "score": p["data"].get("score", 0),
                "comments": p["data"].get("num_comments", 0),
                "upvote_ratio": p["data"].get("upvote_ratio", 0),
                "url": p["data"].get("url", ""),
                "permalink": f"https://reddit.com{p['data'].get('permalink', '')}",
                "created_utc": p["data"].get("created_utc", 0),
            }
            for p in resp.json()["data"]["children"]
        ]
    except Exception as e:
        logger.warning(f"Reddit publico r/{subreddit}/{feed}: {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Reddit."""
    reddit = _get_praw_client()
    all_posts: list[dict] = []

    for sub in query.subreddits:
        for feed in ["hot", "rising"]:
            posts: list[dict] = []

            if reddit:
                try:
                    method = getattr(reddit.subreddit(sub), feed)
                    for post in method(limit=15):
                        posts.append({
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
                    logger.warning(f"PRAW r/{sub} -> fallback publico: {e}")
                    posts = _fetch_public(sub, feed)
            else:
                posts = _fetch_public(sub, feed)

            # Filtrar por relevancia con las keywords de la query
            if query.keywords and posts:
                kws = [k.lower() for k in query.keywords]
                filtered = [p for p in posts if any(k in p["title"].lower() for k in kws)]
                posts = filtered or posts  # Si no hay match, mantener todos

            all_posts.extend(posts)
            time.sleep(1.5)  # Respetar rate limit

    logger.info(f"Reddit: {len(all_posts)} posts para '{query.display_name}'")
    return all_posts
