# TrendScope Evolution — Plan Maestro de Implementación

> **Versión:** 1.0.0  
> **Fecha:** 2026-07-23  
> **Autor:** mamboyepez17 + Hermes Agent  
> **Objetivo:** Transformar TrendScope de un script funcional a una plataforma de trend intelligence instalable, persistente, inteligente (LLM local) y monitoreable.

---

## Filosofía de trabajo

- Un bloque a la vez. Bloque terminado, probado, verificado y commiteado antes de pasar al siguiente.
- Cada tarea es de 2–5 minutos máximo.
- TDD siempre que sea posible: test rojo → implementación mínima → test verde.
- Sin features de más (YAGNI). Solo lo que necesitamos ahora.
- Commits frecuentes con mensajes claros en español + conventional commits.

---

## Resumen de bloques

| Bloque | Nombre | Objetivo | Impacto |
|--------|--------|----------|---------|
| 0 | Fundamentos del repo | Arreglar Git, limpiar basura, `.gitignore`, unificar estructura | Alto |
| 1 | Paquete instalable | `pyproject.toml`, entry points, imports absolutos, tests pasando | Alto |
| 2 | Configuración robusta | Reemplazar `config.py` plano por `pydantic-settings` | Alto |
| 3 | Cache persistente | SQLite para cache de resultados con TTL | Alto |
| 4 | Narrador con Ollama | Generar resúmenes ejecutivos y reportes narrativos con LLM local | Revolucionario |
| 5 | Watchlist + monitoreo | Temas recurrentes, scheduler, historial, alertas básicas | Diferenciador |
| 6 | Dashboard real-time | WebSockets, historial, comparación temporal | Diferenciador |
| 7 | Docker + CI/CD | Dockerfile, docker-compose, GitHub Actions tests | Escalabilidad |

---

## Estado

- [ ] Bloque 0 — Fundamentos del repo
- [ ] Bloque 1 — Paquete instalable
- [ ] Bloque 2 — Configuración robusta
- [ ] Bloque 3 — Cache persistente
- [ ] Bloque 4 — Narrador con Ollama
- [ ] Bloque 5 — Watchlist + monitoreo
- [ ] Bloque 6 — Dashboard real-time
- [ ] Bloque 7 — Docker + CI/CD

---

# BLOQUE 0 — Fundamentos del repo

**Objetivo:** El repositorio local debe coincidir con GitHub, estar limpio y listo para desarrollo profesional.

**Entregables:**
1. Estructura de carpetas unificada (raíz = repo).
2. `.gitignore` completo.
3. Archivos compilados y `data/` eliminados del control de versiones.
4. Repo inicializado con remote apuntando a GitHub.
5. Primer commit limpio.

### Tarea 0.1: Mover contenido a la raíz
**Archivos:**
- Mover todo el contenido de `D:/Proyectos/TrendScope/trendscope/` a `D:/Proyectos/TrendScope/`.
- Eliminar la carpeta `trendscope/` vacía.

**Verificación:**
```bash
cd /d/Proyectos/TrendScope
ls
# Debe mostrar: analyzer, core, scrapers, sentiment, tests, xactions, main.py, config.py, server_api.py, server_mcp.py, dashboard.html, requirements.txt, README.md, SKILL.md, LICENSE
```

### Tarea 0.2: Crear `.gitignore` correcto
**Archivo:** `.gitignore`

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
ENV/

# Data y outputs generados
data/
*.json
*.md
!README.md
!SKILL.md
!Implementation_Plan/*.md
!docs/**/*.md

# Entorno
.env
.env.local

# Herramientas
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.log
.coverage
htmlcov/
dist/
build/
*.egg-info/

# IDEs
.vscode/
.idea/
*.swp
*.swo
```

**Verificación:**
```bash
git status --short
# No debe aparecer __pycache__, data/, .pyc
```

### Tarea 0.3: Eliminar archivos compilados y data del árbol
**Comando:**
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -name "*.pyc" -delete
find . -name "*.pyo" -delete
rm -rf data/
```

