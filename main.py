# main.py
# TrendScope — CLI interactivo
# Uso: python main.py
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from config import CATEGORIES, SENTIMENT_ENGINE_DEFAULT
from core.query import TrendQuery
from core.pipeline import run

console = Console()

BANNER = """
 _____ ____  _____ _   _ ____  ____   ____ ___  ____  _____
|_   _|  _ \\| ____| \\ | |  _ \\/ ___| / ___/ _ \\|  _ \\| ____|
  | | | |_) |  _| |  \\| | | | \\___ \\| |  | | | | |_) |  _|
  | | |  _ <| |___| |\\  | |_| |___) | |__| |_| |  __/| |___
  |_| |_| \\_\\_____|_| \\_|____/|____/ \\____\\___/|_|   |_____|

  Inteligencia de tendencias universal
  github.com/mamboyepez17/trendscope
"""


def choose_topic() -> tuple[str, str | None, str | None]:
    """Permite al usuario elegir entre categoria predefinida o tema libre."""
    console.print("\n[bold]Como quieres analizar tendencias?[/bold]\n")
    console.print("  [cyan]1[/cyan] - Categoria predefinida")
    console.print("  [cyan]2[/cyan] - Tema libre\n")
    mode = Prompt.ask("Elige", choices=["1", "2"], default="1")

    if mode == "1":
        table = Table(show_header=False, box=None, padding=(0, 2))
        cats = list(CATEGORIES.keys())
        for i, cat in enumerate(cats, 1):
            table.add_row(f"[cyan]{i:2}[/cyan]", cat)
        console.print(table)
        console.print("")
        cat = Prompt.ask(
            "Categoria",
            choices=cats,
            default="tecnologia",
        )
        return "category", cat, None
    else:
        topic = Prompt.ask("\nSobre que tema?")
        return "free", None, topic.strip()


def choose_sentiment() -> str:
    """Permite al usuario elegir el motor de sentimiento."""
    console.print("\n[bold]Motor de sentimiento:[/bold]")
    console.print("  [cyan]1[/cyan] - Local (pysentimiento, gratis)")
    console.print("  [cyan]2[/cyan] - Claude API (premium, mas preciso)")
    console.print(f"  [dim]Enter = default del .env ({SENTIMENT_ENGINE_DEFAULT})[/dim]\n")
    choice = Prompt.ask("Motor", choices=["1", "2", ""], default="")
    return {"1": "local", "2": "claude"}.get(choice, SENTIMENT_ENGINE_DEFAULT)


def show_results(payload: dict, query: TrendQuery) -> None:
    """Muestra resultados en terminal."""
    top = payload["top_trends"]
    ss = payload["meta"]["sentiment_summary"]
    date = payload["meta"]["date"]

    console.print(f"\n[bold green]Analisis completado[/bold green]")
    console.print(f"  JSON:    data/trends_{date}_{query.topic_slug}.json")
    console.print(f"  Reporte: data/report_{date}_{query.topic_slug}.md")
    console.print(
        f"\n  Sentimiento: [bold]{ss['overall'].upper()}[/bold] "
        f"(+{ss['positive']} -{ss['negative']} ~{ss['neutral']})\n"
    )

    console.print(Panel("[bold]Top 5 Tendencias[/bold]", border_style="yellow"))
    for item in top[:5]:
        s = item["trend_score"]
        if s >= 75:
            heat = "[red][HOT][/red]"
        elif s >= 50:
            heat = "[yellow][MED][/yellow]"
        else:
            heat = "[green][LOW][/green]"

        sent_label = item["sentiment"]["label"]
        if sent_label == "positive":
            s_mark = "[green]+[/green]"
        elif sent_label == "negative":
            s_mark = "[red]-[/red]"
        else:
            s_mark = "[dim]~[/dim]"

        console.print(f"  {item['rank']}. {heat} {s_mark} [bold]{item['title'][:70]}[/bold]")
        console.print(f"     Score: {s}/100 | {item['source'].replace('_',' ').title()}\n")


def main() -> None:
    """Entry point del CLI."""
    try:
        console.print(Panel(BANNER, border_style="cyan"))
        mode, category, free_topic = choose_topic()
        engine = choose_sentiment()

        query = TrendQuery(
            mode=mode,
            category=category,
            free_topic=free_topic,
            sentiment_engine=engine,
        )

        payload, _ = run(query)
        show_results(payload, query)

    except KeyboardInterrupt:
        console.print("\n[red]Cancelado.[/red]")
        sys.exit(0)


if __name__ == "__main__":
    main()
