# core/pipeline.py
import hashlib
import sys
import io
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger
from rich.console import Console

from trendscope.core.query import TrendQuery
from trendscope.analyzer.scorer import enrich_and_score
from trendscope.analyzer.deduplicator import deduplicate
from trendscope.analyzer.insights import generate_insights
from trendscope.sentiment import analyze_items
from trendscope.output.json_exporter import export as export_json
from trendscope.output.report_exporter import export as export_report
from trendscope.core.cache import get as cache_get, set as cache_set
import trendscope.scrapers.reddit as reddit
import trendscope.scrapers.google_trends as gtrends
import trendscope.scrapers.twitter as twitter
import trendscope.scrapers.tweetclaw as tweetclaw
import trendscope.scrapers.amazon as amazon
import trendscope.scrapers.tiktok as tiktok
import trendscope.scrapers.hackernews as hackernews
import trendscope.scrapers.youtube as youtube

# Forzar UTF-8 en Windows para evitar encoding errors con rich
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True)

# Límite global de pipelines concurrentes (API + scheduler)
_PIPELINE_SEMAPHORE = threading.Semaphore(2)

SOURCES = [
    ("Reddit", reddit.run),
    ("Google Trends", gtrends.run),
    ("Twitter/X", twitter.run),
    ("TweetClaw JSON", tweetclaw.run),
    ("Amazon", amazon.run),
    ("TikTok", tiktok.run),
    ("Hacker News", hackernews.run),
    ("YouTube", youtube.run),
]

# Scrapers que requieren I/O de red pesado (benefician mas de paralelismo)
_PARALLEL_SOURCES = {"Reddit", "Google Trends", "Amazon", "TikTok", "Hacker News", "YouTube"}
# Scrapers que pueden saturar rate limits o dependen de auth frágil (mejor secuencial)
_SERIAL_SOURCES = {"Twitter/X", "TweetClaw JSON"}


def _cache_key(query: TrendQuery) -> str:
    kw_hash = hashlib.sha1("|".join(query.keywords).encode("utf-8")).hexdigest()[:10]
    return (
        f"{query.mode}:{query.category or query.free_topic}:"
        f"{query.geo}:{query.sentiment_engine}:{query.top_n}:{kw_hash}"
    )


def run(query: TrendQuery) -> tuple[dict, str]:
    """
    Pipeline completo: scraping -> dedup -> sentimiento -> scoring -> output.
    Ejecuta scrapers en paralelo cuando es seguro (ThreadPoolExecutor).
    Retorna (json_payload, markdown_report).
    """
    acquired = _PIPELINE_SEMAPHORE.acquire(blocking=False)
    if not acquired:
        raise RuntimeError("Pipeline saturado: demasiados análisis en curso. Reintenta en unos segundos.")
    try:
        return _run_unlocked(query)
    finally:
        _PIPELINE_SEMAPHORE.release()


def _run_unlocked(query: TrendQuery) -> tuple[dict, str]:
    console.print(f"\n[bold cyan]TrendScope - {query.display_name}[/bold cyan]")
    console.print(f"[dim]Geo: {query.geo} | Sentimiento: {query.sentiment_engine}[/dim]\n")

    # Cache: si ya se consulto lo mismo recientemente, usar resultado cacheado
    cache_key = _cache_key(query)
    cached = cache_get(cache_key)
    if cached:
        console.print("[dim green](resultado desde cache)[/dim green]")
        # Cache almacena lista [payload, report] tras json.loads
        if isinstance(cached, (list, tuple)) and len(cached) == 2:
            return cached[0], cached[1]
        return cached

    all_items: list[dict] = []
    source_errors: dict[str, str] = {}

    # NO mutar sinks globales de loguru: el logging a fichero debe sobrevivir
    # a cada run del pipeline. Solo reportamos resultados al final.

    # Dividir fuentes en paralelas y seriales
    parallel_sources = [(n, f) for n, f in SOURCES if n in _PARALLEL_SOURCES]
    serial_sources = [(n, f) for n, f in SOURCES if n in _SERIAL_SOURCES]

    # --- Fuentes paralelas ---
    if parallel_sources:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(fn, query): name
                for name, fn in parallel_sources
            }
            results_parallel: list[tuple[str, list[dict], str | None]] = []
            for future in as_completed(futures):
                name = futures[future]
                try:
                    items = future.result()
                    results_parallel.append((name, items, None))
                except Exception as e:
                    logger.error(f"Pipeline - {name}: {e}")
                    source_errors[name] = str(e)
                    results_parallel.append((name, [], str(e)))

            # Imprimir resultados DESPUES de que todos terminen (sin interleaving)
            for name, items, err in results_parallel:
                if items:
                    console.print(f"  [cyan]>[/cyan] {name}... [green]OK ({len(items)} items)[/green]")
                else:
                    console.print(f"  [cyan]>[/cyan] {name}... [red]FAIL[/red]")
                    if err:
                        source_errors.setdefault(name, err)
                all_items.extend(items)

    # --- Fuentes seriales ---
    for name, scraper_fn in serial_sources:
        console.print(f"  [cyan]>[/cyan] {name}... ", end="")
        try:
            items = scraper_fn(query)
            all_items.extend(items)
            console.print(f"[green]OK ({len(items)} items)[/green]")
        except Exception as e:
            logger.error(f"Pipeline - {name}: {e}")
            source_errors[name] = str(e)
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

    # Insights — el "cerebro" de TrendScope
    console.print(f"[yellow]Generando analisis...[/yellow]")
    labels = [i.get("sentiment_label", "neutral") for i in scored]
    sentiment_summary = {
        "positive": labels.count("positive"),
        "negative": labels.count("negative"),
        "neutral": labels.count("neutral"),
        "engine": query.sentiment_engine,
        "overall": max(set(labels), key=labels.count) if labels else "neutral",
    }
    insights = generate_insights(scored, query, sentiment_summary)

    # Export
    json_payload = export_json(scored, query, insights)
    report = export_report(json_payload, query, insights)

    if source_errors:
        json_payload.setdefault("meta", {})["source_errors"] = source_errors

    # Guardar en cache para futuras consultas (lista, no tuple, por JSON)
    cache_set(cache_key, [json_payload, report])

    return json_payload, report