**Verificación:**
```bash
find . -type d -name __pycache__ | wc -l
# Debe devolver 0
ls data/ 2>&1 | grep "No such file"
```

### Tarea 0.4: Inicializar Git y conectar con GitHub
**Comandos:**
```bash
git init
git remote add origin https://github.com/mamboyepez17/trendscope.git
git fetch origin main
git branch --set-upstream-to=origin/main main
```

**Verificación:**
```bash
git remote -v
# origin  https://github.com/mamboyepez17/trendscope.git (fetch)
# origin  https://github.com/mamboyepez17/trendscope.git (push)

git status
# Debe mostrar archivos listos para staging
```

### Tarea 0.5: Primer commit limpio
**Comandos:**
```bash
git add .
git commit -m "chore(repo): estructura limpia, .gitignore y sync con GitHub"
git push origin main
```

**Verificación:**
```bash
git log --oneline -1
# muestra el commit
```

---

# BLOQUE 1 — Paquete instalable

**Objetivo:** Convertir TrendScope en un paquete Python instalable con entry points para CLI, API y MCP.

**Entregables:**
1. `pyproject.toml` con metadatos, dependencias y scripts.
2. Módulo `trendscope/` con `__init__.py`.
3. Imports absolutos en todos los archivos.
4. Scripts: `trendscope`, `trendscope-api`, `trendscope-mcp`.
5. Tests corriendo con `pytest` desde la raíz.

### Tarea 1.1: Crear `pyproject.toml`
**Archivo:** `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "trendscope"
version = "1.4.0"
description = "Universal trend intelligence infrastructure"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "mamboyepez17"}
]
requires-python = ">=3.10"
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "scrapling",
    "praw>=7.8.1",
    "pytrends>=4.9.2",
    "pysentimiento>=0.7.3",
    "anthropic>=0.25.0",
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "mcp[cli]>=1.0.0",
    "python-dotenv>=1.0.1",
    "loguru>=0.7.2",
    "rich>=13.7.1",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "tenacity>=8.3.0",
    "apscheduler>=3.10.0",
    "websockets>=12.0",
    "ollama>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]

[project.scripts]
trendscope = "trendscope.main:main"
trendscope-api = "trendscope.server_api:run"
trendscope-mcp = "trendscope.server_mcp:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["trendscope*"]
exclude = ["tests*", "data*"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

**Verificación:**
```bash
python -m pip install -e .
# Debe instalar sin errores
```

### Tarea 1.2: Mover todo el código a `trendscope/`
**Estructura objetivo:**
```
D:/Proyectos/TrendScope/
├── trendscope/
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py
│   ├── config.py
│   ├── server_api.py
│   ├── server_mcp.py
│   ├── dashboard.html
│   ├── analyzer/
│   ├── core/
│   ├── output/
│   ├── scrapers/
│   ├── sentiment/
│   ├── tests/
│   └── xactions/
├── pyproject.toml
├── README.md
├── SKILL.md
├── LICENSE
├── .env.example
├── .gitignore
└── Implementation_Plan/
```

**Verificación:**
```bash
ls trendscope/
# Debe mostrar main.py, config.py, analyzer, core, etc.
```

### Tarea 1.3: Actualizar imports a absolutos
**Cambio general:**
- `from config import ...` → `from trendscope.config import ...`
- `from core.query import ...` → `from trendscope.core.query import ...`
- `from analyzer.scorer import ...` → `from trendscope.analyzer.scorer import ...`
- etc.

**Archivos a modificar:** todos los `.py` dentro de `trendscope/`.

**Verificación:**
```bash
grep -R "^from \(config\|core\|analyzer\|scrapers\|sentiment\|output\|xactions\)" trendscope/
# No debe devolver resultados (o solo en __init__.py si aplica)
```

### Tarea 1.4: Crear `__main__.py` para `python -m trendscope`
**Archivo:** `trendscope/__main__.py`

```python
from trendscope.main import main

if __name__ == "__main__":
    main()
