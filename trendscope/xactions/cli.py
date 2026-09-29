#!/usr/bin/env python3
"""
XActions-PY — CLI
Interfaz de línea de comandos. Sin npm.

v1.3.0:
  - Carga automática de .env (TWITTER_COOKIES, TWITTER_PROXY).
  - Pool de cookies: --cookies-file acepta varias cuentas (una por línea).
  - Export NDJSON (--ndjson).
  - Comandos nuevos: analyze, track, history.
  - post soporta --media para adjuntar imágenes.

v1.4.0:
  - Decorador @with_client: elimina el boilerplate de client/finally en cada comando.
  - Version leída de importlib.metadata (fuente única en pyproject.toml).
  - search falla con error claro cuando la API bloquea la query (403) sin resultados.
"""

from __future__ import annotations

import asyncio
import csv
import functools
import json
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import click
from dotenv import load_dotenv

# Carga .env automáticamente (no rompe si no existe)
load_dotenv()

# Fix encoding para Windows (emojis, caracteres especiales)
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

from .actions import (
    bulk_unfollow,
    create_bookmark,
    delete_bookmark,
    delete_tweet,
    follow_user,
    like_tweet,
    post_thread,
    post_tweet,
    unfollow_user,
    unlike_tweet,
    upload_media,
)
from .analyzer import analyze_tweets, compare_accounts
from .client import TwitterClient
from .db import TrackerDB, compute_profile_delta
from .pool import ClientPool
from .scrapers import (
    get_bookmarks,
    get_home_timeline,
    get_trends,
    get_tweet_favoriters,
    get_tweet_replies,
    get_tweet_retweeters,
    get_user_id,
    get_user_likes,
    scrape_followers,
    scrape_following,
    scrape_non_followers,
    scrape_profile,
    scrape_tweets,
    search_tweets,
)
from .search_query import build_search_query
from .security import (
    check_cookies_file_permissions,
    redact_in_text,
    warn_cli_cookies,
)

# ─── Helpers ──────────────────────────────────────────────────────────────────

COOKIES_ENV = "TWITTER_COOKIES"
PROXY_ENV = "TWITTER_PROXY"

AnyClient = TwitterClient | ClientPool

try:
    __version__ = version("xactions-py")
except PackageNotFoundError:
    __version__ = "1.5.0"


def _load_cookies_list(cookies: str, cookies_file: str | None, from_browser: str | None = None) -> list[str]:
    """
    Devuelve la lista de strings de cookies disponibles.
    - --from-browser: lee auth_token/ct0 del navegador instalado
    - --cookies-file: soporta cookie-string, Netscape, Cookie-Editor JSON, Playwright
    - --cookies / TWITTER_COOKIES: una sola cookie, o varias separadas por '|||'
    """
    from .browser_cookies import import_from_browser, load_cookies_from_file

    if from_browser:
        imported = import_from_browser(from_browser)
        if not imported:
            raise click.ClickException(
                f"No se pudieron importar cookies desde {from_browser}. "
                "Exporta con Cookie-Editor y usa --cookies-file."
            )
        return [imported]

    raw: list[str] = []
    if cookies_file:
        if not os.path.exists(cookies_file):
            raise click.ClickException(f"Archivo no encontrado: {cookies_file}")
        perm_warn = check_cookies_file_permissions(cookies_file)
        if perm_warn:
            click.echo(f"⚠️  {perm_warn}", err=True)
        raw = load_cookies_from_file(cookies_file)
        if not raw:
            # fallback simple lines
            with open(cookies_file, encoding="utf-8") as f:
                raw = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    else:
        value = cookies or os.getenv(COOKIES_ENV, "")
        if value:
            raw = [c.strip() for c in value.split("|||") if c.strip()]
    return raw


def get_client(
    cookies: str = "",
    cookies_file: str | None = None,
    from_browser: str | None = None,
) -> AnyClient:
    """Devuelve un TwitterClient (1 cookie) o un ClientPool (varias)."""
    cookie_list = _load_cookies_list(cookies, cookies_file, from_browser=from_browser)
    cli_warn = warn_cli_cookies(cookies)
    if cli_warn:
        click.echo(f"⚠️  {cli_warn}", err=True)
    proxy = os.getenv(PROXY_ENV)
    if len(cookie_list) > 1:
        return ClientPool(cookie_list, proxy=proxy)
    return TwitterClient(cookies=cookie_list[0] if cookie_list else "", proxy=proxy)


def _safe_error_message(e: Exception) -> str:
    """Mensaje de error sin valores de cookies (por si vienen en el texto)."""
    return redact_in_text(str(e))


