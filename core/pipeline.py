# core/pipeline.py
import sys
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from rich.console import Console

from core.query import TrendQuery
from analyzer.scorer import enrich_and_score
from analyzer.deduplicator import deduplicate
from sentiment import analyze_items
from output.json_exporter import export as export_json
from output.report_exporter import export as export_report
from core.cache import get as cache_get, set as cache_set
import scrapers.reddit as reddit
import scrapers.google_trends as gtrends
import scrapers.twitter as twitter
import scrapers.tweetclaw as tweetclaw
import scrapers.amazon as amazon
import scrapers.tiktok as tiktok

# Forzar UTF-8 en Windows para evitar encoding errors con rich
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True)

SOURCES = [
    ("Reddit", reddit.run),
    ("Google Trends", gtrends.run),
    ("Twitter/X", twitter.run),
    ("TweetClaw JSON", tweetclaw.run),
    ("Amazon", amazon.run),
    ("TikTok", tiktok.run),
]

# Scrapers que requieren I/O de red pesado (benefician mas de paralelismo)
_PARALLEL_SOURCES = {"Reddit", "Google Trends", "Amazon", "TikTok"}
# Scrapers que pueden saturar rate limits o dependen de auth frágil (mejor secuencial)
_SERIAL_SOURCES = {"Twitter/X", "TweetClaw JSON"}


def run(query: TrendQuery) -> tuple[dict, str]:
    """
    Pipeline completo: scraping -> dedup -> sentimiento -> scoring -> output.
    Ejecuta scrapers en paralelo cuando es seguro (ThreadPoolExecutor).
    Retorna (json_payload, markdown_report).
    """
    console.print(f"\n[bold cyan]TrendScope - {query.display_name}[/bold cyan]")
    console.print(f"[dim]Geo: {query.geo} | Sentimiento: {query.sentiment_engine}[/dim]\n")

    # Cache: si ya se consulto lo mismo recientemente, usar resultado cacheado
    cache_key = f"{query.mode}:{query.category or query.free_topic}:{query.geo}:{query.sentiment_engine}"
    cached = cache_get(cache_key)
    if cached:
        console.print("[dim green](resultado desde cache)[/dim green]")
        return cached

    all_items: list[dict] = []

    # Dividir fuentes en paralelas y seriales
    parallel_sources = [(n, f) for n, f in SOURCES if n in _PARALLEL_SOURCES]
    serial_sources = [(n, f) for n, f in SOURCES if n in _SERIAL_SOURCES]

    # --- Fuentes paralelas ---
    if parallel_sources:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(fn, query): name
                for name, fn in parallel_sources
            }
            for future in as_completed(futures):
                name = futures[future]
                console.print(f"  [cyan]>[/cyan] {name}...", end=" ")
                try:
                    items = future.result()
                    all_items.extend(items)
                    console.print(f"[green]OK ({len(items)} items)[/green]")
                except Exception as e:
                    logger.error(f"Pipeline - {name}: {e}")
                    console.print(f"[red]FAIL[/red]")

    # --- Fuentes seriales ---
    for name, scraper_fn in serial_sources:
        console.print(f"  [cyan]>[/cyan] {name}...", end=" ")
        try:
            items = scraper_fn(query)
            all_items.extend(items)
            console.print(f"[green]OK ({len(items)} items)[/green]")
        except Exception as e:
            logger.error(f"Pipeline - {name}: {e}")
            console.print(f"[red]FAIL[/red]")

    console.print(f"\n[yellow]Recolectado: {len(all_items)} senales[/yellow]")

    # Deduplicacion
    all_items = deduplicate(all_items)
    console.print(f"[yellow]Unicos tras deduplicar: {len(all_items)}[/yellow]")

    # Sentimiento
    console.print(f"[yellow]Analizando sentimiento ({query.sentiment_engine})...[/yellow]")
    all_items = analyze_items(all_items, query)

    # Scoring
    scored = enrich_and_score(all_items, query)

    # Export
    json_payload = export_json(scored, query)
    report = export_report(json_payload, query)

    # Guardar en cache para futuras consultas
    cache_set(cache_key, (json_payload, report))

    return json_payload, report
