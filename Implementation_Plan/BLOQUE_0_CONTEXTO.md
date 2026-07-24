# 🧠 TRENDSCOPE — BLOQUE 0 DE 7
## Contexto interno del proyecto (.context/)
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 0 de 7. Tu única misión aquí es crear los archivos
de contexto interno del proyecto en la carpeta `.context/`.

Estos archivos son el cerebro privado de TrendScope. Cualquier modelo
que trabaje en este proyecto los lee PRIMERO antes de tocar código.

**Reglas:**
- Crear carpeta `trendscope/.context/`
- Crear los 5 archivos exactamente como están definidos aquí
- Estos archivos NO van al repo público (van en `.gitignore`)
- Verificar que todos existen y tienen contenido antes de reportar
- NO pasar al Bloque 1 sin confirmación del usuario

---

## PASO 0.1 — Crear carpeta base

```bash
mkdir -p trendscope/.context
cd trendscope
```

---

## PASO 0.2 — `.context/PROJECT.md`

```markdown
# TrendScope — Project Context

## Qué es
TrendScope es infraestructura de inteligencia de tendencias universal.
Permite analizar tendencias sobre CUALQUIER tema desde múltiples fuentes
gratuitas, con análisis de sentimiento incluido.

No está limitada a un nicho — sirve para negocios, salud, política,
tecnología, deportes, inmobiliaria, crypto, o cualquier tema libre.

## Autor
mamboyepez17

## Tres modos de uso
1. `python main.py`        — CLI interactivo para humanos
2. `python server_api.py`  — API REST para agentes HTTP
3. `python server_mcp.py`  — Servidor MCP para agentes compatibles

## Stack principal
- Python 3.10+ — lenguaje único, sin JavaScript ni Node
- PRAW 7.8.1 — Reddit (+ JSON público fallback)
- xactions-py (mamboyepez17/xactions-py) — Twitter/X
- Google Trends RSS — primario, sin JS ni captcha
- pytrends — fallback Google Trends
- Scrapling — scraping adaptativo (reemplaza Playwright + requests + BS4)
- pysentimiento — sentimiento español latinoamericano (local, gratis)
- Claude API Haiku — sentimiento premium
- FastAPI + uvicorn — API REST
- mcp[cli] — servidor MCP
- rich — CLI bonito en terminal
- loguru — logs con rotación

## Por qué Scrapling en lugar de Playwright
Scrapling es adaptativo — aprende de cambios en el sitio y reubica
elementos automáticamente. Bypassa anti-bot (Cloudflare, etc.) out of
the box. Es hasta 240x más rápido que BeautifulSoup. Tiene servidor MCP
integrado. Reemplaza Playwright + requests + BeautifulSoup en un solo
paquete.

## Filosofía de diseño
- Portable: `python main.py` igual en PC o VPS
- Resiliente: si una fuente falla, las demás siguen
- Accesible: sentimiento gratis (local) o premium (API) según bolsillo
- Modular: cada scraper es independiente, fácil añadir fuentes
- Privado: credenciales en .env, nunca en código

## Repositorios relacionados
- xactions-py: github.com/mamboyepez17/xactions-py
- TrendScope:  github.com/mamboyepez17/trendscope

## Estado actual
Ver CHANGELOG.md
```

---

## PASO 0.3 — `.context/ARCHITECTURE.md`