def with_client(func):
    """
    Decorador para comandos: extrae --cookies/--cookies-file de los kwargs,
    crea el client (o pool), lo inyecta como primer argumento, maneja errores
    y garantiza el cierre de conexiones.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cookies = kwargs.pop("cookies", "")
        cookies_file = kwargs.pop("cookies_file", None)
        from_browser = kwargs.pop("from_browser", None)
        client = get_client(cookies, cookies_file, from_browser=from_browser)
        exit_code = 0
        try:
            return func(client, *args, **kwargs)
        except SystemExit as e:
            exit_code = e.code if isinstance(e.code, int) else 1
            raise
        except Exception as e:
            click.echo(f"❌ {_safe_error_message(e)}", err=True)
            exit_code = 1
        finally:
            try:
                run(client.aclose())
            except Exception:
                pass
            if exit_code:
                sys.exit(exit_code)

    return wrapper


def run(coro):
    return asyncio.run(coro)


def print_json(data: Any, output: str | None = None):
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(out)
        click.echo(f"✅ Guardado en {output}")
    else:
        click.echo(out)


def _write_csv(path: str, rows: list[dict[str, Any]], fieldnames: list[str] | None = None):
    if not rows:
        click.echo("⚠️  No hay datos para exportar a CSV.")
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    click.echo(f"✅ CSV guardado en {path}")


def _write_ndjson(path: str, rows: list[dict[str, Any]]):
    if not rows:
        click.echo("⚠️  No hay datos para exportar a NDJSON.")
        return
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    click.echo(f"✅ NDJSON guardado en {path}")


def _flatten_users(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": u.get("id"),
            "username": u.get("username"),
            "name": u.get("name"),
            "followers": u.get("followers"),
            "following": u.get("following"),
            "verified": u.get("verified"),
            "bio": (u.get("bio") or "").replace("\n", " "),
        }
        for u in users
    ]


def _flatten_tweets(tweets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": t.get("id"),
            "url": t.get("url"),
            "author": (t.get("author") or {}).get("username"),
            "text": (t.get("text") or "").replace("\n", " "),
            "likes": t.get("likes"),
            "retweets": t.get("retweets"),
            "replies": t.get("replies"),
            "quotes": t.get("quotes"),
            "views": t.get("views"),
            "created_at": t.get("created_at"),
        }
        for t in tweets
    ]


def _handle_output(
    data: Any,
    output: str | None,
    csv_path: str | None,
    ndjson_path: str | None = None,
    csv_data: list[dict[str, Any]] | None = None,
    table_fn=None,
    table_title: str = "",
):
    if csv_path:
        _write_csv(csv_path, csv_data or [])
    elif ndjson_path:
        _write_ndjson(ndjson_path, csv_data or [])
    elif output:
        print_json(data, output)
    elif table_fn:
        table_fn(data, table_title)
    else:
        print_json(data)


def print_users_table(users: list[dict[str, Any]], title: str = ""):
    if title:
        click.echo(f"\n{'─'*50}")
        click.echo(f"  {title} ({len(users)} usuarios)")
        click.echo(f"{'─'*50}")
    for u in users:
        verified = "✓" if u.get("verified") else " "
        click.echo(
            f"  {verified} @{u.get('username', '?'):<25} "
            f"{u.get('name', ''):<25} "
            f"👥 {u.get('followers', 0):>8,}"
        )


def print_tweets_table(tweets: list[dict[str, Any]], title: str = ""):
    if title:
        click.echo(f"\n{'─'*60}")
        click.echo(f"  {title} ({len(tweets)} tweets)")
        click.echo(f"{'─'*60}")
    for t in tweets:
        author = t.get("author") or {}
        text = (t.get("text") or "")[:80].replace("\n", " ")
        likes = t.get("likes") or 0
        rts = t.get("retweets") or 0
        uname = author.get("username") or "?"
        click.echo(
            f"  @{uname:<20} "
            f"❤ {likes:>6}  "
            f"🔁 {rts:>5}  "
            f"{text}"
        )


def print_trends_table(trends: list[dict[str, Any]], title: str = ""):
    if title:
        click.echo(f"\n{'─'*50}")
        click.echo(f"  {title} ({len(trends)} trends)")
        click.echo(f"{'─'*50}")
    for i, t in enumerate(trends, 1):
        volume = t.get("tweet_volume")
        vol_str = f"{volume:>10,} tweets" if volume else ""
        click.echo(f"  {i:>2}. {t.get('name', '?')} {vol_str}")


def print_analysis(report: dict[str, Any], username: str):
    avg = report["averages"]
    click.echo(f"\n{'═'*55}")
    click.echo(f"  📊 Análisis de @{username} — {report['total_tweets']} tweets")
    click.echo(f"{'═'*55}")
    click.echo("  Promedios por tweet:")
    click.echo(f"    ❤ {avg.get('likes', 0):>10,.1f}   🔁 {avg.get('retweets', 0):>8,.1f}   "
               f"💬 {avg.get('replies', 0):>6,.1f}   👁 {avg.get('views', 0):>10,.1f}")
    if report.get("engagement_rate_followers") is not None:
        click.echo(f"  Engagement rate (followers): {report['engagement_rate_followers']}%")
    if report.get("engagement_rate_views") is not None:
        click.echo(f"  Engagement rate (views):     {report['engagement_rate_views']}%")

    content = report.get("content", {})
    if content:
        click.echo(f"\n  Contenido: {content.get('with_media_pct', 0)}% con media, "
                   f"{content.get('replies_pct', 0)}% replies, "
                   f"{content.get('quotes_pct', 0)}% quotes")

    if report.get("best_hours"):
        hours = ", ".join(f"{h['hour']:02d}:00" for h in report["best_hours"])
        click.echo(f"  Mejores horas (UTC): {hours}")
    if report.get("best_days"):
        days = ", ".join(d["day"] for d in report["best_days"])
        click.echo(f"  Mejores días:        {days}")

    if report.get("top_tweets"):
        click.echo("\n  🏆 Top tweets:")
        for t in report["top_tweets"]:
            click.echo(f"    [{t['score']:>6}] ❤{t['likes'] or 0:<6} {(t['text'] or '')[:60]}")
    click.echo(f"{'═'*55}\n")


def common_options(fn):
    """Opciones comunes para comandos de lectura."""
    fn = click.option(
        "--cookies",
        envvar=COOKIES_ENV,
        default="",
        help="Cookies de sesión (preferir .env TWITTER_COOKIES o --cookies-file)",
    )(fn)
    fn = click.option("--cookies-file", type=click.Path(exists=True), default=None,
                      help="Cookie file (line format, Netscape, Cookie-Editor JSON)")(fn)
    fn = click.option(
        "--from-browser",
        type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]),
        default=None,
        help="Import auth_token/ct0 from an installed browser profile",
    )(fn)
    fn = click.option("--output", "-o", default=None, help="Archivo JSON de salida")(fn)
    fn = click.option("--csv", "csv_path", default=None, help="Archivo CSV de salida")(fn)
    fn = click.option("--ndjson", "ndjson_path", default=None, help="Archivo NDJSON de salida")(fn)
    fn = click.option("--table", is_flag=True, help="Mostrar como tabla en vez de JSON")(fn)
    return fn


# ─── CLI principal ────────────────────────────────────────────────────────────

@click.group()
@click.version_option(__version__, prog_name="xactions-py")
def cli():
    """⚡ XActions-PY — Twitter automation sin npm."""
    pass


@cli.command()
@click.argument("username")
@common_options
@with_client
def profile(client, username, output, csv_path, ndjson_path, table):
    """Obtiene el perfil de un usuario."""
    data = run(scrape_profile(client, username))
    flat = [{
        "id": data.get("id"),
        "username": data.get("username"),
        "name": data.get("name"),
        "followers": data.get("followers"),
        "following": data.get("following"),
        "tweets_count": data.get("tweets_count"),
        "verified": data.get("verified"),
        "bio": (data.get("bio") or "").replace("\n", " "),
        "created_at": data.get("created_at"),
    }]
    if csv_path or ndjson_path or output:
        _handle_output(data, output, csv_path, ndjson_path, csv_data=flat)
    else:
        click.echo(f"\n{'─'*50}")
        click.echo(f"  @{data.get('username')} — {data.get('name')}")
        click.echo(f"  {'✓ Verificado' if data.get('verified') else 'No verificado'}")
        click.echo(f"  Bio: {data.get('bio', '')[:100]}")
        click.echo(f"  Followers: {data.get('followers', 0):,}")
        click.echo(f"  Following: {data.get('following', 0):,}")
        click.echo(f"  Tweets:    {data.get('tweets_count', 0):,}")
        click.echo(f"  Ubicación: {data.get('location', 'N/A')}")
        click.echo(f"  Creado:    {data.get('created_at', 'N/A')}")
        click.echo(f"{'─'*50}\n")


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=100, show_default=True, help="Máximo de usuarios")
@common_options
@with_client
def followers(client, username, limit, output, csv_path, ndjson_path, table):
    """Lista los followers de un usuario."""
    data = run(scrape_followers(client, username, limit=limit))
    _handle_output(
        {"count": len(data), "followers": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_users(data),
        table_fn=print_users_table if table else None,
        table_title=f"Followers de @{username}",
    )


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=100, show_default=True, help="Máximo de usuarios")
@common_options
@with_client
def following(client, username, limit, output, csv_path, ndjson_path, table):
    """Lista los usuarios que sigue una cuenta."""
    data = run(scrape_following(client, username, limit=limit))
    _handle_output(
        {"count": len(data), "following": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_users(data),
        table_fn=print_users_table if table else None,
        table_title=f"Following de @{username}",
    )


@cli.command("non-followers")
@click.argument("username")
@click.option("--limit", "-l", default=200, show_default=True, help="Cuántos following revisar")
@common_options
@with_client
def non_followers_cmd(client, username, limit, output, csv_path, ndjson_path, table):
    """Muestra quién no te sigue de vuelta."""
    data = run(scrape_non_followers(client, username, limit=limit))
    _handle_output(
        {"count": len(data), "non_followers": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_users(data),
        table_fn=print_users_table if table else None,
        table_title=f"No te siguen de vuelta (@{username})",
    )


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de tweets")
@click.option("--replies", is_flag=True, help="Incluir respuestas")
@common_options
@with_client
def tweets(client, username, limit, replies, output, csv_path, ndjson_path, table):
    """Obtiene los tweets recientes de un usuario."""
    data = run(scrape_tweets(client, username, limit=limit, include_replies=replies))
    _handle_output(
        {"count": len(data), "tweets": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title=f"Tweets de @{username}",
    )


@cli.command()
@click.argument("query", required=False, default="")
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de resultados")
@click.option("--mode", default="Top", type=click.Choice(["Latest", "Top"]), show_default=True)
@click.option("--from", "from_user", default=None, help="Operador from:USERNAME")
@click.option("--to", "to_user", default=None, help="Operador to:USERNAME")
@click.option("--since", default=None, help="since:YYYY-MM-DD")
@click.option("--until", default=None, help="until:YYYY-MM-DD")
@click.option("--min-faves", type=int, default=None, help="min_faves:N")
@click.option("--min-retweets", type=int, default=None, help="min_retweets:N")
@click.option("--lang", default=None, help="lang:es|en|...")
@click.option("--exclude-retweets", is_flag=True, help="-filter:retweets")
@click.option("--exclude-replies", is_flag=True, help="-filter:replies")
@click.option("--media", "filter_media", is_flag=True, help="filter:media")
@common_options
@with_client
def search(
    client, query, limit, mode, from_user, to_user, since, until,
    min_faves, min_retweets, lang, exclude_retweets, exclude_replies, filter_media,
    output, csv_path, ndjson_path, table,
):
    """Busca tweets por query (acepta operadores avanzados)."""
    q = build_search_query(
        query,
        from_user=from_user,
        to_user=to_user,
        since=since,
        until=until,
        min_faves=min_faves,
        min_retweets=min_retweets,
        lang=lang,
        exclude_retweets=exclude_retweets,
        exclude_replies=exclude_replies,
        filter_media=filter_media,
    )
    if not q.strip():
        raise click.ClickException("Query vacía: pasa un término o flags (--from, --lang, …)")
    data = run(search_tweets(client, q, limit=limit, mode=mode))
    _handle_output(
        {"query": q, "count": len(data), "tweets": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title=f'Resultados: "{q}" ({mode})',
    )


@cli.command()
@click.argument("tweet_id")
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de replies")
@common_options
@with_client
def replies(client, tweet_id, limit, output, csv_path, ndjson_path, table):
    """Obtiene replies/conversación de un tweet."""
    data = run(get_tweet_replies(client, tweet_id, limit=limit))
    _handle_output(
        {"tweet_id": tweet_id, "count": len(data), "tweets": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title=f"Replies a {tweet_id}",
    )


@cli.command()
@click.argument("tweet_id")
@click.option("--limit", "-l", default=100, show_default=True, help="Cantidad de usuarios")
@common_options
@with_client
def likers(client, tweet_id, limit, output, csv_path, ndjson_path, table):
    """Usuarios que dieron like a un tweet."""
    data = run(get_tweet_favoriters(client, tweet_id, limit=limit))
    _handle_output(
        {"tweet_id": tweet_id, "count": len(data), "users": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_users(data),
        table_fn=print_users_table if table else None,
        table_title=f"Likers de {tweet_id}",
    )


@cli.command()
@click.argument("tweet_id")
@click.option("--limit", "-l", default=100, show_default=True, help="Cantidad de usuarios")
@common_options
@with_client
def retweeters(client, tweet_id, limit, output, csv_path, ndjson_path, table):
    """Usuarios que hicieron retweet a un tweet."""
    data = run(get_tweet_retweeters(client, tweet_id, limit=limit))
    _handle_output(
        {"tweet_id": tweet_id, "count": len(data), "users": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_users(data),
        table_fn=print_users_table if table else None,
        table_title=f"Retweeters de {tweet_id}",
    )


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de tweets")
@common_options
@with_client
def likes(client, username, limit, output, csv_path, ndjson_path, table):
    """Tweets a los que les dio like un usuario."""
    data = run(get_user_likes(client, username, limit=limit))
    _handle_output(
        {"username": username, "count": len(data), "tweets": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title=f"Likes de @{username}",
    )


@cli.command()
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de bookmarks")
@common_options
@with_client
def bookmarks(client, limit, output, csv_path, ndjson_path, table):
    """Bookmarks del usuario autenticado."""
    data = run(get_bookmarks(client, limit=limit))
    _handle_output(
        {"count": len(data), "bookmarks": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title="Bookmarks",
    )


@cli.command()
@click.option("--woeid", default=1, show_default=True, help="Yahoo Where On Earth ID (1=worldwide)")
@common_options
@with_client
def trends(client, woeid, output, csv_path, ndjson_path, table):
    """Trending topics de Twitter/X."""
    data = run(get_trends(client, woeid=woeid))
    _handle_output(
        {"count": len(data), "trends": data},
        output, csv_path, ndjson_path,
        csv_data=data,
        table_fn=print_trends_table if table else None,
        table_title="Trending topics",
    )


@cli.command()
@click.option("--limit", "-l", default=50, show_default=True, help="Cantidad de tweets")
@click.option("--latest", is_flag=True, help="Usar HomeLatestTimeline en vez de HomeTimeline")
@common_options
@with_client
def home(client, limit, latest, output, csv_path, ndjson_path, table):
    """Home timeline del usuario autenticado."""
    data = run(get_home_timeline(client, limit=limit, latest=latest))
    _handle_output(
        {"count": len(data), "tweets": data},
        output, csv_path, ndjson_path,
        csv_data=_flatten_tweets(data),
        table_fn=print_tweets_table if table else None,
        table_title="Home timeline",
    )


# ─── Analytics & tracking ─────────────────────────────────────────────────────

@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=100, show_default=True, help="Tweets a analizar")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
@with_client
def analyze(client, username, limit, output):
    """Analiza el engagement de un usuario (promedios, top tweets, mejores horas)."""

    async def _analyze():
        prof = await scrape_profile(client, username)
        tw = await scrape_tweets(client, username, limit=limit)
        return prof, tw

    prof, tw = run(_analyze())
    report = analyze_tweets(tw, profile=prof)
    report["username"] = username
    report["followers"] = prof.get("followers")

    if output:
        print_json(report, output)
    else:
        print_analysis(report, username)


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=50, show_default=True, help="Tweets a trackear")
@click.option("--db", "db_path", default=None, help="Path de la base SQLite (default ~/.xactions/xactions.db)")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def track(client, username, limit, db_path):
    """Guarda un snapshot de métricas de un usuario en SQLite y muestra el delta."""
    db = TrackerDB(db_path)

    async def _collect():
        prof = await scrape_profile(client, username)
        tw = await scrape_tweets(client, username, limit=limit)
        return prof, tw

    prof, tw = run(_collect())

    previous = db.get_last_profile_snapshot(username)
    delta = compute_profile_delta(previous, prof)

    db.save_profile_snapshot(username, prof)
    saved = db.save_tweet_snapshots(tw)

    click.echo(f"\n📸 Snapshot guardado para @{username} ({saved} tweets)")
    click.echo(f"  Followers: {prof.get('followers', 0):,}")
    if delta["followers_delta"] is not None:
        sign = "+" if delta["followers_delta"] >= 0 else ""
        click.echo(f"  Δ followers: {sign}{delta['followers_delta']:,} (desde {delta.get('since')})")
        click.echo(f"  Δ tweets:    {'+' if delta['tweets_delta'] >= 0 else ''}{delta['tweets_delta']:,}")
    else:
        click.echo("  (primer snapshot — corre el comando de nuevo para ver deltas)")
    click.echo(f"  DB: {db.path}\n")


@cli.command()
@click.argument("username")
@click.option("--limit", "-l", default=30, show_default=True, help="Snapshots a mostrar")
@click.option("--db", "db_path", default=None, help="Path de la base SQLite")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
def history(username, limit, db_path, output):
    """Muestra el histórico de snapshots de un usuario trackeado."""
    try:
        db = TrackerDB(db_path)
        rows = db.get_profile_history(username, limit=limit)

        if output:
            print_json({"username": username, "count": len(rows), "history": rows}, output)
            return

        if not rows:
            click.echo(f"⚠️  No hay snapshots de @{username}. Usa: xactions track {username}")
            return

        click.echo(f"\n{'─'*60}")
        click.echo(f"  📈 Histórico de @{username} ({len(rows)} snapshots)")
        click.echo(f"{'─'*60}")
        click.echo(f"  {'Fecha':<22} {'Followers':>12} {'Following':>12} {'Tweets':>10}")
        for r in reversed(rows):
            click.echo(
                f"  {r['captured_at']:<22} {r['followers']:>12,} "
                f"{r['following']:>12,} {r['tweets_count']:>10,}"
            )
        click.echo(f"{'─'*60}\n")
    except Exception as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)


# ─── Write actions ────────────────────────────────────────────────────────────

@cli.command()
@click.argument("text")
@click.option("--reply-to", default=None, help="ID del tweet al que responder")
@click.option("--media", "media_files", multiple=True, type=click.Path(exists=True),
              help="Imagen a adjuntar (se puede repetir, máx 4)")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def post(client, text, reply_to, media_files):
    """Publica un tweet. Requiere auth_token."""
    from .drafts import approval_required, create_draft

    if approval_required() and not media_files:
        draft = create_draft(
            "post_tweet",
            {"text": text, "reply_to_id": reply_to},
        )
        click.echo(f"📝 Draft saved (approval required): {draft['id']}")
        click.echo("   Review: xactions drafts list → xactions drafts approve <id>")
        return

    async def _post():
        media_ids = []
        for path in media_files[:4]:
            up = await upload_media(client, path)
            media_ids.append(up["media_id"])
            click.echo(f"📎 Media subida: {path} (id {up['media_id']})")
        return await post_tweet(client, text, reply_to_id=reply_to, media_ids=media_ids)

    result = run(_post())
    if result["success"]:
        click.echo(f"✅ Tweet publicado! ID: {result['tweet_id']}")
    else:
        click.echo(f"❌ No se pudo publicar. {result.get('error') or ''}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("tweets", nargs=-1)
@click.option("--from-file", type=click.Path(exists=True), default=None,
              help="Archivo de texto: un tweet por línea o separados por ---")
@click.option("--delay", default=1.5, show_default=True, help="Segundos entre tweets del hilo")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def thread(client, tweets, from_file, delay):
    """Publica un hilo. Cada argumento es un tweet, o usa --from-file."""
    parts: list[str] = []
    if from_file:
        raw = open(from_file, encoding="utf-8").read()
        # separar por --- o saltos dobles si no hay ---
        if "\n---\n" in raw or raw.strip().startswith("---"):
            chunks = [c.strip() for c in re.split(r"\n?---\n?", raw) if c.strip()]
        else:
            chunks = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        parts.extend(chunks)
    parts.extend(t.strip() for t in tweets if t and t.strip())

    if not parts:
        raise click.ClickException("Pasa tweets como argumentos o usa --from-file")

    click.echo(f"🧵 Publicando hilo de {len(parts)} tweets…")
    result = run(post_thread(client, parts, delay_seconds=delay))
    if result["success"]:
        click.echo(f"✅ Hilo publicado. Root: {result['root_id']} ({result['count']} tweets)")
    else:
        click.echo(f"❌ {result.get('error', 'Error')}", err=True)
        if result.get("tweet_ids"):
            click.echo(f"   Publicados parcialmente: {', '.join(result['tweet_ids'])}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("user_a")
@click.argument("user_b")
@click.option("--limit", "-l", default=50, show_default=True, help="Tweets a analizar por cuenta")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@click.option("--table", is_flag=True, help="Mostrar como tabla")
@with_client
def compare(client, user_a, user_b, limit, output, table):
    """Compara dos cuentas: followers, engagement rate y promedios."""

    async def _collect():
        prof_a, tw_a, prof_b, tw_b = await asyncio.gather(
            scrape_profile(client, user_a),
            scrape_tweets(client, user_a, limit=limit),
            scrape_profile(client, user_b),
            scrape_tweets(client, user_b, limit=limit),
        )
        return prof_a, tw_a, prof_b, tw_b

    prof_a, tw_a, prof_b, tw_b = run(_collect())
    report = compare_accounts(prof_a, tw_a, prof_b, tw_b)

    if output:
        print_json(report, output)
        return

    a, b = report["a"], report["b"]
    click.echo(f"\n{'═'*60}")
    click.echo(f"  Comparativa @{a['username']} vs @{b['username']}")
    click.echo(f"{'═'*60}")
    click.echo(f"  {'Métrica':<28} {'@' + str(a['username']):>14} {'@' + str(b['username']):>14}")
    click.echo(f"  {'-'*56}")
    rows = [
        ("Followers", a.get("followers"), b.get("followers")),
        ("Following", a.get("following"), b.get("following")),
        ("Tweets (total)", a.get("tweets_count"), b.get("tweets_count")),
        ("Avg likes", (a.get("averages") or {}).get("likes"), (b.get("averages") or {}).get("likes")),
        ("Avg RTs", (a.get("averages") or {}).get("retweets"), (b.get("averages") or {}).get("retweets")),
        ("Avg views", (a.get("averages") or {}).get("views"), (b.get("averages") or {}).get("views")),
        ("ER followers %", a.get("engagement_rate_followers"), b.get("engagement_rate_followers")),
    ]
    for label, va, vb in rows:
        fa = f"{va:,}" if isinstance(va, (int, float)) else "—"
        fb = f"{vb:,}" if isinstance(vb, (int, float)) else "—"
        click.echo(f"  {label:<28} {fa:>14} {fb:>14}")
    winners = report.get("winner") or {}
    click.echo(f"\n  Ganadores: followers={winners.get('followers')} · "
               f"ER={winners.get('engagement_rate_followers')} · "
               f"likes={winners.get('avg_likes')}")
    click.echo(f"{'═'*60}\n")


@cli.command()
@click.argument("tweet_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def delete(client, tweet_id):
    """Elimina un tweet por ID. Requiere auth_token."""
    result = run(delete_tweet(client, tweet_id))
    click.echo("✅ Tweet eliminado." if result["success"] else "❌ No se pudo eliminar.")


@cli.command()
@click.argument("tweet_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def like(client, tweet_id):
    """Da like a un tweet. Requiere auth_token."""
    from .drafts import approval_required, create_draft

    if approval_required():
        draft = create_draft("like", {"tweet_id": tweet_id})
        click.echo(f"📝 Draft saved: {draft['id']} — approve with: xactions drafts approve {draft['id']}")
        return
    result = run(like_tweet(client, tweet_id))
    click.echo("✅ Like dado." if result["success"] else "❌ Error dando like.")


@cli.command()
@click.argument("tweet_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def unlike(client, tweet_id):
    """Quita el like de un tweet. Requiere auth_token."""
    result = run(unlike_tweet(client, tweet_id))
    click.echo("✅ Like quitado." if result["success"] else "❌ Error quitando like.")


@cli.command()
@click.argument("tweet_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def bookmark(client, tweet_id):
    """Agrega un tweet a bookmarks. Requiere auth_token."""
    result = run(create_bookmark(client, tweet_id))
    click.echo("✅ Bookmark agregado." if result["success"] else "❌ Error agregando bookmark.")


@cli.command()
@click.argument("tweet_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def unbookmark(client, tweet_id):
    """Elimina un tweet de bookmarks. Requiere auth_token."""
    result = run(delete_bookmark(client, tweet_id))
    click.echo("✅ Bookmark eliminado." if result["success"] else "❌ Error eliminando bookmark.")


@cli.command()
@click.argument("username")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def follow(client, username):
    """Sigue a un usuario. Requiere auth_token."""
    user_id = run(get_user_id(client, username))
    result = run(follow_user(client, user_id))
    click.echo(f"✅ Siguiendo a @{username}." if result["success"] else f"❌ Error siguiendo a @{username}.")


@cli.command()
@click.argument("username")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def unfollow(client, username):
    """Deja de seguir a un usuario. Requiere auth_token."""
    user_id = run(get_user_id(client, username))
    result = run(unfollow_user(client, user_id))
    click.echo(f"✅ Unfollow de @{username}." if result["success"] else f"❌ Error en unfollow de @{username}.")


@cli.command("bulk-unfollow")
@click.argument("username")
@click.option("--limit", "-l", default=200, show_default=True, help="Cuántos following revisar")
@click.option("--delay", default=2.0, show_default=True, help="Segundos entre unfollows")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@click.option("--dry-run", is_flag=True, help="Solo muestra quién sería unfollowed, sin hacer nada")
@with_client
def bulk_unfollow_cmd(client, username, limit, delay, dry_run):
    """
    Unfollow masivo de cuentas que no te siguen de vuelta.
    ⚠️  Usa --dry-run primero para ver qué pasaría.
    """
    try:
        non_followers = run(scrape_non_followers(client, username, limit=limit))

        if not non_followers:
            click.echo("✅ ¡Todos tus following te siguen de vuelta!")
            return

        click.echo(f"\n📋 Encontrados {len(non_followers)} no-followers:")
        print_users_table(non_followers[:10])
        if len(non_followers) > 10:
            click.echo(f"  ... y {len(non_followers) - 10} más")

        if dry_run:
            click.echo("\n🔍 Dry-run: no se hizo nada. Remueve --dry-run para ejecutar.")
            return

        click.confirm(f"\n⚠️  ¿Hacer unfollow de {len(non_followers)} usuarios?", abort=True)

        user_ids = [u["id"] for u in non_followers if u.get("id")]

        with click.progressbar(length=len(user_ids), label="Unfollowing") as bar:
            def on_progress(current, total, uid):
                bar.update(1)

            result = run(bulk_unfollow(client, user_ids, delay_seconds=delay, on_progress=on_progress))

        click.echo(
            f"\n✅ Completado: {result['success']} éxitos, {result['failed']} fallos de {result['total']} total."
        )

    except click.Abort:
        click.echo("\nCancelado.")


@cli.command()
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@with_client
def validate(client):
    """Valida que las cookies funcionan contra la API (todas las del pool)."""
    result = run(client.validate_cookies())
    if "accounts" in result:
        # Pool multi-cuenta
        click.echo(f"\n🔐 Pool: {result['alive']}/{result['total']} cuentas vivas")
        for acc in result["accounts"]:
            if acc.get("valid"):
                click.echo(f"  ✅ cuenta #{acc['account']}: @{acc.get('username')}")
            else:
                click.echo(f"  ❌ cuenta #{acc['account']}: {acc.get('error')}")
        if result["alive"] == 0:
            sys.exit(1)
    elif result.get("valid"):
        click.echo(f"✅ Cookies válidas. @{result.get('username')} ({result.get('user_id')})")
    else:
        click.echo(f"❌ Cookies inválidas: {result.get('error')}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, show_default=True)
@click.option("--mode", default="Latest", type=click.Choice(["Latest", "Top"]))
@click.option("--loop", "loop_interval", type=float, default=0, help="Seconds between polls (0 = once)")
@click.option("--max-polls", type=int, default=0, help="Stop after N polls when --loop > 0 (0 = forever)")
@common_options
@with_client
def watch(client, query, limit, mode, loop_interval, max_polls, output, csv_path, ndjson_path, table):
    """Poll a search and print only new tweets (delta)."""
    from .notify import format_tweet_alert, make_notifier
    from .watch import watch_search_once

    notify = make_notifier()
    polls = 0
    while True:
        result = run(watch_search_once(client, query, limit=limit, mode=mode))
        polls += 1
        new = result["new_tweets"]
        if new:
            alert = format_tweet_alert(new, query)
            notify(alert)
            _handle_output(
                {"query": query, "new_count": result["new_count"], "tweets": new},
                output, csv_path, ndjson_path,
                csv_data=_flatten_tweets(new),
                table_fn=print_tweets_table if table else None,
                table_title=f"New for “{query}”",
            )
        else:
            click.echo(f"… no new tweets for “{query}” (poll {polls})")
        if loop_interval <= 0:
            break
        if max_polls and polls >= max_polls:
            break
        import time as _time
        _time.sleep(loop_interval)


@cli.command("download-media")
@click.argument("username")
@click.option("--limit", "-l", default=30, show_default=True, help="Tweets to scan for media")
@click.option("--dest", default="media", show_default=True, help="Output directory")
@click.option("--max-files", default=50, show_default=True)
@common_options
@with_client
def download_media_cmd(client, username, limit, dest, max_files, output, csv_path, ndjson_path, table):
    """Download photos/videos from a user's recent tweets."""
    from .media import collect_media_urls, download_media

    tweets = run(scrape_tweets(client, username, limit=limit))
    urls = collect_media_urls(tweets)
    result = run(download_media(urls, dest, max_files=max_files))
    result["media_found"] = len(urls)
    if output:
        print_json(result, output)
        return
    click.echo(
        f"📁 {len(result['downloaded'])} downloaded, "
        f"{len(result['skipped'])} skipped, {len(result['failed'])} failed → {result['dest']}"
    )