```

**Verificación:**
```bash
python -m trendscope --help
# Debe mostrar el banner o menú interactivo
```

### Tarea 1.5: Actualizar scripts y ejecutables
**Archivo:** `trendscope/server_api.py`

Agregar al final:
```python
def run():
    import uvicorn
    uvicorn.run("trendscope.server_api:app", host=API_HOST, port=API_PORT, reload=False)

if __name__ == "__main__":
    run()
```

**Archivo:** `trendscope/server_mcp.py`

Agregar:
```python
def main():
    asyncio.run(main_async())
```

Renombrar `main()` actual a `main_async()`.

**Verificación:**
```bash
trendscope --help
trendscope-api &
curl http://localhost:8000/health
```

### Tarea 1.6: Ejecutar tests y corregir imports rotos
**Comando:**
```bash
python -m pytest trendscope/tests/ -v
```

**Verificación:**
```bash
# Debe mostrar 49 passed
```

### Tarea 1.7: Commit
```bash
git add .
git commit -m "build: paquete instalable con pyproject.toml y entry points"
```

---

# BLOQUE 2 — Configuración robusta

**Objetivo:** Reemplazar `config.py` plano y mutable por un sistema de configuración tipado, validado y testeable.

**Entregables:**
1. `trendscope/settings.py` con `pydantic-settings`.
2. Eliminar `trendscope/config.py` (o convertirlo en re-export).
3. Todos los módulos usan `from trendscope.settings import settings`.
4. Tests para validación de settings.

### Tarea 2.1: Crear `trendscope/settings.py`
**Archivo:** `trendscope/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "TrendScope/1.4.0"

    # Twitter/X
    twitter_auth_token: str = ""
    twitter_ct0: str = ""
    tweetclaw_results_file: str = ""

    # Claude
    anthropic_api_key: str = ""

    # Engine
    sentiment_engine: str = "local"

    # General
    geo_target: str = "CO"
    top_n: int = 25
    data_dir: str = "data"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Ollama
    ollama_enabled: bool = True
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:9b"

    # Cache
    cache_ttl_seconds: int = 300


settings = Settings()
```

### Tarea 2.2: Actualizar `trendscope/config.py` como re-export
**Archivo:** `trendscope/config.py`

```python
from trendscope.settings import settings

REDDIT_CLIENT_ID = settings.reddit_client_id
REDDIT_CLIENT_SECRET = settings.reddit_client_secret
REDDIT_USER_AGENT = settings.reddit_user_agent
TWITTER_AUTH_TOKEN = settings.twitter_auth_token
TWITTER_CT0 = settings.twitter_ct0
TWEETCLAW_RESULTS_FILE = settings.tweetclaw_results_file
ANTHROPIC_API_KEY = settings.anthropic_api_key
SENTIMENT_ENGINE_DEFAULT = settings.sentiment_engine
GEO_TARGET = settings.geo_target
TOP_N = settings.top_n
DATA_DIR = settings.data_dir
API_HOST = settings.api_host
API_PORT = settings.api_port

# Categorías se mantienen aquí por simplicidad
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
```

### Tarea 2.3: Actualizar `.env.example`
**Archivo:** `.env.example`

```env
# Reddit (optional)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=TrendScope/1.4.0

# Twitter/X (cookies)
TWITTER_AUTH_TOKEN=
TWITTER_CT0=

# TweetClaw JSON (optional)
TWEETCLAW_RESULTS_FILE=

# Claude (optional)
ANTHROPIC_API_KEY=

# Sentiment: local | claude
SENTIMENT_ENGINE=local

# General
GEO_TARGET=CO
TOP_N=25
DATA_DIR=data

# API
API_HOST=0.0.0.0
API_PORT=8000

# Ollama local
OLLAMA_ENABLED=true
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3.5:9b

# Cache
CACHE_TTL_SECONDS=300
```

### Tarea 2.4: Test de settings
**Archivo:** `trendscope/tests/test_settings.py`

```python
import unittest
from trendscope.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        s = Settings(_env_file=None)
        self.assertEqual(s.geo_target, "CO")
        self.assertEqual(s.top_n, 25)
        self.assertEqual(s.sentiment_engine, "local")
        self.assertTrue(s.ollama_enabled)

    def test_env_override(self):
        s = Settings(_env_file=None, geo_target="US", top_n=50)
        self.assertEqual(s.geo_target, "US")
        self.assertEqual(s.top_n, 50)