```markdown
# TrendScope — Architecture

## Estructura de carpetas

```
trendscope/
├── .context/                  # ❌ NO va al repo — solo modelos
│   ├── PROJECT.md
│   ├── ARCHITECTURE.md
│   ├── CHANGELOG.md
│   ├── AGENTS.md
│   └── WORKING_STYLE.md
│
├── core/
│   ├── __init__.py
│   ├── query.py               # TrendQuery: modelo de consulta
│   └── pipeline.py            # Orquesta todo el flujo
│
├── scrapers/                  # Una fuente por archivo
│   ├── __init__.py
│   ├── reddit.py              # PRAW + JSON público fallback
│   ├── google_trends.py       # RSS primario + pytrends fallback
│   ├── twitter.py             # xactions-py
│   ├── amazon.py              # Scrapling StealthyFetcher
│   └── tiktok.py              # Scrapling DynamicFetcher
│
├── sentiment/
│   ├── __init__.py            # analyze_items() entry point
│   ├── base.py                # SentimentResult dataclass
│   ├── local_engine.py        # pysentimiento (gratis)
│   └── claude_engine.py       # Claude Haiku API (premium)
│
├── analyzer/
│   ├── __init__.py
│   ├── scorer.py              # Puntuación 0-100 + bonus sentimiento
│   └── deduplicator.py        # Elimina duplicados cross-fuente
│
├── output/
│   ├── __init__.py
│   ├── json_exporter.py       # JSON para agentes
│   └── report_exporter.py     # Markdown para humanos
│
├── data/                      # ❌ NO va al repo
│   ├── trends_FECHA_TEMA.json
│   └── report_FECHA_TEMA.md
│
├── main.py                    # CLI interactivo (rich)
├── server_api.py              # API REST (FastAPI)
├── server_mcp.py              # Servidor MCP
├── config.py                  # Configuración central
├── requirements.txt
├── .env                       # ❌ NO va al repo
├── .env.example               # ✅ Sí va (template)
└── .gitignore
```

## Flujo de datos

```
Usuario / Agente
      │
      ▼
TrendQuery
  mode: "category" | "free"
  topic / category
  geo, top_n, sentiment_engine
      │
      ▼
Pipeline
  ├── reddit.py          → items[]
  ├── google_trends.py   → items[]
  ├── twitter.py         → items[]
  ├── amazon.py          → items[]
  └── tiktok.py          → items[]
      │
      ▼
  deduplicator.py        → items únicos
      │
      ▼
  sentiment/             → label + score + emotions
      │
      ▼
  scorer.py              → trend_score 0-100
      │
      ▼
  ┌───┴───┐
  ▼       ▼
JSON    Markdown
```

## Modelo de datos — item enriquecido

```json
{
  "source": "reddit|google_trends_rss|twitter|amazon_bestsellers|tiktok_trending",
  "title": "texto del item",
  "url": "enlace",
  "trend_score": 87.5,
  "sentiment_label": "positive|negative|neutral",
  "sentiment_score": 0.92,
  "emotions": {"joy": 0.8, "anger": 0.05},
  "signals": {
    "reddit_score": 1240,
    "upvote_ratio": 0.97,
    "comments": 340,
    "likes": null,
    "retweets": null,
    "google_traffic": "500K+",
    "amazon_rank": "3",
    "price": "$29.99"
  }
}
```

## Decisiones de arquitectura

| Decisión | Razón |
|---|---|
| Scrapling > Playwright + requests | Adaptativo, anti-bot, 240x más rápido, un solo paquete |
| RSS antes que pytrends | Sin JS, sin captcha, siempre estable |
| JSON público Reddit | Funciona sin API key, más resiliente |
| pysentimiento lang=es | Entrenado en español latinoamericano |
| Claude Haiku para sentiment | Más barato que Sonnet/Opus |
| FastAPI para API REST | Liviano, async, docs en /docs automáticas |
| MCP server | Protocolo nativo de agentes Claude |
| Bloques de desarrollo | Validar antes de avanzar, evita errores acumulados |
```

---

## PASO 0.4 — `.context/CHANGELOG.md`

```markdown
# TrendScope — Changelog

## Formato de entradas

Cuando un modelo complete un bloque, agrega una entrada así:

---
## [VERSION] — FECHA — MODELO_USADO
### Añadido
- descripción
### Cambiado
- descripción
### Corregido
- descripción
### Pendiente
- descripción
---

## [0.1.0] — 2026-05-31 — Planificación

### Añadido
- Definición de arquitectura completa
- Stack tecnológico confirmado (Scrapling reemplaza Playwright)
- División en 7 bloques de desarrollo con validación por bloque
- Archivos de contexto interno (.context/)

### Pendiente
- Bloque 1: Base (estructura, requirements, config, core/query.py)
- Bloque 2: Scrapers (Reddit, Google Trends, Twitter, Amazon, TikTok)
- Bloque 3: Análisis (scorer, deduplicator, sentimiento local + Claude)
- Bloque 4: Output (JSON exporter, Markdown report)
- Bloque 5: Pipeline + CLI
- Bloque 6: Servidores (API REST + MCP)
- Bloque 7: Publicación GitHub
```