@cli.command("snapshot-followers")
@click.argument("username")
@click.option("--limit", "-l", default=200, show_default=True)
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def snapshot_followers(client, username, limit):
    """Save a follower snapshot for later unfollower diff."""
    from .media import save_follower_snapshot

    followers = run(scrape_followers(client, username, limit=limit))
    ids = [str(u["id"]) for u in followers if u.get("id")]
    save_follower_snapshot(username, ids)
    click.echo(f"💾 Saved {len(ids)} followers for @{username}")


@cli.command("unfollowers")
@click.argument("username")
@click.option("--limit", "-l", default=200, show_default=True)
@click.option("--save", "do_save", is_flag=True, help="Also save this run as new snapshot")
@click.option("--output", "-o", default=None)
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def unfollowers_cmd(client, username, limit, do_save, output):
    """Diff current followers vs last snapshot (who unfollowed)."""
    from .media import diff_followers, load_follower_snapshot, save_follower_snapshot

    prev = load_follower_snapshot(username)
    if prev is None:
        raise click.ClickException(
            f"No snapshot for @{username}. Run: xactions snapshot-followers {username}"
        )
    followers = run(scrape_followers(client, username, limit=limit))
    ids = [str(u["id"]) for u in followers if u.get("id")]
    diff = diff_followers(prev, ids)
    report = {
        "username": username,
        "previous_count": len(prev),
        "current_count": len(ids),
        "unfollowed_count": len(diff["unfollowed"]),
        "new_followers_count": len(diff["new_followers"]),
        **diff,
    }
    if do_save:
        save_follower_snapshot(username, ids)
    if output:
        print_json(report, output)
        return
    click.echo(
        f"📉 @{username}: {report['unfollowed_count']} unfollowed, "
        f"{report['new_followers_count']} new (prev {report['previous_count']} → now {report['current_count']})"
    )
    for uid in diff["unfollowed"][:20]:
        click.echo(f"  - {uid}")
    if report["unfollowed_count"] > 20:
        click.echo(f"  … and {report['unfollowed_count'] - 20} more")


