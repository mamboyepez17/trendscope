# scrapers/twitter.py
# Usa xactions-py — github.com/mamboyepez17/xactions-py
from loguru import logger

from config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Twitter/X."""
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        logger.warning("Twitter: credenciales no configuradas en .env — saltando fuente")
        return []

    try:
        from xactions import TwitterClient
        client = TwitterClient(
            auth_token=TWITTER_AUTH_TOKEN,
            ct0=TWITTER_CT0,
        )
        results: list[dict] = []

        for keyword in query.keywords[:4]:  # Max 4 para no saturar
            try:
                tweets = client.search_tweets(
                    query=f"{keyword} lang:es",
                    limit=20,
                )
                for tweet in tweets:
                    results.append({
                        "source": "twitter",
                        "keyword": keyword,
                        "text": tweet.get("text", "")[:200],
                        "likes": tweet.get("favorite_count", 0),
                        "retweets": tweet.get("retweet_count", 0),
                        "replies": tweet.get("reply_count", 0),
                        "user_followers": tweet.get("user", {}).get("followers_count", 0),
                        "url": f"https://twitter.com/i/web/status/{tweet.get('id_str', '')}",
                    })
                logger.info(f"Twitter '{keyword}': {len(tweets)} tweets")
            except Exception as e:
                logger.warning(f"Twitter busqueda '{keyword}': {e}")

        logger.info(f"Twitter total: {len(results)} tweets")
        return results

    except ImportError:
        logger.error(
            "xactions-py no instalado. Ejecuta: "
            "pip install git+https://github.com/mamboyepez17/xactions-py.git"
        )
        return []
    except Exception as e:
        logger.error(f"Twitter scraper: {e}")
        return []
