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
        from xactions.scraper.client import TwitterClient
        from xactions.scraper.scrapers import search_tweets

        # Construir cookie string en el formato que xactions espera
        cookie_str = f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
        client = TwitterClient(cookies=cookie_str)

        if not client.is_authenticated():
            logger.warning("Twitter: cookie auth_token no valida")
            return []

        results: list[dict] = []

        # xactions search_tweets es async — necesitamos event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for keyword in query.keywords[:4]:  # Max 4 keywords
            try:
                # Buscar tweets en español e ingles
                search_query = f"{keyword} lang:es OR lang:en"
                tweets = loop.run_until_complete(
                    search_tweets(client, query=search_query, limit=20, mode="Latest")
                )

                for tweet in tweets:
                    # Usar el texto del tweet como titulo (para dedup y export)
                    text = tweet.get("text", "")
                    results.append({
                        "source": "twitter",
                        "keyword": keyword,
                        "title": text[:200],  # Agregar title para dedup y export
                        "text": text[:200],
                        "likes": tweet.get("likes", 0),
                        "retweets": tweet.get("retweets", 0),
                        "replies": tweet.get("replies", 0),
                        "user_followers": tweet.get("author", {}).get("followers", 0),
                        "url": tweet.get("url", ""),
                    })

                logger.info(f"Twitter '{keyword}': {len(tweets)} tweets")

            except Exception as e:
                logger.warning(f"Twitter busqueda '{keyword}': {e}")

        loop.close()

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