if __name__ == "__main__":
    unittest.main()
```

**Verificación:**
```bash
python -m pytest trendscope/tests/test_settings.py -v
```

### Tarea 2.5: Commit
```bash
git add .
git commit -m "feat(config): configuración tipada con pydantic-settings"
```

---

# BLOQUE 3 — Cache persistente

**Objetivo:** Reemplazar el cache en memoria por SQLite persistente, con TTL, stats y limpieza automática.

**Entregables:**
1. `trendscope/core/persistent_cache.py` con SQLite.
2. Reemplazar uso de `core/cache.py` en pipeline y API.
3. Tests del cache persistente.
4. Backward-compatible API endpoints.

### Tarea 3.1: Implementar cache persistente
**Archivo:** `trendscope/core/persistent_cache.py`

```python
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from trendscope.settings import settings


class PersistentCache:
    """Cache persistente en SQLite con TTL."""

    def __init__(self, db_path: str | Path | None = None, ttl: int | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/cache.db")
        self.ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    ts REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_ts ON cache(ts)")

    def get(self, key: str) -> Any | None:
        with sqlite3.connect(self.path) as conn:
            row = conn.execute(
                "SELECT value, ts FROM cache WHERE key = ?", (key,)
            ).fetchone()
            if not row:
                return None
            value, ts = row
            if time.time() - ts > self.ttl:
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                return None
            return json.loads(value)

    def set(self, key: str, value: Any) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, value, ts) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False, default=str), time.time()),
            )

    def clear(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("DELETE FROM cache")

    def stats(self) -> dict:
        with sqlite3.connect(self.path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
            now = time.time()
            valid = conn.execute(
                "SELECT COUNT(*) FROM cache WHERE ? - ts <= ?", (now, self.ttl)
            ).fetchone()[0]
        return {"total_entries": total, "valid_entries": valid, "ttl_seconds": self.ttl}

    def cleanup(self) -> int:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute("DELETE FROM cache WHERE ? - ts > ?", (time.time(), self.ttl))
            return cur.rowcount


cache = PersistentCache()
```

### Tarea 3.2: Re-export legacy
**Archivo:** `trendscope/core/cache.py`

```python
from trendscope.core.persistent_cache import PersistentCache, cache

get = cache.get
set = cache.set
clear = cache.clear
stats = cache.stats
```

### Tarea 3.3: Actualizar pipeline para usar cache persistente
**Archivo:** `trendscope/core/pipeline.py`

Reemplazar:
```python
from trendscope.core.cache import get as cache_get, set as cache_set
```

(No debería requerir más cambios por el re-export.)

### Tarea 3.4: Tests
**Archivo:** `trendscope/tests/test_persistent_cache.py`

```python
import unittest
import tempfile
from pathlib import Path

from trendscope.core.persistent_cache import PersistentCache


class PersistentCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.cache = PersistentCache(db_path=self.tmp.name, ttl=2)

    def tearDown(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_set_and_get(self):
        self.cache.set("k1", {"a": 1})
        self.assertEqual(self.cache.get("k1"), {"a": 1})

    def test_expired_returns_none(self):
        self.cache.set("k1", {"a": 1})
        import time
        time.sleep(2.1)
        self.assertIsNone(self.cache.get("k1"))

    def test_clear(self):
        self.cache.set("k1", 1)
        self.cache.clear()
        self.assertIsNone(self.cache.get("k1"))

    def test_stats(self):
        self.cache.set("k1", 1)
        self.cache.set("k2", 2)
        s = self.cache.stats()
        self.assertEqual(s["total_entries"], 2)
        self.assertEqual(s["valid_entries"], 2)


if __name__ == "__main__":
    unittest.main()
```

**Verificación:**
```bash
python -m pytest trendscope/tests/test_persistent_cache.py -v
```

### Tarea 3.5: Commit
```bash
git add .
git commit -m "feat(cache): cache persistente en SQLite con TTL"
```

---

# BLOQUE 4 — Narrador con Ollama

**Objetivo:** Integrar Ollama local para generar resúmenes ejecutivos, reportes narrativos y respuestas a partir de los datos de TrendScope.

**Entregables:**
1. `trendscope/narrator/` módulo.
2. Función `generate_executive_summary(payload)`.
3. Función `generate_trend_narrative(payload, style)`.
4. Endpoint `POST /narrate`.
5. Tests con mock de Ollama.

### Tarea 4.1: Crear módulo narrator
**Archivo:** `trendscope/narrator/__init__.py`

**Archivo:** `trendscope/narrator/engine.py`

```python
import json
from typing import Literal

from loguru import logger

from trendscope.settings import settings


NARRATIVE_STYLES = {
    "executive": "Eres un analista senior. Resume en 3 párrafos ejecutivos.",
    "creative": "Eres un copywriter. Crea un texto atractivo y viral.",
    "technical": "Eres un ingeniero de datos. Sé técnico y preciso.",
    "alert": "Eres un analista de riesgo. Destaca alertas y riesgos.",
}


def _ollama_client():
    try:
        import ollama
        return ollama
    except ImportError:
        logger.error("ollama no instalado")
        return None


def generate_summary(
    payload: dict,
    style: Literal["executive", "creative", "technical", "alert"] = "executive",
) -> str:
    if not settings.ollama_enabled:
        return "Ollama deshabilitado en configuración."

    client = _ollama_client()
    if client is None:
        return "Error: librería ollama no instalada."

    top = payload.get("top_trends", [])[:10]
    meta = payload.get("meta", {})
    insights = payload.get("insights", {})

    context = json.dumps({
        "topic": meta.get("query", {}).get("topic"),
        "geo": meta.get("query", {}).get("geo"),
        "total_signals": meta.get("total_analyzed"),
        "sentiment_summary": meta.get("sentiment_summary"),
        "top_trends": [
            {"title": t.get("title"), "score": t.get("trend_score"), "source": t.get("source")}
            for t in top
        ],
        "insights": {
            "executive_summary": insights.get("executive_summary"),
            "recommendations": insights.get("recommendations"),
        },
    }, ensure_ascii=False)

    prompt = (
        f"{NARRATIVE_STYLES[style]}\n\n"
        "Analiza los siguientes datos de tendencias y genera un resumen en español.\n"
        "Sé concreto, accionable y basado en los datos.\n\n"
        f"{context}"
    )

    try:
        response = client.chat(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": "Eres un experto en análisis de tendencias."},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": 0.7, "num_predict": 800},
        )
        return response.message.content.strip()
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return f"Error al generar narrativa: {e}"
```

### Tarea 4.2: Endpoint `/narrate`
**Archivo:** `trendscope/server_api.py`

Agregar:
```python
from fastapi import Body
from trendscope.narrator.engine import generate_summary

@app.post("/narrate")
def narrate(
    topic: str | None = QParam(None),
    category: str | None = QParam(None),
    style: str = QParam("executive"),
):
    if not topic and not category:
        raise HTTPException(400, "topic or category required")
    query = TrendQuery(
        mode="category" if category else "free",
        category=category,
        free_topic=topic,
    )
    payload, _ = run_pipeline(query)
    narrative = generate_summary(payload, style=style)
    return {"narrative": narrative, "style": style, "topic": topic or category}
```

### Tarea 4.3: Tests con mock
**Archivo:** `trendscope/tests/test_narrator.py`

```python
import unittest
from unittest.mock import patch, MagicMock

from trendscope.narrator.engine import generate_summary


class NarratorTest(unittest.TestCase):
    def test_generate_summary_disabled(self):
        payload = {"meta": {"query": {}}}
        with patch("trendscope.narrator.engine.settings.ollama_enabled", False):
            result = generate_summary(payload)
        self.assertIn("deshabilitado", result.lower())

    @patch("trendscope.narrator.engine._ollama_client")
    def test_generate_summary_success(self, mock_client_fn):
        mock_client = MagicMock()
        mock_client.chat.return_value = MagicMock(
            message=MagicMock(content="Resumen generado")
        )
        mock_client_fn.return_value = mock_client

        payload = {
            "meta": {"query": {"topic": "crypto", "geo": "CO"}, "total_analyzed": 10},
            "top_trends": [{"title": "Bitcoin", "trend_score": 90, "source": "reddit"}],
        }
        with patch("trendscope.narrator.engine.settings.ollama_enabled", True):
            with patch("trendscope.narrator.engine.settings.ollama_model", "test-model"):
                result = generate_summary(payload)
        self.assertEqual(result, "Resumen generado")
```

### Tarea 4.4: Commit
```bash
git add .
git commit -m "feat(narrator): narrativas con Ollama local y endpoint /narrate"
```

---

# BLOQUE 5 — Watchlist + monitoreo

**Objetivo:** Permitir a los usuarios configurar temas a monitorear automáticamente y guardar el historial.

**Entregables:**
1. Modelo `WatchItem` y tabla SQLite.
2. Scheduler con APScheduler.
3. Endpoints REST para CRUD de watchlist.
4. Historial de análisis guardado.

### Tarea 5.1: Modelo y persistencia de watchlist
**Archivo:** `trendscope/watchlist/__init__.py`

**Archivo:** `trendscope/watchlist/store.py`

```python
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from trendscope.settings import settings


@dataclass
class WatchItem:
    id: Optional[int]
    topic: str
    category: Optional[str]
    geo: str
    interval_minutes: int
    sentiment_engine: str
    active: bool = True


class WatchlistStore:
    def __init__(self, db_path: str | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/watchlist.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT,
                    category TEXT,
                    geo TEXT NOT NULL DEFAULT 'CO',
                    interval_minutes INTEGER NOT NULL DEFAULT 60,
                    sentiment_engine TEXT NOT NULL DEFAULT 'local',
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)

    def add(self, item: WatchItem) -> WatchItem:
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                """INSERT INTO watchlist (topic, category, geo, interval_minutes, sentiment_engine, active)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item.topic, item.category, item.geo, item.interval_minutes,
                 item.sentiment_engine, int(item.active)),
            )
            item.id = cur.lastrowid
        return item

    def list_active(self) -> list[WatchItem]:
        with sqlite3.connect(self.path) as conn:
            rows = conn.execute("SELECT * FROM watchlist WHERE active = 1").fetchall()
        return [self._row_to_item(r) for r in rows]

    def _row_to_item(self, row) -> WatchItem:
        return WatchItem(
            id=row[0], topic=row[1], category=row[2], geo=row[3],
            interval_minutes=row[4], sentiment_engine=row[5], active=bool(row[6]),
        )
```

### Tarea 5.2: Historial de análisis
**Archivo:** `trendscope/watchlist/history.py`

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from trendscope.settings import settings


class AnalysisHistory:
    def __init__(self, db_path: str | None = None):
        self.path = Path(db_path or f"{settings.data_dir}/history.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    geo TEXT NOT NULL,
                    analyzed_at TEXT NOT NULL,
                    total_signals INTEGER,
                    top_score REAL,
                    positive INTEGER,
                    negative INTEGER,
                    neutral INTEGER,
                    payload_json TEXT
                )
            """)

    def save(self, payload: dict) -> None:
        meta = payload.get("meta", {})
        query = meta.get("query", {})
        ss = meta.get("sentiment_summary", {})
        top = payload.get("top_trends", [])
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """INSERT INTO history
                   (topic, geo, analyzed_at, total_signals, top_score, positive, negative, neutral, payload_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    query.get("topic"),
                    query.get("geo", "CO"),
                    datetime.now(timezone.utc).isoformat(),
                    meta.get("total_analyzed"),
                    top[0]["trend_score"] if top else 0,
                    ss.get("positive", 0),
                    ss.get("negative", 0),
                    ss.get("neutral", 0),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )

    def get_history(self, topic: str, days: int = 7) -> list[dict]:
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT * FROM history
                   WHERE topic = ? AND analyzed_at >= datetime('now', '-' || ? || ' days')
                   ORDER BY analyzed_at""",
                (topic, days),
            ).fetchall()
        return [dict(r) for r in rows]
