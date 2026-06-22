# scrapers/twitter.py
# Usa xactions-py — github.com/mamboyepez17/xactions-py
# xactions-py se incluye como modulo local (carpeta xactions/)
import asyncio

from loguru import logger

from config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Twitter/X."""
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        logger.warning("Twitter: credenciales no configuradas en .env — saltando fuente")
        return []

    try:
        from xactions.scraper.scrapers import search_tweets_sync
        from xactions.scraper.client import TwitterError

        cookie_str = f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
        results: list[dict] = []

        for keyword in query.keywords[:4]:
            try:
                # Buscar en modo Top (tweets con mas engagement) primero
                tweets = search_tweets_sync(
                    cookies=cookie_str,
                    query=f"{keyword} lang:es OR lang:en",
                    limit=20,
                    mode="Top",
                )

                for tweet in tweets:
                    text = tweet.get("text", "")
                    author = tweet.get("author", {})
                    results.append({
                        "source": "twitter",
                        "keyword": keyword,
                        "title": text[:200],
                        "text": text[:200],
                        "likes": tweet.get("likes", 0),
                        "retweets": tweet.get("retweets", 0),
                        "replies": tweet.get("replies", 0),
                        "user_followers": author.get("followers", 0),
                        "url": tweet.get("url", ""),
                    })

                logger.info(f"Twitter '{keyword}': {len(tweets)} tweets")

            except TwitterError as e:
                logger.warning(f"Twitter busqueda '{keyword}': {e}")
            except Exception as e:
                logger.warning(f"Twitter busqueda '{keyword}': {e}")

        logger.info(f"Twitter total: {len(results)} tweets")
        return results

    except ImportError as e:
        logger.error(
            f"xactions-py no instalado o import fallido: {e}. "
            "El modulo xactions/ debe estar en el directorio del proyecto."
        )
        return []
    except Exception as e:
        logger.error(f"Twitter scraper: {e}")
        return []