@cli.command()
@click.argument("target")
@click.argument("target_b", required=False)
@click.option("--limit", "-l", default=50, show_default=True, help="Tweets to sample")
@click.option("--format", "fmt", type=click.Choice(["md", "html"]), default="md")
@click.option("--out", "out_path", default=None, help="Write report to file (default stdout)")
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def report(client, target, target_b, limit, fmt, out_path):
    """
    Generate a shareable engagement report.

    xactions report USERNAME
    xactions report USER_A USER_B --format html --out compare.html
    """
    from .report import (
        render_account_report_html,
        render_account_report_md,
        render_compare_report_html,
        render_compare_report_md,
    )

    if target_b:
        async def _cmp():
            return await asyncio.gather(
                scrape_profile(client, target),
                scrape_tweets(client, target, limit=limit),
                scrape_profile(client, target_b),
                scrape_tweets(client, target_b, limit=limit),
            )

        pa, ta, pb, tb = run(_cmp())
        content = (
            render_compare_report_html(pa, ta, pb, tb)
            if fmt == "html"
            else render_compare_report_md(pa, ta, pb, tb)
        )
    else:
        async def _one():
            return await asyncio.gather(
                scrape_profile(client, target),
                scrape_tweets(client, target, limit=limit),
            )

        prof, tw = run(_one())
        content = (
            render_account_report_html(prof, tw)
            if fmt == "html"
            else render_account_report_md(prof, tw)
        )

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        click.echo(f"✅ Report written to {out_path}")
    else:
        click.echo(content)


