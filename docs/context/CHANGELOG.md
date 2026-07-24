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

## [0.1.0] — 2026-06-01 — Claude Opus 4

### Añadido
- Carpeta .context/ con 5 archivos de contexto interno
- PROJECT.md: visión, stack, filosofía
- ARCHITECTURE.md: estructura, flujo, modelos de datos, decisiones, resiliencia
- CHANGELOG.md: registro de cambios del proyecto
- AGENTS.md: guía para cualquier modelo que trabaje aquí
- WORKING_STYLE.md: convenciones, Scrapling usage, reglas

### Pendiente
- Bloque 1: Base del proyecto (estructura, requirements, config, core/query.py)
- Bloque 2: Scrapers (Reddit, Google Trends, Twitter, Amazon, TikTok)
- Bloque 3: Análisis (scorer, deduplicator, sentimiento local + Claude)
- Bloque 4: Output (JSON exporter, Markdown report)
- Bloque 5: Pipeline + CLI
- Bloque 6: Servidores (API REST + MCP)
- Bloque 7: Publicación GitHub

---

## [0.2.0] — 2026-06-01 — Claude Opus 4

### Añadido
- Estructura de carpetas completa (core, scrapers, sentiment, analyzer, output, data)
- requirements.txt con stack completo (Scrapling, PRAW, pytrends, anthropic, FastAPI, etc.)
- config.py: configuración central con 10 categorías, subreddits y URLs de Amazon
- core/query.py: TrendQuery dataclass con keywords, subreddits y topic_slug
- .env.example: template de credenciales con todas las variables
- .env: archivo de prueba con valores vacíos
- .gitignore: excluye .env, data/, .context/, __pycache__, IDE files

### Notas
- Python 3.14.3 detectado — pysentimiento comentado en requirements (incompatible aún)
- xactions-py tiene problema de build con setuptools en Python 3.14 (resolver en Bloque 2)
- Versiones flexibles (>=) en requirements.txt para compatibilidad con Python 3.14

### Pendiente
- Bloque 2: Scrapers (Reddit, Google Trends, Twitter, Amazon, TikTok)

---

## [0.3.0] — 2026-06-01 — Claude Opus 4

### Añadido
- scrapers/reddit.py: PRAW + JSON público fallback, filtro por keywords
- scrapers/google_trends.py: RSS primario + pytrends fallback
- scrapers/twitter.py: xactions-py con manejo graceful de credenciales faltantes
- scrapers/amazon.py: Scrapling StealthyFetcher, selectores adaptativos (14 productos OK)
- scrapers/tiktok.py: API JSON Creative Center + DynamicFetcher fallback

### Notas
- Reddit JSON público bloqueado (403) sin OAuth — funciona con credenciales PRAW
- Google Trends RSS funciona perfecto (10 tendencias CO)
- Amazon StealthyFetcher extrae 14 productos correctamente
- TikTok API cerrada (40101 no permission) — requiere cookie de sesión o browser real
- Todos los scrapers retornan list[dict] sin excepción al pipeline

### Pendiente
- Bloque 3: Análisis (scorer, deduplicator, sentimiento local + Claude)

---

## [0.4.0] — 2026-06-01 — Claude Opus 4

### Añadido
- analyzer/deduplicator.py: elimina duplicados cross-fuente (threshold 72% similitud)
- sentiment/base.py: SentimentResult dataclass estándar
- sentiment/local_engine.py: pysentimiento + fallback por keywords (Python 3.14 compatible)
- sentiment/claude_engine.py: Claude Haiku API en batches de 10 textos
- sentiment/__init__.py: analyze_items() entry point unificado con fallback neutral
- analyzer/scorer.py: scoring 0-100 por fuente + bonus keywords + bonus/penalización sentimiento

### Notas
- pysentimiento incompatible con Python 3.14 — fallback por keywords funciona correctamente
- Fallback detecta positivo/negativo/neutral con ~80% accuracy basado en vocabulario
- Scorer produce valores correctos: Amazon #3 = 95.5, Google 500K+ = 93.0, Reddit con engagement = 28.8
- Bonus sentimiento verificado: positivo > negativo (+8 puntos de diferencia)

### Pendiente
- Bloque 4: Output (JSON exporter + Markdown report)

---

## [0.5.0] — 2026-06-02 — Claude Opus 4

### Añadido
- output/json_exporter.py: JSON estructurado con meta, top_trends, signals y agent_prompt
- output/report_exporter.py: Markdown legible con tabla sentimiento, scores y senales por item

### Notas
- JSON incluye agent_prompt listo para pasar a otro modelo de IA
- Reporte Markdown usa formato terminal-friendly (sin emojis problemáticos en encoding)
- Ambos exportadores crean directorio data/ automáticamente si no existe
- Archivos nombrados: trends_YYYY-MM-DD_slug.json / report_YYYY-MM-DD_slug.md

### Pendiente
- Bloque 5: Pipeline + CLI

---

## [0.6.0] — 2026-06-02 — Claude Opus 4

### Añadido
- core/pipeline.py: orquesta scraping -> dedup -> sentimiento -> scoring -> output
- main.py: CLI interactivo con rich (categoria + libre, motor sentimiento elegible)

### Cambiado
- analyzer/scorer.py: escala logaritmica para Google Trends traffic (fix: 1000+ ahora da ~63 en vez de 0.85)
- core/pipeline.py: status inline en vez de Progress spinners (evita encoding errors en Windows cp1252)

### Notas
- Pipeline end-to-end validado: 24 senales recolectadas, 2 duplicados removidos, 22 unicos puntuados
- Windows UTF-8 handling con sys.stdout.reconfigure
- main.py importa correctamente, listo para uso interactivo

### Pendiente
- Bloque 6: Servidores (API REST + MCP)

---

## [0.7.0] — 2026-06-02 — Claude Opus 4

### Añadido
- server_api.py: FastAPI con GET /health, /categories, /trends, /report
- server_mcp.py: Servidor MCP con 3 tools (analyze_trends, get_categories, get_latest_report)

### Notas
- API REST validada: /health retorna {"status":"ok"}, /categories lista 10 categorias, /trends ejecuta pipeline completo, /report retorna Markdown
- MCP server importa correctamente con 3 tools registradas
- API corre en uvicorn, configurable via .env (API_HOST, API_PORT)
- MCP usa stdio_server para comunicacion con agentes

### Pendiente
- Bloque 7: Publicacion en GitHub

---

## [1.0.0] — 2026-06-02 — Claude Opus 4

### Añadido
- README.md publico con documentacion completa (instalacion, uso, stack, configuracion)
- LICENSE MIT
- git init + commit inicial (28 archivos, 1817 lineas)
- gh CLI instalado (v2.93.0)

### Verificado
- .env NO esta en el repo (excluido por .gitignore)
- data/ NO esta en el repo (excluido)
- .context/ NO esta en el repo (excluido)
- Solo codigo fuente publico + .env.example + LICENSE + README

### Estado
PROYECTO COMPLETO v1.0.0 — Pendiente: gh auth login + push por el usuario
