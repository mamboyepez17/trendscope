# 🏗️ TRENDSCOPE — BLOQUE 1 DE 7
## Base del proyecto
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 1 de 7. Construyes la base completa del proyecto:
estructura de carpetas, dependencias, configuración central y el
modelo de consulta TrendQuery.

**Prerequisito:** Bloque 0 aprobado. Si no existe `.context/`, detente
y ejecuta primero BLOQUE_0_CONTEXTO.md

**Reglas:**
- Instalar dependencias y verificar que importan correctamente
- Al final correr la validación del bloque
- NO pasar al Bloque 2 sin confirmación del usuario

---

## PASO 1.1 — Crear estructura de carpetas

```bash
cd trendscope
mkdir -p core scrapers sentiment analyzer output data
touch core/__init__.py
touch scrapers/__init__.py
touch sentiment/__init__.py
touch analyzer/__init__.py
touch output/__init__.py
touch data/.gitkeep
```

---

## PASO 1.2 — Crear `requirements.txt`

```txt
# Scraping adaptativo (reemplaza playwright + requests + beautifulsoup4)
scrapling

# Reddit
praw==7.8.1

# Google Trends fallback
pytrends==4.9.2

# Sentimiento español latinoamericano
pysentimiento==0.7.4

# Claude API (sentimiento premium)
anthropic>=0.25.0

# API REST
fastapi==0.111.0
uvicorn==0.30.0

# MCP (OpenClaw)
mcp[cli]>=1.0.0

# Utils
python-dotenv==1.0.1
loguru==0.7.2
rich==13.7.1
```

Instalar:
```bash
pip install -r requirements.txt --break-system-packages
pip install git+https://github.com/mamboyepez17/xactions-py.git --break-system-packages
```

---

## PASO 1.3 — Crear `config.py`

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ── Credenciales ──────────────────────────────────────────────────────
REDDIT_CLIENT_ID     = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT    = os.getenv("REDDIT_USER_AGENT", "TrendScope/1.0")

TWITTER_AUTH_TOKEN   = os.getenv("TWITTER_AUTH_TOKEN", "")
TWITTER_CT0          = os.getenv("TWITTER_CT0", "")

ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")

# ── Motor de sentimiento ──────────────────────────────────────────────
# "local"  = pysentimiento (gratis, corre en CPU/GPU)
# "claude" = Claude Haiku API (premium, más preciso)
SENTIMENT_ENGINE_DEFAULT = os.getenv("SENTIMENT_ENGINE", "local")

# ── General ───────────────────────────────────────────────────────────
GEO_TARGET = "CO"
TOP_N      = 25
DATA_DIR   = "data"

# ── Servidores ────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# ── Categorías predefinidas ───────────────────────────────────────────
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
```

---

## PASO 1.4 — Crear `core/query.py`

```python
# core/query.py
from dataclasses import dataclass, field
from typing import Optional
from config import (
    CATEGORIES,
    SUBREDDITS_BY_CATEGORY,
    SENTIMENT_ENGINE_DEFAULT,
    TOP_N,
    GEO_TARGET,
)


@dataclass
class TrendQuery:
    """
    Modelo de consulta del usuario.
    Representa QUÉ analizar, CÓMO y con qué configuración.
    """
    mode: str                          # "category" | "free"
    category: Optional[str] = None    # clave de CATEGORIES
    free_topic: Optional[str] = None  # tema libre del usuario
    geo: str = GEO_TARGET
    top_n: int = TOP_N
    sentiment_engine: str = SENTIMENT_ENGINE_DEFAULT

    @property
    def keywords(self) -> list[str]:
        """Keywords para buscar en todas las fuentes."""
        if self.mode == "category" and self.category in CATEGORIES:
            return CATEGORIES[self.category]
        elif self.mode == "free" and self.free_topic:
            t = self.free_topic.strip()
            return [t, f"{t} Colombia", f"{t} 2026", f"tendencias {t}"]
        return []

    @property
    def subreddits(self) -> list[str]:
        """Subreddits relevantes según la categoría."""
        if self.mode == "category" and self.category in SUBREDDITS_BY_CATEGORY:
            return SUBREDDITS_BY_CATEGORY[self.category]
        return SUBREDDITS_BY_CATEGORY["libre"]

    @property
    def display_name(self) -> str:
        """Nombre legible para mostrar en CLI y reportes."""
        if self.mode == "category":
            return f"Categoría: {self.category}"
        return f"Tema libre: {self.free_topic}"

    @property
    def topic_slug(self) -> str:
        """Slug para nombres de archivos de output."""
        topic = self.free_topic or self.category or "general"
        return topic.strip().replace(" ", "_")[:30]
