# 🕷️ TRENDSCOPE — BLOQUE 2 DE 7
## Scrapers (5 fuentes)
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 2 de 7. Construyes los 5 scrapers independientes.
Cada uno es autónomo — si falla, retorna [] y el pipeline sigue.

**Prerequisito:** Bloque 1 aprobado.

**Reglas:**
- Scrapling para Amazon y TikTok (reemplaza Playwright + BS4)
- Cada scraper tiene su validación individual
- Validar CADA scraper antes de pasar al siguiente
- NO pasar al Bloque 3 sin confirmación del usuario

---

## PASO 2.1 — `scrapers/reddit.py`

```python
# scrapers/reddit.py
import praw
import requests
import time
from loguru import logger
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from core.query import TrendQuery


def _get_praw_client() -> praw.Reddit | None:
    """Retorna cliente PRAW si hay credenciales, si no None."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        return praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
    return None


def _fetch_public(subreddit: str, feed: str = "hot", limit: int = 20) -> list[dict]:
    """
    Endpoint JSON público de Reddit — sin API key.
    Funciona sin credenciales, 100% gratuito.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{feed}.json?limit={limit}"
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": REDDIT_USER_AGENT},
            timeout=10,
        )
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
        logger.warning(f"Reddit público r/{subreddit}/{feed}: {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
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
                    logger.warning(f"PRAW r/{sub} → fallback público: {e}")
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
```

---

## PASO 2.2 — `scrapers/google_trends.py`

```python
# scrapers/google_trends.py
import requests
import xml.etree.ElementTree as ET
import time
from loguru import logger
from core.query import TrendQuery


def _fetch_rss(geo: str) -> list[dict]:
    """
    RSS público de Google Trends — primario.
    Sin JavaScript, sin captcha, sin autenticación.
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
            results.append({
                "source": "google_trends_rss",
                "keyword": title,
                "approx_traffic": traffic,
                "geo": geo,
            })
        logger.info(f"Google Trends RSS ({geo}): {len(results)} tendencias")
        return results
    except Exception as e:
        logger.warning(f"Google Trends RSS falló: {e} → activando pytrends")
        return []


def _fetch_pytrends(keywords: list[str], geo: str) -> list[dict]:
    """
    Fallback pytrends para keywords específicas.
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

    except Exception as e:
        logger.error(f"pytrends completamente fallido: {e}")
        return []


def run(query: TrendQuery) -> list[dict]:
    # Intentar RSS primero, pytrends como fallback
    results = _fetch_rss(query.geo) or _fetch_pytrends(query.keywords, query.geo)

    # Filtrar por relevancia si hay keywords
    if query.keywords and results:
        kws = [k.lower() for k in query.keywords]
        filtered = [r for r in results if any(k in r.get("keyword", "").lower() for k in kws)]
        return filtered or results

    return results
```

---

## PASO 2.3 — `scrapers/twitter.py`

```python
# scrapers/twitter.py
# Usa xactions-py — github.com/mamboyepez17/xactions-py
from loguru import logger
from config import TWITTER_AUTH_TOKEN, TWITTER_CT0
from core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
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

        for keyword in query.keywords[:4]:  # Máx 4 para no saturar
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
                logger.warning(f"Twitter búsqueda '{keyword}': {e}")

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
```

---

## PASO 2.4 — `scrapers/amazon.py`

```python
# scrapers/amazon.py
# Usa Scrapling StealthyFetcher — bypassa anti-bot de Amazon
import time
import random
from loguru import logger
from config import AMAZON_URLS_BY_CATEGORY
from core.query import TrendQuery


def run(query: TrendQuery) -> list[dict]:
    cat = query.category if query.category in AMAZON_URLS_BY_CATEGORY else "default"
    url = AMAZON_URLS_BY_CATEGORY[cat]
    results: list[dict] = []

    try:
        from scrapling.fetchers import StealthyFetcher

        page = StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            auto_match=True,  # Scrapling aprende de cambios en el DOM
        )

        # Scrapling usa selectores CSS igual que BS4 pero más rápido
        items = page.css(".zg-grid-general-faceout")

        for item in items[:15]:
            title_el = item.css_first(
                "._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, .p13n-sc-truncated"
            )
            price_el = item.css_first(".p13n-sc-price")
            rank_el  = item.css_first(".zg-bdg-text")

            if title_el:
                results.append({
                    "source": "amazon_bestsellers",
                    "category": cat,
                    "title": title_el.text.strip(),
                    "price": price_el.text.strip() if price_el else "N/A",
                    "rank":  rank_el.text.strip()  if rank_el  else "N/A",
                    "url":   url,
                })

        time.sleep(random.uniform(2, 4))

    except Exception as e:
        logger.error(f"Amazon '{cat}': {e}")

    logger.info(f"Amazon '{cat}': {len(results)} productos")
    return results
```