@cli.command()
@click.argument("query", required=False, default="")
@click.option("--file", "file_path", type=click.Path(exists=True), default=None, help="JSON list of tweets")
@click.option("--limit", "-l", default=30, show_default=True)
@click.option("--output", "-o", default=None)
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def sentiment(client, query, file_path, limit, output):
    """Score sentiment of a search query or a JSON tweet file (lightweight lexicon)."""
    from .sentiment import score_tweets, summarize_sentiment

    if file_path:
        data = json.loads(open(file_path, encoding="utf-8").read())
        tweets = data if isinstance(data, list) else data.get("tweets") or []
    elif query:
        tweets = run(search_tweets(client, query, limit=limit, mode="Latest"))
    else:
        raise click.ClickException("Pass a search query or --file tweets.json")

    scored = score_tweets(tweets)
    summary = summarize_sentiment(scored)
    payload = {"summary": summary, "tweets": scored}
    if output:
        print_json(payload, output)
        return
    s = summary
    click.echo(
        f"Sentiment n={s['count']} avg={s['avg_score']:+.3f} "
        f"pos={s['positive']} neu={s['neutral']} neg={s['negative']}"
    )
    for t in scored[:10]:
        sent = t["sentiment"]
        click.echo(f"  [{sent['label'][:3]} {sent['score']:+.2f}] {(t.get('text') or '')[:70]}")


