# main.py
# TrendScope — CLI interactivo
# Uso: python main.py
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

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
    """Muestra resultados en terminal con tablas rich."""
    top = payload["top_trends"]
    ss = payload["meta"]["sentiment_summary"]
    date = payload["meta"]["date"]
    sources = payload["meta"]["sources_used"]

    console.print(f"\n[bold green]Analisis completado[/bold green]")
    console.print(f"  JSON:    data/trends_{date}_{query.topic_slug}.json")
    console.print(f"  Reporte: data/report_{date}_{query.topic_slug}.md")
    console.print(
        f"\n  Sentimiento: [bold]{ss['overall'].upper()}[/bold] "
        f"([green]+{ss['positive']}[/green] "
        f"[red]-{ss['negative']}[/red] "
        f"[dim]~{ss['neutral']}[/dim])\n"
    )

    # Fuente info
    console.print(f"[dim]Fuentes activas: {', '.join(sources)}[/dim]\n")

    # Tabla de top tendencias
    table = Table(
        title="Top Tendencias",
        show_header=True,
        header_style="bold yellow",
        border_style="yellow",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Heat", width=6)
    table.add_column("Sent", width=4)
    table.add_column("Titulo", min_width=40, max_width=60)
    table.add_column("Score", justify="right", width=7)
    table.add_column("Fuente", width=18)

    for item in top[:10]:
        s = item["trend_score"]
        if s >= 75:
            heat = "[red]HOT[/red]"
        elif s >= 50:
            heat = "[yellow]MED[/yellow]"
        else:
            heat = "[green]LOW[/green]"

        sent_label = item["sentiment"]["label"]
        if sent_label == "positive":
            s_mark = "[green]+[/green]"
        elif sent_label == "negative":
            s_mark = "[red]-[/red]"
        else:
            s_mark = "[dim]~[/dim]"

        title = item["title"][:60]
        source = item["source"].replace("_", " ").title()

        table.add_row(
            str(item["rank"]),
            heat,
            s_mark,
            title,
            f"{s}/100",
            source,
        )

    console.print(table)

    # Detalles de top 3
    console.print("\n[bold]Detalles Top 3:[/bold]\n")
    for item in top[:3]:
        sigs = item.get("signals", {})
        details = []
        if sigs.get("reddit_score"):
            details.append(f"Upvotes: {sigs['reddit_score']}")
        if sigs.get("comments"):
            details.append(f"Comments: {sigs['comments']}")
        if sigs.get("likes"):
            details.append(f"Likes: {sigs['likes']}")
        if sigs.get("retweets"):
            details.append(f"RTs: {sigs['retweets']}")
        if sigs.get("google_traffic"):
            details.append(f"Traffic: {sigs['google_traffic']}")
        if sigs.get("amazon_rank"):
            details.append(f"Amazon #{sigs['amazon_rank']}")
        if sigs.get("price"):
            details.append(f"Price: {sigs['price']}")

        console.print(f"  [bold]{item['rank']}. {item['title'][:70]}[/bold]")
        if details:
            console.print(f"     [dim]{' | '.join(details)}[/dim]")
        if item.get("url"):
            console.print(f"     [dim blue]{item['url'][:80]}[/dim blue]")
        console.print("")

    # Mostrar insights del análisis
    insights = payload.get("insights")
    if insights:
        console.print(Panel("🧠 Análisis de TrendScope", border_style="magenta"))

        # Resumen ejecutivo
        console.print(f"\n[bold]Resumen ejecutivo:[/bold]")
        console.print(f"  {insights.get('executive_summary', 'N/A')}\n")

        # Insights accionables
        for i in insights.get("actionable_insights", []):
            color = "green" if i["type"] == "opportunity" else "red" if i["type"] == "alert" else "cyan"
            icon = "🎯" if i["type"] == "opportunity" else "⚠️" if i["type"] == "alert" else "📊"
            console.print(f"  [{color}]{icon} [{i['priority'].upper()}][/{color}] {i['title']}")
            console.print(f"  [dim]   {i['description'][:100]}[/dim]\n")

        # Correlaciones
        for c in insights.get("correlations", []):
            icon = "🤝" if c["type"] == "consensus" else "🔀" if c["type"] == "divergence" else "📈"
            console.print(f"  [cyan]{icon}[/cyan] {c['description'][:100]}")
        console.print("")

        # Emergentes
        em = insights.get("emerging_vs_established", {})
        if em.get("emerging"):
            console.print("  [bold yellow]⚡ Emergentes:[/bold yellow]")
            for e in em["emerging"][:3]:
                console.print(f"     {e['title'][:60]} ({e['score']}/100)")
        if em.get("established"):
            console.print("  [bold green]✅ Establecidas:[/bold green]")
            for e in em["established"][:3]:
                console.print(f"     {e['title'][:60]} ({e['score']}/100, {e['sources_count']} fuentes)")
        console.print("")

        # Recomendaciones
        recs = insights.get("recommendations", [])
        if recs:
            console.print("  [bold magenta]🎯 Recomendaciones:[/bold magenta]")
            for r in recs:
                console.print(f"     {r}")
        console.print("")


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

        # Preguntar si quiere abrir el reporte
        console.print("\n[bold]Que quieres hacer?[/bold]")
        console.print("  [cyan]1[/cyan] - Ver reporte Markdown completo")
        console.print("  [cyan]2[/cyan] - Analizar otro tema")
        console.print("  [cyan]3[/cyan] - Salir\n")
        action = Prompt.ask("Opcion", choices=["1", "2", "3"], default="3")

        if action == "1":
            import os
            date = payload["meta"]["date"]
            report_path = os.path.join("data", f"report_{date}_{query.topic_slug}.md")
            console.print(f"\n[green]Reporte en: {report_path}[/green]")
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    console.print(Panel(f.read(), border_style="cyan", title="Reporte"))
            except Exception:
                console.print("[red]No se pudo leer el reporte.[/red]")
        elif action == "2":
            main()  # Recursivo: volver a empezar

    except KeyboardInterrupt:
        console.print("\n[red]Cancelado.[/red]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error inesperado: {e}[/red]")
        console.print("[dim]Revisa los logs para mas detalles.[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
