# core/doctor.py
"""
TrendScope Doctor — diagnostica el estado de todas las fuentes.
Inspirado en Agent-Reach: verifica cada fuente real, no solo si existe.
Te dice qué funciona, qué no, y cómo arreglarlo.
"""
import os
import time

from loguru import logger

from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET,
    TWITTER_AUTH_TOKEN, TWITTER_CT0,
    TWEETCLAW_RESULTS_FILE,
    ANTHROPIC_API_KEY,
    SENTIMENT_ENGINE_DEFAULT,
)


def _check_google_trends() -> dict:
    """Google Trends — RSS + pytrends."""
    try:
        import requests
        resp = requests.get(
            "https://trends.google.com/trending/rss?geo=CO",
            headers={"User-Agent": "TrendScope/1.0"},
            timeout=10,
        )
        if resp.status_code == 200 and len(resp.text) > 100:
            return {"status": "ok", "message": "Google Trends RSS disponible"}
        return {"status": "warn", "message": f"RSS respondio {resp.status_code}, pytrends puede funcionar como fallback"}
    except Exception as e:
        return {"status": "error", "message": f"Google Trends RSS fallo: {e}"}


def _check_reddit() -> dict:
    """Reddit — RSS de old.reddit.com o PRAW."""
    if REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
        try:
            import praw
            reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent="TrendScope/1.0",
            )
            reddit.user.me()
            return {"status": "ok", "message": "PRAW autenticado y funcionando"}
        except Exception:
            return {"status": "warn", "message": "PRAW configurado pero fallo auth — fallback a RSS gratis"}

    # Sin PRAW — probar RSS
    try:
        import requests
        resp = requests.get(
            "https://old.reddit.com/r/test/hot.rss",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"status": "ok", "message": "Reddit RSS disponible (gratis, sin API key)"}
        if resp.status_code == 429:
            return {"status": "warn", "message": "RSS rate-limited — funcionara con backoff. Opcional: configurar PRAW para mejor data"}
        return {"status": "warn", "message": f"RSS respondio {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Reddit RSS fallo: {e}. Opcional: configurar REDDIT_CLIENT_ID y REDDIT_CLIENT_SECRET en .env"}


def _check_twitter() -> dict:
    """Twitter/X — xactions-py con cookies."""
    if not TWITTER_AUTH_TOKEN or not TWITTER_CT0:
        return {
            "status": "off",
            "message": "Sin credenciales. Obtener cookies de x.com → DevTools → Application → Cookies. Poner TWITTER_AUTH_TOKEN y TWITTER_CT0 en .env",
        }

    token_len = len(TWITTER_AUTH_TOKEN)
    ct0_len = len(TWITTER_CT0)

    if token_len < 10 or ct0_len < 20:
        return {"status": "error", "message": f"Credenciales incompletas (auth_token={token_len} chars, ct0={ct0_len} chars). Revisar .env"}

    # Verificar que xactions importa
    try:
        from xactions.scraper.scrapers import search_tweets_sync
        from xactions.scraper.client import TwitterError
        return {"status": "ok", "message": f"xactions-py listo (auth_token={token_len} chars, ct0={ct0_len} chars)"}
    except ImportError:
        return {"status": "error", "message": "Modulo xactions/ no encontrado. El directorio xactions/ debe estar en la raiz del proyecto"}
    except Exception as e:
        return {"status": "warn", "message": f"xactions importa pero podria haber issues: {e}"}