@cli.command()
@click.argument("query")
@click.option("--like", is_flag=True, help="Like matching tweets")
@click.option("--retweet", is_flag=True, help="Retweet matching tweets")
@click.option("--limit", "-l", default=10, show_default=True, help="Max tweets to consider")
@click.option("--delay", default=3.0, show_default=True, help="Seconds between write actions")
@click.option("--min-likes", type=int, default=None, help="Skip tweets below this like count")
@click.option("--dry-run", is_flag=True, default=True, help="Preview only (default)")
@click.option("--execute", is_flag=True, help="Actually perform likes/RTs (uses daily caps)")
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def engage(client, query, like, retweet, limit, delay, min_likes, dry_run, execute):
    """
    Engage with search results (like / retweet) with delay and daily caps.

    Always preview with --dry-run; add --execute to write.
    """
    from .actions import like_tweet
    from .actions import retweet as rt_action
    from .caps import WriteCapExceeded
    from .scrapers import search_tweets

    if not like and not retweet:
        raise click.ClickException("Pass --like and/or --retweet")
    if execute:
        dry_run = False

    tweets = run(search_tweets(client, query, limit=limit, mode="Latest"))
    if min_likes is not None:
        tweets = [t for t in tweets if (t.get("likes") or 0) >= min_likes]

    click.echo(f"Found {len(tweets)} tweets for “{query}”")
    planned = []
    for t in tweets:
        planned.append(
            {
                "id": t.get("id"),
                "like": like,
                "retweet": retweet,
                "likes": t.get("likes"),
                "text": (t.get("text") or "")[:60],
            }
        )

    if dry_run:
        click.echo("🔍 DRY-RUN — nothing will be written. Use --execute to run.")
        for p in planned:
            acts = "+".join([a for a, on in (("like", p["like"]), ("rt", p["retweet"])) if on])
            click.echo(f"  [{acts}] {p['id']} ❤{p['likes']} {p['text']}")
        return

    done = {"like": 0, "retweet": 0, "skipped": 0, "failed": 0}
    import time as _time

    for p in planned:
        tid = p["id"]
        if not tid:
            continue
        try:
            if p["like"]:
                r = run(like_tweet(client, str(tid)))
                if r.get("success"):
                    done["like"] += 1
                else:
                    done["failed"] += 1
                _time.sleep(delay)
            if p["retweet"]:
                r = run(rt_action(client, str(tid)))
                if r.get("success"):
                    done["retweet"] += 1
                else:
                    done["failed"] += 1
                _time.sleep(delay)
        except WriteCapExceeded as e:
            click.echo(f"🛑 Cap reached: {e}", err=True)
            done["skipped"] += 1
            break
    click.echo(
        f"Engage done: likes={done['like']} rts={done['retweet']} "
        f"failed={done['failed']} stopped_cap={done['skipped']}"
    )


