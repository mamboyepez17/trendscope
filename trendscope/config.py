"""Re-export de configuración legacy para compatibilidad."""

from trendscope.settings import settings


def _parse_twitter_cookies(raw: str) -> tuple[str, str]:
    """Extrae auth_token y ct0 de un cookie string (o varias cookies separadas por |||)."""
    auth, ct0 = "", ""
    if not raw:
        return auth, ct0
    # xactions permite varias cuentas con |||; usamos la primera
    first = raw.split("|||")[0]
    for part in first.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, value = part.split("=", 1)
        name = name.strip().lower()
        if name == "auth_token" and not auth:
            auth = value.strip()
        elif name == "ct0" and not ct0:
            ct0 = value.strip()
    return auth, ct0


_COOKIE_AUTH, _COOKIE_CT0 = _parse_twitter_cookies(settings.twitter_cookies)

REDDIT_CLIENT_ID = settings.reddit_client_id
REDDIT_CLIENT_SECRET = settings.reddit_client_secret
REDDIT_USER_AGENT = settings.reddit_user_agent  # TrendScope/1.5.0 default

TWITTER_AUTH_TOKEN = settings.twitter_auth_token or _COOKIE_AUTH
TWITTER_CT0 = settings.twitter_ct0 or _COOKIE_CT0
TWEETCLAW_RESULTS_FILE = settings.tweetclaw_results_file

ANTHROPIC_API_KEY = settings.anthropic_api_key

SENTIMENT_ENGINE_DEFAULT = settings.sentiment_engine

GEO_TARGET = settings.geo_target
TOP_N = settings.top_n
DATA_DIR = settings.data_dir

API_HOST = settings.api_host
API_PORT = settings.api_port

CACHET_TTL_SECONDS = settings.cache_ttl_seconds

CATEGORIES: dict[str, list[str]] = {
    "tecnologia": ["tech news", "gadgets 2026", "inteligencia artificial", "startups"],
    "economia": ["mercado colombiano", "inversiones Colombia", "finanzas personales"],
    "salud": ["salud bienestar", "medicina Colombia", "fitness trends"],
    "moda": ["moda Colombia 2026", "tendencias ropa", "streetwear"],
    "deportes": ["deportes Colombia", "futbol colombiano", "fitness"],
    "politica": ["politica Colombia 2026", "gobierno Colombia"],
    "emprendimiento": ["emprendimiento Colombia", "negocios online", "dropshipping"],
    "educacion": ["educacion Colombia", "cursos online", "aprendizaje"],
    "inmobiliario": ["finca raiz Colombia", "arriendos Bogota", "vivienda"],
    "crypto": ["crypto Colombia", "bitcoin tendencias", "web3"],
}

SUBREDDITS_BY_CATEGORY: dict[str, list[str]] = {
    "tecnologia": ["technology", "artificial", "gadgets", "programming"],
    "economia": ["economics", "investing", "personalfinance", "stocks"],
    "salud": ["health", "Fitness", "nutrition", "medical"],
    "moda": ["femalefashionadvice", "malefashionadvice", "streetwear"],
    "deportes": ["sports", "soccer", "fitness"],
    "politica": ["worldnews", "politics", "colombia"],
    "emprendimiento": ["entrepreneur", "dropshipping", "ecommerce", "shutupandtakemymoney"],
    "educacion": ["learnprogramming", "languagelearning", "edtech"],
    "inmobiliario": ["realestate", "personalfinance"],
    "crypto": ["CryptoCurrency", "Bitcoin", "ethereum", "defi"],
    "libre": ["worldnews", "technology", "science", "business"],
}

AMAZON_URLS_BY_CATEGORY: dict[str, str] = {
    "tecnologia": "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "salud": "https://www.amazon.com/Best-Sellers-Health-Personal-Care/zgbs/hpc/",
    "deportes": "https://www.amazon.com/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods/",
    "moda": "https://www.amazon.com/Best-Sellers-Clothing-Shoes-Jewelry/zgbs/fashion/",
    "emprendimiento": "https://www.amazon.com/Best-Sellers-Books-Business/zgbs/books/173514011",
    "default": "https://www.amazon.com/Best-Sellers/zgbs/",
}