```

### Tarea 5.3: Endpoints REST
**Archivo:** `trendscope/server_api.py`

```python
from trendscope.watchlist.store import WatchlistStore, WatchItem
from trendscope.watchlist.history import AnalysisHistory

watchlist_store = WatchlistStore()
history_store = AnalysisHistory()

@app.post("/watchlist")
def add_watch(item: WatchItem):
    return watchlist_store.add(item)

@app.get("/watchlist")
def list_watch():
    return {"items": [vars(i) for i in watchlist_store.list_active()]}

@app.get("/history")
def get_history(topic: str, days: int = 7):
    return {"topic": topic, "days": days, "entries": history_store.get_history(topic, days)}
```

### Tarea 5.4: Scheduler
**Archivo:** `trendscope/scheduler.py`

```python
from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from trendscope.core.pipeline import run as run_pipeline
from trendscope.core.query import TrendQuery
from trendscope.watchlist.store import WatchlistStore
from trendscope.watchlist.history import AnalysisHistory


def run_watchlist():
    store = WatchlistStore()
    history = AnalysisHistory()
    for item in store.list_active():
        try:
            query = TrendQuery(
                mode="category" if item.category else "free",
                category=item.category,
                free_topic=item.topic,
                geo=item.geo,
                sentiment_engine=item.sentiment_engine,
            )
            payload, _ = run_pipeline(query)
            history.save(payload)
            logger.info(f"Watchlist analysis done: {item.topic}")
        except Exception as e:
            logger.error(f"Watchlist failed for {item.topic}: {e}")


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_watchlist, "interval", minutes=15, id="watchlist")
    scheduler.start()
    return scheduler