@cli.command()
@click.argument("pipeline_file", type=click.Path(exists=True))
@click.option("--execute", is_flag=True, help="Allow write steps (like); default is dry-run")
@click.option("--output", "-o", default=None, help="JSON result file")
@click.option("--cookies", envvar=COOKIES_ENV, default="")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
@with_client
def pipeline(client, pipeline_file, execute, output, cookies, cookies_file, from_browser):
    """Run a declarative JSON pipeline (search → filter → notify/report/like)."""
    from .pipeline import run_pipeline

    result = run(run_pipeline(client, pipeline_file, dry_run=not execute))
    # drop full tweet dump from CLI JSON unless requested via file
    payload = {k: v for k, v in result.items() if k != "tweets"}
    payload["tweet_count"] = len(result.get("tweets") or [])
    if output:
        print_json(payload, output)
        return
    click.echo(f"Pipeline {payload.get('name')}: {payload['tweet_count']} tweets after steps")
    for entry in payload.get("log") or []:
        click.echo(f"  {entry}")
    if result.get("dry_run"):
        click.echo("(dry-run: write steps skipped — use --execute to run likes)")


# ─── GraphQL endpoints ────────────────────────────────────────────────────────

@cli.command("gql-status")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
def gql_status(output):
    """Muestra el estado del cache de GraphQL query IDs."""
    from .client import _DEFAULT_GRAPHQL_ENDPOINTS, GRAPHQL_ENDPOINTS
    from .gql_refresh import cache_status

    status = cache_status()
    payload = {
        **status,
        "loaded": {
            name: {
                "queryId": ep.get("queryId"),
                "operationName": ep.get("operationName"),
                "method": ep.get("method", "GET"),
            }
            for name, ep in sorted(GRAPHQL_ENDPOINTS.items())
        },
        "defaults_count": len(_DEFAULT_GRAPHQL_ENDPOINTS),
    }
    if output:
        print_json(payload, output)
        return

    click.echo(f"\n{'─'*55}")
    click.echo("  GraphQL query IDs")
    click.echo(f"{'─'*55}")
    if status["exists"]:
        click.echo(f"  Cache:  {status['path']}")
        click.echo(f"  Update: {status.get('updated_at')}")
        click.echo(f"  Source: {status.get('source')}")
    else:
        click.echo(f"  Cache:  (sin archivo) {status['path']}")
        click.echo("  Usando solo defaults embebidos")
    click.echo(f"  Endpoints cargados: {len(GRAPHQL_ENDPOINTS)}")
    click.echo(f"{'─'*55}\n")