```

---

## PASO 1.5 — Crear `.env.example`

```env
# Reddit FREE tier — crear en reddit.com/prefs/apps
REDDIT_CLIENT_ID=tu_client_id
REDDIT_CLIENT_SECRET=tu_client_secret
REDDIT_USER_AGENT=TrendScope/1.0

# Twitter/X — DevTools > Application > Cookies en twitter.com
TWITTER_AUTH_TOKEN=tu_auth_token
TWITTER_CT0=tu_ct0

# Claude API — para sentimiento premium (opcional)
ANTHROPIC_API_KEY=tu_api_key

# Motor de sentimiento por defecto: local | claude
SENTIMENT_ENGINE=local

# API REST
API_HOST=0.0.0.0
API_PORT=8000
```

---

## PASO 1.6 — Crear `.gitignore`

```
# Privado — nunca al repo
.env
.env.*
.context/
data/
*.log

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.venv/
venv/

# Playwright (ya no se usa pero por si acaso)
.playwright/
```

---

## PASO 1.7 — Crear `.env` de prueba

```bash
cp .env.example .env
# El .env puede quedar con valores vacíos para pruebas
# Los scrapers manejan credenciales faltantes con fallbacks
```

---

## PASO 1.8 — Validación del Bloque 1

```bash
# 1. Verificar estructura de carpetas
find trendscope -type f -name "*.py" | sort

# 2. Verificar que config.py carga sin errores
cd trendscope
python -c "
import config
print('✅ config.py OK')
print(f'   GEO_TARGET: {config.GEO_TARGET}')
print(f'   TOP_N: {config.TOP_N}')
print(f'   SENTIMENT_ENGINE: {config.SENTIMENT_ENGINE_DEFAULT}')
print(f'   Categorías: {list(config.CATEGORIES.keys())}')
"

# 3. Verificar TrendQuery
python -c "
from core.query import TrendQuery

# Test categoría
q1 = TrendQuery(mode='category', category='tecnologia')
print(f'✅ TrendQuery categoría OK')
print(f'   keywords: {q1.keywords}')
print(f'   subreddits: {q1.subreddits}')
print(f'   slug: {q1.topic_slug}')

# Test tema libre
q2 = TrendQuery(mode='free', free_topic='mercado inmobiliario Colombia')
print(f'✅ TrendQuery libre OK')
print(f'   keywords: {q2.keywords}')
print(f'   slug: {q2.topic_slug}')
"

# 4. Verificar dependencias principales
python -c "
import praw; print('✅ praw OK')
import rich; print('✅ rich OK')
import loguru; print('✅ loguru OK')
import fastapi; print('✅ fastapi OK')
import scrapling; print('✅ scrapling OK')
"
```

Todo debe pasar sin errores antes de reportar.

---

## PASO 1.9 — Actualizar CHANGELOG

Agregar en `.context/CHANGELOG.md`:

```markdown
## [0.2.0] — FECHA — MODELO_USADO

### Añadido
- Estructura de carpetas completa (core, scrapers, sentiment, analyzer, output, data)
- requirements.txt con stack completo (Scrapling, PRAW, pytrends, etc.)
- config.py: configuración central con categorías, subreddits y URLs de Amazon
- core/query.py: TrendQuery dataclass con keywords, subreddits y topic_slug
- .env.example: template de credenciales
- .gitignore: excluye .env, data/, .context/

### Pendiente
- Bloque 2: Scrapers (Reddit, Google Trends, Twitter, Amazon, TikTok)
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 1

- [ ] Estructura de carpetas creada con todos los `__init__.py`
- [ ] `requirements.txt` instalado sin errores
- [ ] xactions-py instalado desde GitHub
- [ ] `config.py` carga sin errores
- [ ] `TrendQuery` modo categoría funciona correctamente
- [ ] `TrendQuery` modo libre funciona correctamente
- [ ] `.env.example` y `.gitignore` creados
- [ ] CHANGELOG actualizado
- [ ] Todos los checks de validación pasan ✅

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 1 COMPLETADO

Creado:
- Estructura de carpetas (core, scrapers, sentiment, analyzer, output)
- requirements.txt instalado correctamente
- config.py con X categorías predefinidas
- core/query.py — TrendQuery (categoría + libre)
- .env.example y .gitignore

Validación:
- config.py ✅
- TrendQuery categoría ✅
- TrendQuery libre ✅
- Dependencias principales ✅

¿Aprobado para continuar al Bloque 2 — Scrapers?
```

---

*TrendScope — Bloque 1 de 7 | Siguiente: BLOQUE_2_SCRAPERS.md*