---

## PASO 2.5 — `scrapers/tiktok.py`

```python
# scrapers/tiktok.py
# Usa Scrapling DynamicFetcher — maneja JS pesado de TikTok
from loguru import logger
from core.query import TrendQuery

TIKTOK_URL = "https://ads.tiktok.com/business/creativecenter/inspiration/popular/pc/en"


def run(query: TrendQuery) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    try:
        from scrapling.fetchers import DynamicFetcher

        page = DynamicFetcher.fetch(
            TIKTOK_URL,
            headless=True,
            network_idle=True,
            timeout=40000,
        )

        # Intentar múltiples selectores — TikTok cambia su DOM frecuentemente
        # Scrapling con auto_match=True reubica elementos si cambian
        selectors = [
            "[class*='hashtagName']",
            "[class*='trend-name']",
            "[class*='TopicName']",
            "[class*='hashtag']",
        ]

        for selector in selectors:
            for el in page.css(selector):
                text = el.text.strip()
                if text and text not in seen and len(text) > 2:
                    seen.add(text)
                    results.append({
                        "source": "tiktok_trending",
                        "keyword": text,
                        "type": "hashtag",
                    })

    except Exception as e:
        logger.error(f"TikTok: {e}")

    logger.info(f"TikTok: {len(results)} hashtags trending")
    return results
```

---

## PASO 2.6 — Validación individual de cada scraper

```bash
cd trendscope

# Test Reddit (usa JSON público, no necesita credenciales)
python -c "
from core.query import TrendQuery
from scrapers.reddit import run

query = TrendQuery(mode='category', category='tecnologia')
items = run(query)
print(f'✅ Reddit: {len(items)} items')
if items:
    print(f'   Ejemplo: {items[0][\"title\"][:60]}')
"

# Test Google Trends (RSS público)
python -c "
from core.query import TrendQuery
from scrapers.google_trends import run

query = TrendQuery(mode='free', free_topic='tecnologia Colombia')
items = run(query)
print(f'✅ Google Trends: {len(items)} items')
if items:
    print(f'   Ejemplo: {items[0].get(\"keyword\",\"\")}')
"

# Test Twitter (sin credenciales retorna [] sin error)
python -c "
from core.query import TrendQuery
from scrapers.twitter import run

query = TrendQuery(mode='free', free_topic='crypto')
items = run(query)
print(f'✅ Twitter: {len(items)} items ([] si sin credenciales — OK)')
"

# Test Amazon (Scrapling StealthyFetcher)
python -c "
from core.query import TrendQuery
from scrapers.amazon import run

query = TrendQuery(mode='category', category='tecnologia')
items = run(query)
print(f'✅ Amazon: {len(items)} items')
if items:
    print(f'   Ejemplo: {items[0][\"title\"][:60]}')
"

# Test TikTok (Scrapling DynamicFetcher)
python -c "
from core.query import TrendQuery
from scrapers.tiktok import run

query = TrendQuery(mode='free', free_topic='tendencias')
items = run(query)
print(f'✅ TikTok: {len(items)} items')
if items:
    print(f'   Ejemplo: {items[0][\"keyword\"]}')
"
```

---

## PASO 2.7 — Actualizar CHANGELOG

Agregar en `.context/CHANGELOG.md`:

```markdown
## [0.3.0] — FECHA — MODELO_USADO

### Añadido
- scrapers/reddit.py: PRAW + JSON público fallback, filtro por keywords
- scrapers/google_trends.py: RSS primario + pytrends fallback
- scrapers/twitter.py: xactions-py, maneja credenciales faltantes
- scrapers/amazon.py: Scrapling StealthyFetcher con auto_match
- scrapers/tiktok.py: Scrapling DynamicFetcher, múltiples selectores

### Pendiente
- Bloque 3: Análisis (scorer, deduplicator, sentimiento)
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 2

- [ ] `scrapers/reddit.py` — retorna items (con o sin credenciales)
- [ ] `scrapers/google_trends.py` — retorna items del RSS
- [ ] `scrapers/twitter.py` — retorna [] sin error si sin credenciales
- [ ] `scrapers/amazon.py` — retorna items con Scrapling
- [ ] `scrapers/tiktok.py` — retorna items con Scrapling
- [ ] Ningún scraper lanza excepción al pipeline
- [ ] CHANGELOG actualizado

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 2 COMPLETADO

Scrapers validados:
- Reddit        ✅ (X items)
- Google Trends ✅ (X items)
- Twitter/X     ✅ (X items o [] sin credenciales)
- Amazon        ✅ (X items — Scrapling)
- TikTok        ✅ (X items — Scrapling)

¿Aprobado para continuar al Bloque 3 — Análisis y Sentimiento?
```

---

*TrendScope — Bloque 2 de 7 | Siguiente: BLOQUE_3_ANALISIS.md*