@cli.command("gql-refresh")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión (mejora el crawl logueado)")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
def gql_refresh_cmd(cookies, cookies_file, output):
    """
    Actualiza los GraphQL query IDs.

    Con cookies se prioriza el bundle logueado de X; sin ellas se intenta
    anónimo y se cae a twikit como fallback.
    """
    from .client import refresh_graphql_endpoints

    cookie_list = _load_cookies_list(cookies, cookies_file)
    cookie = cookie_list[0] if cookie_list else None
    if cookie:
        click.echo("🔐 Usando cookies para crawl logueado (sin imprimir el token)")
    merged = run(refresh_graphql_endpoints(force=True, cookie=cookie))
    changed = {
        name: ep.get("queryId")
        for name, ep in sorted(merged.items())
        if ep.get("queryId")
    }
    if output:
        print_json({"count": len(changed), "endpoints": changed}, output)
        return
    click.echo(f"\n✅ GraphQL endpoints actualizados ({len(changed)} con queryId)")
    for name, qid in list(changed.items())[:8]:
        click.echo(f"  {name}: {qid}")
    if len(changed) > 8:
        click.echo(f"  … y {len(changed) - 8} más")
    click.echo("")


@cli.command()
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None, help="Archivo con cookies")
@click.option("--output", "-o", default=None, help="Archivo JSON de salida")
@click.option("--json", "as_json", is_flag=True, help="Imprimir JSON en stdout")
def doctor(cookies, cookies_file, output, as_json):
    """Check local setup: cookies, GraphQL cache, write caps, DB."""
    from .doctor import run_doctor

    report = run_doctor(cookies=cookies or None, cookies_file=cookies_file)
    if output:
        print_json(report, output)
        return
    if as_json:
        click.echo(json.dumps(report, ensure_ascii=False, indent=2))
        if not report["ok"]:
            sys.exit(1)
        return

    icon = {"ok": "✅", "warn": "⚠️ ", "error": "❌"}
    click.echo(f"\n{'─'*55}")
    click.echo(f"  🩺 xactions doctor — {report['summary']}")
    click.echo(f"{'─'*55}")
    for c in report["checks"]:
        click.echo(f"  {icon.get(c['status'], '•')} {c['check']:<14} {c['message']}")
    click.echo(f"{'─'*55}\n")
    if not report["ok"]:
        sys.exit(1)


@cli.group()
def drafts():
    """Review and release write drafts (approval gate)."""
    pass


@drafts.command("list")
@click.option("--all", "show_all", is_flag=True, help="Include executed/discarded")
@click.option("--output", "-o", default=None, help="JSON output file")
def drafts_list(show_all, output):
    from .drafts import list_drafts

    items = list_drafts(status=None if show_all else "pending")
    if output:
        print_json({"count": len(items), "drafts": items}, output)
        return
    if not items:
        click.echo("No pending drafts.")
        return
    click.echo(f"\n{'─'*55}\n  📝 {len(items)} draft(s)\n{'─'*55}")
    for d in items:
        params = json.dumps(d.get("params"), ensure_ascii=False)
        if len(params) > 60:
            params = params[:57] + "..."
        click.echo(f"  {d['id']}  [{d.get('status')}]  {d.get('action')}  {params}")
    click.echo(f"{'─'*55}\n")


@drafts.command("approve")
@click.argument("draft_id")
@click.option("--cookies", envvar=COOKIES_ENV, default="", help="Cookies de sesión")
@click.option("--cookies-file", type=click.Path(exists=True), default=None)
@click.option("--from-browser", type=click.Choice(["chrome", "chromium", "brave", "edge", "firefox"]), default=None)
def drafts_approve(draft_id, cookies, cookies_file, from_browser):
    """Mark draft approved and execute it now."""
    from .actions import (
        create_bookmark,
        delete_tweet,
        follow_user,
        like_tweet,
        post_tweet,
        unfollow_user,
        unlike_tweet,
    )
    from .drafts import approve as approve_draft
    from .drafts import load_draft, mark_executed

    draft = load_draft(draft_id)
    if not draft:
        raise click.ClickException(f"Draft not found: {draft_id}")
    if draft.get("status") != "pending":
        raise click.ClickException(f"Draft {draft_id} is {draft.get('status')}, not pending")

    approve_draft(draft_id)
    action = draft.get("action")
    params = draft.get("params") or {}
    client = get_client(cookies, cookies_file, from_browser=from_browser)
    try:
        if action == "post_tweet":
            result = run(post_tweet(client, **params))
        elif action == "like":
            result = run(like_tweet(client, **params))
        elif action == "unlike":
            result = run(unlike_tweet(client, **params))
        elif action == "delete":
            result = run(delete_tweet(client, **params))
        elif action == "follow":
            user_id = params.get("user_id") or run(get_user_id(client, params["username"]))
            result = run(follow_user(client, user_id))
        elif action == "unfollow":
            user_id = params.get("user_id") or run(get_user_id(client, params["username"]))
            result = run(unfollow_user(client, user_id))
        elif action == "bookmark":
            result = run(create_bookmark(client, **params))
        else:
            raise click.ClickException(f"Unknown draft action: {action}")
        mark_executed(draft_id, result)
        if result.get("success"):
            click.echo(f"✅ Draft {draft_id} executed ({action}).")
        else:
            click.echo(f"❌ Draft {draft_id} failed: {result}", err=True)
            sys.exit(1)
    finally:
        run(client.aclose())


@drafts.command("discard")
@click.argument("draft_id")
def drafts_discard(draft_id):
    from .drafts import discard

    d = discard(draft_id)
    if not d:
        raise click.ClickException(f"Draft not found: {draft_id}")
    click.echo(f"🗑️  Draft {draft_id} discarded.")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
