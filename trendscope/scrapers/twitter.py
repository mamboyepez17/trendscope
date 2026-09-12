# scrapers/twitter.py
# Usa xactions-py — github.com/mamboyepez17/xactions-py
# xactions-py se incluye como modulo local (carpeta xactions/)
import time

from loguru import logger

from trendscope.config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from trendscope.core.query import TrendQuery


def _twitter_query(keyword: str) -> str:
    """
    Construye la query de búsqueda de X/Twitter.
    - Comillas en frases multi-palabra (si no, X trata palabras sueltas y devuelve ruido).
    - NO usar `lang:es OR lang:en`: con esa operatoria X devuelve el feed Explore/viral
      en vez de resultados del tema.
    """
    kw = (keyword or "").strip()
    if not kw:
        return kw
    if " " in kw and not kw.startswith('"'):
        return f'"{kw}"'
    return kw


def _is_relevant(text: str, keyword: str, min_hits: int = 1) -> bool:
    """Descarta tweets que no mencionan tokens significativos del tema."""
    if not text:
        return False
    tokens = [t.lower() for t in keyword.replace('"', "").split() if len(t) > 3]
    if not tokens:
        return True
    tl = text.lower()
    hits = sum(1 for t in tokens if t in tl)
    return hits >= min(min_hits, len(tokens))


def run(query: TrendQuery) -> list[dict]:
    """Entry point del scraper de Twitter/X."""
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        logger.warning("Twitter: credenciales no configuradas en .env — saltando fuente")
        return []

    try:
        from trendscope.xactions import TwitterError, search_tweets_sync

        cookie_str = f"auth_token={TWITTER_AUTH_TOKEN}; ct0={TWITTER_CT0}"
        results: list[dict] = []
        keywords = query.keywords[:3]

        for idx, keyword in enumerate(keywords):
            q = _twitter_query(keyword)
            if not q:
                continue
            try:
                # Latest: resultados del tema (Top + query sin comillas = feed viral)
                tweets = search_tweets_sync(
                    cookies=cookie_str,
                    query=q,
                    limit=15,
                    mode="Latest",
                )

                kept = 0
                for tweet in tweets:
                    text = tweet.get("text", "")
                    if not _is_relevant(text, keyword):
                        continue
                    author = tweet.get("author", {})
                    results.append(
                        {
                            "source": "twitter",
                            "keyword": keyword,
                            "title": text[:200],
                            "text": text[:200],
                            "likes": tweet.get("likes", 0),
                            "retweets": tweet.get("retweets", 0),
                            "replies": tweet.get("replies", 0),
                            "user_followers": author.get("followers", 0),
                            "url": tweet.get("url", ""),
                        }
                    )
                    kept += 1

                logger.info(f"Twitter '{q}': {kept}/{len(tweets)} relevantes")
            except TwitterError as e:
                logger.warning(f"Twitter busqueda '{q}': {e}")
                if "rate" in str(e).lower():
                    break
            except Exception as e:
                logger.warning(f"Twitter busqueda '{q}': {e}")

            if idx < len(keywords) - 1:
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