```

**Integrar en `server_api.py`:**
```python
from trendscope.scheduler import start_scheduler
start_scheduler()
```

### Tarea 5.5: Commit
```bash
git add .
git commit -m "feat(watchlist): monitoreo recurrente, historial y scheduler"
```

---

# BLOQUE 6 — Dashboard real-time

**Objetivo:** Actualizar el dashboard para soportar WebSockets, historial y comparación temporal.

**Entregables:**
1. Endpoint WebSocket `/ws`.
2. Función en dashboard para recibir actualizaciones.
3. Gráfico de evolución temporal (usando Chart.js desde CDN).

### Tarea 6.1: Endpoint WebSocket
**Archivo:** `trendscope/server_api.py`

```python
from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            msg = await websocket.receive_text()
            query = TrendQuery(mode="free", free_topic=msg)
            payload, _ = run_pipeline(query)
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        pass
```

### Tarea 6.2: Panel de historial en dashboard
En `dashboard.html` agregar:
- Sección "Historial" con selector de días.
- Gráfico de línea con Chart.js mostrando score, volumen, sentimiento.

### Tarea 6.3: Commit
```bash
git add .
git commit -m "feat(dashboard): WebSockets y visualización de historial"
```

---

# BLOQUE 7 — Docker + CI/CD

**Objetivo:** Empaquetar TrendScope en Docker y correr tests automáticamente en GitHub Actions.

### Tarea 7.1: Dockerfile
**Archivo:** `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY trendscope/ ./trendscope/

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["trendscope-api"]
```

### Tarea 7.2: docker-compose.yml
**Archivo:** `docker-compose.yml`

```yaml
version: "3.8"
services:
  trendscope:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
```

### Tarea 7.3: GitHub Actions
**Archivo:** `.github/workflows/tests.yml`

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv sync
      - run: uv run pytest trendscope/tests/ -v
```

### Tarea 7.4: Commit final
```bash
git add .
git commit -m "ci: Docker, docker-compose y GitHub Actions"
```

---

# Notas finales

- Cada bloque debe quedar probado antes de continuar.
- Si algo falla, no avanzar. Retroceder y arreglar.
- Hacer push a GitHub al final de cada bloque.
- Actualizar README.md al finalizar el bloque 7.

**¿Listo para empezar con el BLOQUE 0?**
