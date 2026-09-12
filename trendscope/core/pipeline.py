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
import trendscope.scrapers.gdelt as gdelt
import trendscope.scrapers.google_news as google_news
import trendscope.scrapers.bing_news as bing_news
import trendscope.scrapers.wikipedia as wikipedia
import trendscope.scrapers.bluesky as bluesky

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
    ("GDELT", gdelt.run),
    ("Google News", google_news.run),
    ("Bing News", bing_news.run),
    ("Wikipedia", wikipedia.run),
    ("Bluesky", bluesky.run),
]

# Scrapers que requieren I/O de red pesado (benefician mas de paralelismo)
_PARALLEL_SOURCES = {
    "Reddit",
    "Google Trends",
    "Amazon",
    "TikTok",
    "Hacker News",
    "YouTube",
    "GDELT",
    "Google News",
    "Bing News",
    "Wikipedia",
    "Bluesky",
}
# Scrapers que pueden saturar rate limits o dependen de auth frágil (mejor secuencial)
_SERIAL_SOURCES = {"Twitter/X", "TweetClaw JSON"}


# Bump when scraper logic changes so stale cache entries are ignored
_CACHE_VERSION = "v7-stance"


def _cache_key(query: TrendQuery) -> str:
    kw_hash = hashlib.sha1("|".join(query.keywords).encode("utf-8")).hexdigest()[:10]
    return (
        f"{_CACHE_VERSION}:{query.mode}:{query.category or query.free_topic}:"
        f"{query.geo}:{query.sentiment_engine}:{query.top_n}:{kw_hash}"
    )


def run(query: TrendQuery) -> tuple[dict, str]:
    """
    Pipeline completo: scraping -> dedup -> sentimiento -> scoring -> output.
    Ejecuta scrapers en paralelo cuando es seguro (ThreadPoolExecutor).
    Retorna (json_payload, markdown_report).
    """
    import time

    from trendscope.core import metrics as metrics_mod

    acquired = _PIPELINE_SEMAPHORE.acquire(blocking=False)
    if not acquired:
        metrics_mod.incr("pipeline_saturated")
        raise RuntimeError("Pipeline saturado: demasiados análisis en curso. Reintenta en unos segundos.")
    start = time.perf_counter()
    try:
        result = _run_unlocked(query)
        metrics_mod.incr("pipeline_runs")
        metrics_mod.observe("pipeline", time.perf_counter() - start)
        return result
    except Exception:
        metrics_mod.incr("pipeline_errors")
        raise
    finally:
        _PIPELINE_SEMAPHORE.release()


def _filter_topic_relevant(items: list[dict], topic: str) -> list[dict]:
    """Mantiene items que mencionan al menos un token significativo del tema."""
    tokens = [t.lower() for t in topic.split() if len(t) > 3]
    if not tokens:
        tokens = [topic.lower()]
    kept = []
    for item in items:
        text = (
            item.get("title")
            or item.get("keyword")
            or item.get("text")
            or ""
        ).lower()
        if any(tok in text for tok in tokens):
            kept.append(item)
    return kept


def _timed_scrape(name: str, fn, query) -> tuple[list[dict], str | None]:
    """Ejecuta un scraper midiendo latencia y registrando health."""
    import time

    from trendscope.core import source_health

    t0 = time.perf_counter()
    try:
        items = fn(query)
        source_health.record_success(name, time.perf_counter() - t0)
        return items, None
    except Exception as e:
        source_health.record_failure(name, str(e))
        raise


def _run_unlocked(query: TrendQuery) -> tuple[dict, str]:
    import time

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

    from trendscope.core import source_health

    # NO mutar sinks globales de loguru: el logging a fichero debe sobrevivir
    # a cada run del pipeline. Solo reportamos resultados al final.

    # Dividir fuentes en paralelas y seriales
    parallel_sources = [
        (n, f) for n, f in SOURCES if n in _PARALLEL_SOURCES and not source_health.should_skip(n)
    ]
    serial_sources = [
        (n, f) for n, f in SOURCES if n in _SERIAL_SOURCES and not source_health.should_skip(n)
    ]
    skipped = [
        n for n, _ in SOURCES if source_health.should_skip(n)
    ]
    for n in skipped:
        source_errors[n] = "skipped: source health score low"

    # --- Fuentes paralelas ---
    if parallel_sources:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {}
            for name, fn in parallel_sources:
                futures[pool.submit(_timed_scrape, name, fn, query)] = name
            results_parallel: list[tuple[str, list[dict], str | None]] = []
            for future in as_completed(futures):
                name = futures[future]
                try:
                    items, err = future.result()
                    results_parallel.append((name, items, err))
                except Exception as e:
                    logger.error(f"Pipeline - {name}: {e}")
                    source_health.record_failure(name, str(e))
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
            t0 = time.perf_counter()
            items = scraper_fn(query)
            source_health.record_success(name, time.perf_counter() - t0)
            all_items.extend(items)
            console.print(f"[green]OK ({len(items)} items)[/green]")
        except Exception as e:
            logger.error(f"Pipeline - {name}: {e}")
            source_health.record_failure(name, str(e))
            source_errors[name] = str(e)
            console.print(f"[red]FAIL[/red]")

    console.print(f"\n[yellow]Recolectado: {len(all_items)} senales[/yellow]")

    # Tema libre: descartar ruido que no menciona el tema
    if query.mode == "free" and query.free_topic:
        before = len(all_items)
        all_items = _filter_topic_relevant(all_items, query.free_topic)
        dropped = before - len(all_items)
        if dropped:
            console.print(
                f"[yellow]Filtrados {dropped} items sin relación con el tema[/yellow]"
            )

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
    from trendscope.sentiment.stance import summarize_stances

    stance_summary = summarize_stances(scored)
    by_source = _sentiment_by_source(scored)
    insights = generate_insights(scored, query, sentiment_summary)

    # Export
    json_payload = export_json(scored, query, insights)
    report = export_report(json_payload, query, insights)

    if source_errors:
        json_payload.setdefault("meta", {})["source_errors"] = source_errors
    meta = json_payload.setdefault("meta", {})
    meta["source_health"] = source_health.snapshot()
    meta["stance_summary"] = stance_summary
    meta["sentiment_by_source"] = by_source

    # Guardar en cache para futuras consultas (lista, no tuple, por JSON)
    cache_set(cache_key, [json_payload, report])

    return json_payload, report


def _sentiment_by_source(items: list[dict]) -> dict:
    """Agrega sentimiento y stance por fuente."""
    from collections import defaultdict

    buckets: dict[str, dict] = defaultdict(
        lambda: {
            "count": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "support": 0,
            "against": 0,
            "mixed": 0,
            "unknown": 0,
        }
    )
    for item in items:
        src = item.get("source") or "unknown"
        b = buckets[src]
        b["count"] += 1
        lab = item.get("sentiment_label", "neutral")
        if lab in ("positive", "negative", "neutral"):
            b[lab] += 1
        st = item.get("stance", "unknown")
        if st in ("support", "against", "mixed", "unknown"):
            b[st] += 1
    return dict(buckets)