---

## PASO 0.5 — `.context/AGENTS.md`

```markdown
# TrendScope — Guía para Modelos de IA

## Para cualquier modelo que trabaje aquí
Opus 4.7, MiMo, DeepSeek, Haiku, o cualquier otro.
Leer este archivo ANTES de tocar cualquier código.

## Checklist obligatorio al abrir el proyecto
1. Leer PROJECT.md — qué es y para qué sirve
2. Leer ARCHITECTURE.md — estructura y flujo de datos
3. Leer CHANGELOG.md — qué está hecho y qué falta
4. Leer WORKING_STYLE.md — reglas y convenciones
5. Identificar en qué bloque trabajar
6. Nunca asumir — si no está claro, revisar los .context/

## Sistema de bloques — OBLIGATORIO respetar

| Bloque | Contenido | Criterio de aprobación |
|---|---|---|
| 0 | .context/ | 5 archivos existen con contenido |
| 1 | Base: estructura, config, query | Imports limpios, .env carga |
| 2 | 5 scrapers | Cada uno devuelve list[dict] |
| 3 | Scorer + sentimiento | Items entran, salen puntuados |
| 4 | JSON + Markdown output | Archivos generados en data/ |
| 5 | Pipeline + CLI | python main.py corre end-to-end |
| 6 | API REST + MCP | Endpoints y tools responden |
| 7 | GitHub | Repo limpio, sin archivos privados |

**NUNCA avanzar al siguiente bloque sin aprobación del usuario.**

## Reglas de código
- Python 3.10+ únicamente — sin JavaScript, Node, npm
- `pip install --break-system-packages` en Linux
- Credenciales SIEMPRE en .env, nunca en código
- Scrapling para todo scraping HTTP y browser
- loguru para logs, nunca print() en producción
- Type hints en todas las funciones
- Cada scraper: try/except propio, retorna [] si falla

## Reglas de archivos
- `.env` → nunca al repo
- `data/` → nunca al repo
- `.context/` → nunca al repo
- Solo `.env.example` va al repo como template

## Al completar cada bloque
1. Verificar criterio de aprobación del bloque
2. Actualizar CHANGELOG.md con lo que se hizo
3. Reportar al usuario con el mensaje estándar
4. Esperar APROBADO antes de continuar

## Mensaje estándar de completitud

```
✅ BLOQUE X COMPLETADO

[lista de lo que se creó/hizo]

¿Aprobado para continuar al Bloque X+1?
```
```

---

## PASO 0.6 — `.context/WORKING_STYLE.md`

```markdown
# TrendScope — Working Style

## Convenciones de nombrado
- Archivos: snake_case (google_trends.py, json_exporter.py)
- Clases: PascalCase (TrendQuery, SentimentResult)
- Funciones: snake_case (run_pipeline, analyze_items)
- Constantes: UPPER_SNAKE (API_HOST, DATA_DIR)
- Variables: snake_case (all_items, trend_score)

## Estructura estándar de un scraper

```python
# scrapers/nombre.py
from loguru import logger
from core.query import TrendQuery

def run(query: TrendQuery) -> list[dict]:
    """
    Entry point estándar de todo scraper.
    Siempre retorna list[dict], nunca lanza excepción al pipeline.
    """
    results = []
    try:
        # lógica aquí
        pass
    except Exception as e:
        logger.error(f"NombreScraper: {e}")
    logger.info(f"NombreScraper: {len(results)} items")
    return results