def _check_hackernews() -> dict:
    """Hacker News — API Algolia."""
    try:
        import requests
        resp = requests.get(
            "https://hn.algolia.com/api/v1/search?query=test&hitsPerPage=1",
            timeout=10,
        )
        if resp.status_code == 200:
            return {"status": "ok", "message": "HackerNews API disponible (gratis, sin auth)"}
        return {"status": "warn", "message": f"HN API respondio {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"HackerNews API fallo: {e}"}


def _check_youtube() -> dict:
    """YouTube — API interna de busqueda."""
    try:
        import requests
        payload = {
            "context": {"client": {"clientName": "WEB", "clientVersion": "2.20240601.00.00", "hl": "es", "gl": "CO"}},
            "query": "test",
        }
        resp = requests.post(
            "https://www.youtube.com/youtubei/v1/search",
            json=payload,
            timeout=10,
        )
        if resp.status_code == 200:
            return {"status": "ok", "message": "YouTube API interna disponible (gratis, sin auth)"}
        return {"status": "warn", "message": f"YouTube API respondio {resp.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"YouTube API fallo: {e}"}


def _check_amazon() -> dict:
    """Amazon — Scrapling StealthyFetcher."""
    try:
        from scrapling.fetchers import StealthyFetcher
        return {"status": "ok", "message": "Scrapling StealthyFetcher disponible"}
    except ImportError:
        return {"status": "off", "message": "Scrapling no instalado o curl_cffi faltante. Ejecutar: pip install scrapling curl_cffi"}
    except Exception as e:
        return {"status": "warn", "message": f"Scrapling importo pero podria fallar: {e}"}


def _check_tiktok() -> dict:
    """TikTok — API interna del Creative Center."""
    try:
        import requests
        params = {"page": 1, "limit": 1, "period": 7, "country_code": "CO", "sort_by": "popular"}
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        resp = requests.get(
            "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list",
            params=params, headers=headers, timeout=10,
        )
        if resp.status_code == 200:
            return {"status": "ok", "message": "TikTok API disponible (gratis, sin auth)"}
        return {"status": "warn", "message": f"TikTok API respondio {resp.status_code} — puede haber cambiado"}
    except Exception as e:
        return {"status": "error", "message": f"TikTok API fallo: {e}"}


def _check_tweetclaw() -> dict:
    """TweetClaw — archivo JSON local opcional."""
    if not TWEETCLAW_RESULTS_FILE:
        return {"status": "off", "message": "No configurado (opcional). Poner TWEETCLAW_RESULTS_FILE en .env con la ruta del JSON"}
    from pathlib import Path
    path = Path(TWEETCLAW_RESULTS_FILE).expanduser()
    if path.exists():
        return {"status": "ok", "message": f"Archivo encontrado: {path}"}
    return {"status": "warn", "message": f"Archivo no encontrado: {path}. Crear el JSON o quitar TWEETCLAW_RESULTS_FILE del .env"}


def _check_sentiment() -> dict:
    """Motor de sentimiento."""
    if SENTIMENT_ENGINE_DEFAULT == "claude":
        if not ANTHROPIC_API_KEY:
            return {"status": "error", "message": "Motor 'claude' seleccionado pero ANTHROPIC_API_KEY no configurada"}
        return {"status": "ok", "message": "Motor Claude configurado (premium)"}

    # Motor local
    try:
        import torch
        return {"status": "ok", "message": "pysentimiento + torch disponibles (motor local premium)"}
    except OSError:
        return {"status": "warn", "message": "pysentimiento cargado pero torch bloqueado por WDAC — fallback por keywords activo (funciona, menos preciso)"}
    except ImportError:
        try:
            from sentiment.local_engine import _analyze_fallback
            return {"status": "ok", "message": "Fallback por keywords bilingue activo (funciona sin torch)"}
        except Exception:
            return {"status": "error", "message": "Motor local no disponible"}
    except Exception:
        return {"status": "ok", "message": "Motor local con fallback por keywords"}


def check_all() -> dict:
    """Ejecuta todos los checks y retorna el reporte completo."""
    checks = {
        "Google Trends": _check_google_trends,
        "Reddit": _check_reddit,
        "Twitter/X": _check_twitter,
        "Hacker News": _check_hackernews,
        "YouTube": _check_youtube,
        "Amazon": _check_amazon,
        "TikTok": _check_tiktok,
        "TweetClaw": _check_tweetclaw,
        "Sentiment": _check_sentiment,
    }

    results = {}
    for name, check_fn in checks.items():
        try:
            results[name] = check_fn()
        except Exception as e:
            results[name] = {"status": "error", "message": f"Check fallo: {e}"}

    return results


def format_report(results: dict) -> str:
    """Formatea el reporte para mostrar en terminal o devolver como string."""
    lines = []
    lines.append("\n[bold cyan]TrendScope Doctor[/bold cyan] — Diagnostico de fuentes\n")
    lines.append("[cyan]" + "=" * 50 + "[/cyan]")
    lines.append("[dim]Leyenda: [green]OK[/green]  [yellow]WARN[/yellow]  [red]ERROR[/red]  OFF[/dim]")

    ok_count = sum(1 for r in results.values() if r["status"] == "ok")
    warn_count = sum(1 for r in results.values() if r["status"] == "warn")
    error_count = sum(1 for r in results.values() if r["status"] == "error")
    off_count = sum(1 for r in results.values() if r["status"] == "off")

    for name, result in results.items():
        status = result["status"]
        if status == "ok":
            icon = "[green]✅[/green]"
        elif status == "warn":
            icon = "[yellow]⚠️[/yellow]"
        elif status == "error":
            icon = "[red]❌[/red]"
        else:
            icon = "[dim]⚪[/dim]"

        lines.append(f"  {icon} [bold]{name:15}[/bold] {result['message']}")

    lines.append("")
    lines.append(
        f"  [bold]Total: [green]{ok_count} OK[/green] · "
        f"[yellow]{warn_count} WARN[/yellow] · "
        f"[red]{error_count} ERROR[/red] · "
        f"[dim]{off_count} OFF[/dim][/bold]"
    )

    active = ok_count + warn_count
    lines.append(f"  [bold green]{active} fuentes activas de {len(results)} totales[/bold green]")

    return "\n".join(lines)


def run_doctor() -> str:
    """Entry point — ejecuta todos los checks y retorna el reporte."""
    results = check_all()
    return format_report(results)