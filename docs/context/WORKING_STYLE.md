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
- pysentimiento usa lang="es" para español y lang="en" para inglés
- Detección automática de idioma por texto (sin config manual)
- Google Trends RSS usa geo=CO
- Keywords orientadas a contexto colombiano

## Sentimiento
- Default: local (pysentimiento bilingüe ES/EN, gratis)
- Premium: claude (Haiku, bajo costo, multilingüe nativo)
- Detección automática: si el texto tiene palabras en español → modelo ES, si no → modelo EN
- Configurable en .env Y sobreescribible en CLI cada vez

## Archivos de salida
- JSON: `data/trends_YYYY-MM-DD_slug.json`
- Markdown: `data/report_YYYY-MM-DD_slug.md`
- slug = tema[:30].replace(" ", "_")

## Patrón de Error Handling

Todos los scrapers siguen este patrón de manejo de errores:

```python
from loguru import logger
import time

def run(query: TrendQuery) -> list[dict]:
    results = []
    try:
        # Intento principal
        results = _fetch_primary(query)
    except RateLimitError as e:
        logger.warning(f"Rate limit alcanzado: {e}")
        time.sleep(5)
        # No retry — retornar lo que se tenga
    except ConnectionError as e:
        logger.error(f"Sin conexión a la fuente: {e}")
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
    
    # SIEMPRE retornar lista, nunca None, nunca raise
    return results
```

### Principios clave:
- Un scraper NUNCA rompe el pipeline
- Errores se loguean con `loguru`, nunca se silencian
- Si hay fallback disponible (ej: Reddit JSON público), se intenta
- El pipeline recibe [] y simplemente continúa con las otras fuentes

## Logging con loguru

```python
from loguru import logger

# Niveles usados en TrendScope:
logger.debug("Detalle técnico solo para debugging")
logger.info("Operación completada exitosamente")
logger.warning("Algo no ideal pero el sistema sigue")
logger.error("Fallo en una operación, pero el pipeline continúa")
logger.critical("Fallo que impide continuar")
```

## Lo que NUNCA se hace
- npm, Node.js, JavaScript de cualquier tipo
- print() en producción (usar loguru)
- Hardcodear credenciales
- Avanzar de bloque sin aprobación del usuario
- Commitear .env, data/, .context/
- Dejar que un scraper rompa el pipeline completo
- Incluir información privada del usuario en ningún archivo
- Retornar None desde un scraper (siempre list[dict])
- Ignorar errores silenciosamente (siempre logguear)
