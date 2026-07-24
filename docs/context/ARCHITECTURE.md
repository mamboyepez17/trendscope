# TrendScope — Architecture

## Estructura de carpetas

```
trendscope/
├── .context/                  # NO va al repo — solo modelos
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
├── data/                      # NO va al repo
│   ├── trends_FECHA_TEMA.json
│   └── report_FECHA_TEMA.md
│
├── main.py                    # CLI interactivo (rich)
├── server_api.py              # API REST (FastAPI)
├── server_mcp.py              # Servidor MCP
├── config.py                  # Configuración central
├── requirements.txt
├── .env                       # NO va al repo
├── .env.example               # SI va (template)
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

## Resiliencia y Rate Limiting

Cada scraper implementa su propia estrategia de resiliencia:

| Fuente | Rate Limit | Retry Strategy |
|---|---|---|
| Reddit (PRAW) | 60 req/min | Backoff exponencial, fallback a JSON público |
| Reddit (JSON) | ~30 req/min estimado | Sleep 2s entre requests |
| Google Trends RSS | Sin límite conocido | Retry x3 con 1s delay |
| pytrends | 429 frecuente | Backoff exponencial 5s-30s, max 3 intentos |
| Twitter (xactions-py) | Depende de auth | Retry x2, timeout 15s |
| Amazon (Scrapling) | Agresivo anti-bot | StealthyFetcher con random delay 2-5s |
| TikTok (Scrapling) | Anti-bot moderado | DynamicFetcher con network_idle wait |

### Patrón de retry estándar

```python
import time
from loguru import logger

def retry_with_backoff(func, max_retries: int = 3, base_delay: float = 1.0):
    """Retry genérico con backoff exponencial."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Retry {attempt+1}/{max_retries} en {delay}s: {e}")
            time.sleep(delay)
```

## Concurrencia

El pipeline ejecuta scrapers de forma **secuencial por defecto** para evitar
rate limits cruzados. Opcionalmente se puede habilitar `concurrent=True` en
la configuración para ejecutar scrapers en paralelo con `asyncio.gather()`
(útil en servidor API donde la latencia importa).