```

## Estructura estándar de un item

```python
{
    "source": "nombre_scraper",   # obligatorio
    "title": "texto principal",   # o "keyword" o "text"
    "url": "enlace",              # opcional
    # campos adicionales según la fuente
}
```

## Scrapling — cómo usarlo en este proyecto

```python
from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher

# Para sitios normales (rápido)
page = Fetcher.get("https://ejemplo.com")

# Para sitios con anti-bot (Amazon, etc.)
page = StealthyFetcher.fetch("https://ejemplo.com", headless=True)

# Para sitios que requieren JS pesado (TikTok)
page = DynamicFetcher.fetch("https://ejemplo.com", network_idle=True)

# Selectores CSS
items = page.css(".clase-producto")
for item in items:
    title = item.css_first("h2").text
```

## Dependencias — decisiones tomadas

| Librería | Versión | Reemplaza a |
|---|---|---|
| scrapling | latest | playwright + requests + beautifulsoup4 |
| praw | 7.8.1 | nada (único para Reddit API) |
| pytrends | 4.9.2 | nada (fallback Google Trends) |
| pysentimiento | 0.7.4 | transformers genérico |
| fastapi | 0.111.0 | flask |
| rich | 13.7.1 | click solo |
| loguru | 0.7.2 | logging stdlib |

## Configuración regional
- GEO_TARGET = "CO" (Colombia) por defecto
- pysentimiento usa lang="es"
- Google Trends RSS usa geo=CO
- Keywords orientadas a contexto colombiano

## Sentimiento
- Default: local (pysentimiento, gratis)
- Premium: claude (Haiku, bajo costo)
- Configurable en .env Y sobreescribible en CLI cada vez

## Archivos de salida
- JSON: `data/trends_YYYY-MM-DD_slug.json`
- Markdown: `data/report_YYYY-MM-DD_slug.md`
- slug = tema[:30].replace(" ", "_")

## Lo que NUNCA se hace
- npm, Node.js, JavaScript de cualquier tipo
- print() en producción (usar loguru)
- Hardcodear credenciales
- Avanzar de bloque sin aprobación del usuario
- Commitear .env, data/, .context/
- Dejar que un scraper rompa el pipeline completo
- Incluir información privada del usuario en ningún archivo
```

---

## PASO 0.7 — Verificación

```bash
ls -la trendscope/.context/
wc -l trendscope/.context/*.md
```

Resultado esperado: 5 archivos, ninguno vacío.

---

## PASO 0.8 — Actualizar CHANGELOG.md

```markdown
## [0.1.0] — HOY — TU_MODELO

### Añadido
- Carpeta .context/ con 5 archivos de contexto interno
- PROJECT.md: visión, stack, filosofía
- ARCHITECTURE.md: estructura, flujo, modelos de datos, decisiones
- CHANGELOG.md: registro de cambios del proyecto
- AGENTS.md: guía para cualquier modelo que trabaje aquí
- WORKING_STYLE.md: convenciones, Scrapling usage, reglas

### Pendiente
- Bloque 1: Base del proyecto
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 0

- [ ] Carpeta `trendscope/.context/` existe
- [ ] `PROJECT.md` — sin referencias a proyectos privados
- [ ] `ARCHITECTURE.md` — sin referencias a proyectos privados
- [ ] `CHANGELOG.md` — existe con entrada inicial
- [ ] `AGENTS.md` — sin referencias a proyectos privados
- [ ] `WORKING_STYLE.md` — incluye regla de no info privada
- [ ] CHANGELOG actualizado con entrada del Bloque 0
- [ ] Reportar al usuario con mensaje estándar

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 0 COMPLETADO

Archivos creados en trendscope/.context/:
- PROJECT.md       (X líneas)
- ARCHITECTURE.md  (X líneas)
- CHANGELOG.md     (X líneas)
- AGENTS.md        (X líneas)
- WORKING_STYLE.md (X líneas)

¿Aprobado para continuar al Bloque 1 — Base del proyecto?
```

---

*TrendScope — Bloque 0 de 7 | Siguiente: BLOQUE_1_BASE.md*
