# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# -- Credenciales ----------------------------------------------------------
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "TrendScope/1.0")

TWITTER_AUTH_TOKEN   = os.getenv("TWITTER_AUTH_TOKEN", "")
TWITTER_CT0          = os.getenv("TWITTER_CT0", "")
TWEETCLAW_RESULTS_FILE = os.getenv("TWEETCLAW_RESULTS_FILE", "")

ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")

# -- Motor de sentimiento --------------------------------------------------
# "local"  = pysentimiento (gratis, corre en CPU/GPU)
# "claude" = Claude Haiku API (premium, mas preciso)
SENTIMENT_ENGINE_DEFAULT = os.getenv("SENTIMENT_ENGINE", "local")

# -- General ----------------------------------------------------------------
GEO_TARGET = os.getenv("GEO_TARGET", "CO")
TOP_N      = int(os.getenv("TOP_N", "25"))
DATA_DIR   = "data"

# -- Servidores -------------------------------------------------------------
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# -- Categorias predefinidas ------------------------------------------------
CATEGORIES: dict[str, list[str]] = {
    "tecnologia":     ["tech news", "gadgets 2026", "inteligencia artificial", "startups"],
    "economia":       ["mercado colombiano", "inversiones Colombia", "finanzas personales"],
    "salud":          ["salud bienestar", "medicina Colombia", "fitness trends"],
    "moda":           ["moda Colombia 2026", "tendencias ropa", "streetwear"],
    "deportes":       ["deportes Colombia", "futbol colombiano", "fitness"],
    "politica":       ["politica Colombia 2026", "gobierno Colombia"],
    "emprendimiento": ["emprendimiento Colombia", "negocios online", "dropshipping"],
    "educacion":      ["educacion Colombia", "cursos online", "aprendizaje"],
    "inmobiliario":   ["finca raiz Colombia", "arriendos Bogota", "vivienda"],
    "crypto":         ["crypto Colombia", "bitcoin tendencias", "web3"],
}

SUBREDDITS_BY_CATEGORY: dict[str, list[str]] = {
    "tecnologia":     ["technology", "artificial", "gadgets", "programming"],
    "economia":       ["economics", "investing", "personalfinance", "stocks"],
    "salud":          ["health", "Fitness", "nutrition", "medical"],
    "moda":           ["femalefashionadvice", "malefashionadvice", "streetwear"],
    "deportes":       ["sports", "soccer", "fitness"],
    "politica":       ["worldnews", "politics", "colombia"],
    "emprendimiento": ["entrepreneur", "dropshipping", "ecommerce", "shutupandtakemymoney"],
    "educacion":      ["learnprogramming", "languagelearning", "edtech"],
    "inmobiliario":   ["realestate", "personalfinance"],
    "crypto":         ["CryptoCurrency", "Bitcoin", "ethereum", "defi"],
    "libre":          ["worldnews", "technology", "science", "business"],
}

AMAZON_URLS_BY_CATEGORY: dict[str, str] = {
    "tecnologia":     "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/",
    "salud":          "https://www.amazon.com/Best-Sellers-Health-Personal-Care/zgbs/hpc/",
    "deportes":       "https://www.amazon.com/Best-Sellers-Sports-Outdoors/zgbs/sporting-goods/",
    "moda":           "https://www.amazon.com/Best-Sellers-Clothing-Shoes-Jewelry/zgbs/fashion/",
    "emprendimiento": "https://www.amazon.com/Best-Sellers-Books-Business/zgbs/books/173514011",
    "default":        "https://www.amazon.com/Best-Sellers/zgbs/",
}
