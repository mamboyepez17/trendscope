# core/pipeline.py
import sys
import io

from loguru import logger
from rich.console import Console

from core.query import TrendQuery
from analyzer.scorer import enrich_and_score
from analyzer.deduplicator import deduplicate
from sentiment import analyze_items
from output.json_exporter import export as export_json
from output.report_exporter import export as export_report
import scrapers.reddit as reddit
import scrapers.google_trends as gtrends
import scrapers.twitter as twitter
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
    ("Amazon", amazon.run),
    ("TikTok", tiktok.run),
]


def run(query: TrendQuery) -> tuple[dict, str]:
    """
    Pipeline completo: scraping -> dedup -> sentimiento -> scoring -> output.
    Retorna (json_payload, markdown_report).
    """
    console.print(f"\n[bold cyan]TrendScope - {query.display_name}[/bold cyan]")
    console.print(f"[dim]Geo: {query.geo} | Sentimiento: {query.sentiment_engine}[/dim]\n")

    all_items: list[dict] = []

    for name, scraper_fn in SOURCES:
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

    return json_payload, report
