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
