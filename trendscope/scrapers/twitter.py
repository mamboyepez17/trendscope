# scrapers/twitter.py
# Usa xactions-py — github.com/mamboyepez17/xactions-py
# xactions-py se incluye como modulo local (carpeta xactions/)
import asyncio

from loguru import logger

from trendscope.config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from trendscope.core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Twitter/X."""
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        logger.warning("Twitter: credenciales no configuradas en .env — saltando fuente")
        return []

    try:
        # xactions-py v1.5+: API pública unificada
        from xactions import TwitterError, search_tweets_sync

        cookie_str = f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
        results: list[dict] = []

        for idx, keyword in enumerate(query.keywords[:4]):
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
                if "rate" in str(e).lower():
                    break
            except Exception as e:
                logger.warning(f"Twitter busqueda '{keyword}': {e}")

            # Backoff entre keywords para no saturar rate limits
            if idx < len(query.keywords[:4]) - 1:
                import time

                time.sleep(1.5)

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
