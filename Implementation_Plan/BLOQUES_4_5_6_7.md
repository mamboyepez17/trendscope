# 📦 TRENDSCOPE — BLOQUE 4 DE 7
## Output: JSON Exporter + Markdown Report
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 4 de 7. Construyes los dos exportadores de resultados:
JSON estructurado para agentes y reporte Markdown legible para humanos.

**Prerequisito:** Bloque 3 aprobado.

---

## PASO 4.1 — `output/json_exporter.py`

```python
# output/json_exporter.py
import json
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
from config import DATA_DIR
from core.query import TrendQuery


def export(items: list[dict], query: TrendQuery) -> dict:
    top = items[:query.top_n]
    now = datetime.now(timezone.utc)

    # Resumen de sentimiento
    labels = [i.get("sentiment_label", "neutral") for i in top]
    sentiment_summary = {
        "positive": labels.count("positive"),
        "negative": labels.count("negative"),
        "neutral":  labels.count("neutral"),
        "engine":   query.sentiment_engine,
        "overall":  max(set(labels), key=labels.count) if labels else "neutral",
    }

    payload = {
        "meta": {
            "tool":           "TrendScope",
            "version":        "1.0.0",
            "generated_at":   now.isoformat(),
            "date":           now.strftime("%Y-%m-%d"),
            "query": {
                "mode":          query.mode,
                "topic":         query.free_topic or query.category,
                "geo":           query.geo,
                "keywords_used": query.keywords,
            },
            "total_analyzed":    len(items),
            "top_n_exported":    len(top),
            "sources_used":      list(set(i["source"] for i in items)),
            "sentiment_summary": sentiment_summary,
        },
        "top_trends": [
            {
                "rank":     idx + 1,
                "title":    (i.get("title") or i.get("keyword") or i.get("text", ""))[:150],
                "source":   i["source"],
                "trend_score": i["trend_score"],
                "url":      i.get("url") or i.get("permalink", ""),
                "category": i.get("category") or i.get("subreddit") or "general",
                "sentiment": {
                    "label":    i.get("sentiment_label", "neutral"),
                    "score":    i.get("sentiment_score", 0.5),
                    "emotions": i.get("emotions", {}),
                },
                "signals": {
                    "reddit_score":   i.get("score"),
                    "upvote_ratio":   i.get("upvote_ratio"),
                    "comments":       i.get("comments"),
                    "likes":          i.get("likes"),
                    "retweets":       i.get("retweets"),
                    "google_traffic": i.get("approx_traffic"),
                    "amazon_rank":    i.get("rank"),
                    "price":          i.get("price"),
                },
            }
            for idx, i in enumerate(top)
        ],
        "agent_prompt": (
            f"Analiza estas {len(top)} tendencias sobre "
            f"'{query.free_topic or query.category}'. "
            f"El sentimiento general es '{sentiment_summary['overall']}' "
            f"({sentiment_summary['positive']} positivos, "
            f"{sentiment_summary['negative']} negativos). "
            "Identifica los 3 insights más accionables para tomar decisiones. "
            "Considera el contexto colombiano y el momento actual (2026). "
            "Sé específico, concreto y práctico."
        ),
    }

    Path(DATA_DIR).mkdir(exist_ok=True)
    filepath = Path(DATA_DIR) / f"trends_{now.strftime('%Y-%m-%d')}_{query.topic_slug}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.success(f"JSON exportado: {filepath}")
    return payload
```

---

## PASO 4.2 — `output/report_exporter.py`

```python
# output/report_exporter.py
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger
from config import DATA_DIR
from core.query import TrendQuery
from sentiment.base import SENTIMENT_EMOJI


def export(payload: dict, query: TrendQuery) -> str:
    now  = datetime.now(timezone.utc)
    meta = payload["meta"]
    top  = payload["top_trends"]
    ss   = meta["sentiment_summary"]

    lines = [
        "# 📊 TrendScope Report",
        f"**Tema:** {query.display_name}  ",
        f"**Fecha:** {now.strftime('%d/%m/%Y %H:%M')} UTC  ",
        f"**Fuentes:** {', '.join(meta['sources_used'])}  ",
        f"**Total analizado:** {meta['total_analyzed']} señales  ",
        f"**Motor sentimiento:** {ss['engine']}",
        "",
        "## 🧠 Sentimiento General",
        "",
        "| 😊 Positivo | 😟 Negativo | 😐 Neutral | Predominante |",
        "|---|---|---|---|",
        f"| {ss['positive']} | {ss['negative']} | {ss['neutral']} | **{ss['overall'].upper()}** |",
        "",
        "---",
        "",
        "## 🏆 Top Tendencias",
        "",
    ]

    for item in top:
        score  = item["trend_score"]
        heat   = "🔴" if score >= 75 else ("🟡" if score >= 50 else "🟢")
        sent   = item["sentiment"]
        s_emoji = SENTIMENT_EMOJI.get(sent["label"], "❓")
        title  = item["title"]
        url    = item["url"]
        sigs   = item["signals"]

        lines.append(f"### {item['rank']}. {heat} {title}")
        lines.append(
            f"**Score:** {score}/100 | "
            f"**Fuente:** {item['source'].replace('_',' ').title()} | "
            f"**Sentimiento:** {s_emoji} {sent['label']} ({sent['score']:.0%})"
        )

        # Emociones top 2
        if sent.get("emotions"):
            top_emo = sorted(sent["emotions"].items(), key=lambda x: x[1], reverse=True)[:2]
            lines.append(f"**Emociones:** {', '.join(f'{e} {v:.0%}' for e, v in top_emo)}")

        # Señales disponibles
        sig_parts = []
        if sigs.get("reddit_score"):   sig_parts.append(f"👍 {sigs['reddit_score']}")
        if sigs.get("comments"):       sig_parts.append(f"💬 {sigs['comments']}")
        if sigs.get("likes"):          sig_parts.append(f"❤️ {sigs['likes']}")
        if sigs.get("retweets"):       sig_parts.append(f"🔁 {sigs['retweets']}")
        if sigs.get("google_traffic"): sig_parts.append(f"🔍 {sigs['google_traffic']}")
        if sigs.get("amazon_rank"):    sig_parts.append(f"🛒 #{sigs['amazon_rank']} Amazon")
        if sig_parts:
            lines.append("  ".join(sig_parts))
        if url:
            lines.append(f"🔗 {url[:80]}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 💡 Prompt para análisis IA",
        "",
        f"> {payload['agent_prompt']}",
        "",
        f"*TrendScope v1.0 — mamboyepez17 — {now.strftime('%Y-%m-%d')}*",
    ]

    report = "\n".join(lines)
    Path(DATA_DIR).mkdir(exist_ok=True)
    filepath = Path(DATA_DIR) / f"report_{now.strftime('%Y-%m-%d')}_{query.topic_slug}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(report)

    logger.success(f"Reporte exportado: {filepath}")
    return report
```

---

## PASO 4.3 — Validación del Bloque 4

```bash
cd trendscope
python -c "
from core.query import TrendQuery
from sentiment import analyze_items
from analyzer.scorer import enrich_and_score
from analyzer.deduplicator import deduplicate
from output.json_exporter import export as export_json
from output.report_exporter import export as export_report
from datetime import datetime, timezone

query = TrendQuery(mode='category', category='tecnologia', sentiment_engine='local')

items = [
    {'source':'reddit','title':'IA revoluciona salud Colombia','score':3000,'upvote_ratio':0.95,'comments':200,'created_utc':0},
    {'source':'google_trends_rss','keyword':'inteligencia artificial','approx_traffic':'200K+'},
    {'source':'amazon_bestsellers','title':'Kindle Paperwhite','rank':'#2','price':'\$139.99'},
    {'source':'tiktok_trending','keyword':'gadgetsIA'},
    {'source':'twitter','text':'El nuevo iPhone cambió mi vida','likes':500,'retweets':100,'user_followers':10000},
]

items = analyze_items(items, query)
scored = enrich_and_score(items, query)
payload = export_json(scored, query)
report  = export_report(payload, query)

import os
from pathlib import Path
date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
json_file = Path(f'data/trends_{date}_{query.topic_slug}.json')
md_file   = Path(f'data/report_{date}_{query.topic_slug}.md')

assert json_file.exists(), 'JSON no generado'
assert md_file.exists(),   'Markdown no generado'
assert len(payload['top_trends']) > 0, 'Sin trends en payload'
assert 'agent_prompt' in payload, 'Sin agent_prompt'

print(f'✅ JSON generado: {json_file}')
print(f'✅ Markdown generado: {md_file}')
print(f'   Top 1: [{payload[\"top_trends\"][0][\"trend_score\"]}] {payload[\"top_trends\"][0][\"title\"]}')
print(f'   Sentimiento general: {payload[\"meta\"][\"sentiment_summary\"][\"overall\"]}')
"
```

---

## PASO 4.4 — Actualizar CHANGELOG

```markdown
## [0.5.0] — FECHA — MODELO_USADO

### Añadido
- output/json_exporter.py: JSON estructurado para agentes con agent_prompt
- output/report_exporter.py: Markdown legible con tabla de sentimiento

### Pendiente
- Bloque 5: Pipeline + CLI
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 4

- [ ] JSON generado correctamente en `data/`
- [ ] Markdown generado correctamente en `data/`
- [ ] JSON contiene `meta`, `top_trends` y `agent_prompt`
- [ ] Reporte muestra tabla de sentimiento y señales por item
- [ ] CHANGELOG actualizado

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 4 COMPLETADO

Exportadores validados:
- JSON exporter  ✅ (data/trends_FECHA_TEMA.json)
- MD report      ✅ (data/report_FECHA_TEMA.md)

¿Aprobado para continuar al Bloque 5 — Pipeline + CLI?
```

---

*TrendScope — Bloque 4 de 7 | Siguiente: BLOQUE_5_PIPELINE_CLI.md*

---
---
---

# 🔄 TRENDSCOPE — BLOQUE 5 DE 7
## Pipeline + CLI interactivo
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 5 de 7. Conectas todos los bloques anteriores en el
pipeline central y construyes el CLI interactivo con rich.

**Prerequisito:** Bloque 4 aprobado.

---

## PASO 5.1 — `core/pipeline.py`

```python
# core/pipeline.py
from loguru import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
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

console = Console()

SOURCES = [
    ("📡 Reddit",        reddit.run),
    ("📡 Google Trends", gtrends.run),
    ("📡 Twitter/X",     twitter.run),
    ("📡 Amazon",        amazon.run),
    ("📡 TikTok",        tiktok.run),
]


def run(query: TrendQuery) -> tuple[dict, str]:
    """
    Pipeline completo: scraping → dedup → sentimiento → scoring → output.
    Retorna (json_payload, markdown_report).
    """
    console.print(f"\n[bold cyan]🔍 TrendScope — {query.display_name}[/bold cyan]")
    console.print(f"[dim]Geo: {query.geo} | Sentimiento: {query.sentiment_engine}[/dim]\n")

    all_items: list[dict] = []

    with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as progress:
        for name, scraper_fn in SOURCES:
            task = progress.add_task(f"{name}...", total=None)
            try:
                items = scraper_fn(query)
                all_items.extend(items)
                progress.update(task, description=f"{name} ✅ ({len(items)} items)")
            except Exception as e:
                progress.update(task, description=f"{name} ❌ ({e})")
            progress.stop_task(task)

    console.print(f"\n[yellow]📊 Recolectado: {len(all_items)} señales[/yellow]")

    all_items = deduplicate(all_items)
    console.print(f"[yellow]🧹 Únicos tras deduplicar: {len(all_items)}[/yellow]")

    console.print(f"[yellow]🧠 Analizando sentimiento ({query.sentiment_engine})...[/yellow]")
    all_items = analyze_items(all_items, query)

    scored       = enrich_and_score(all_items, query)
    json_payload = export_json(scored, query)
    report       = export_report(json_payload, query)

    return json_payload, report
```

---

## PASO 5.2 — `main.py`

```python
# main.py
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
╔══════════════════════════════════════════╗
║        📊  T R E N D S C O P E          ║
║  Inteligencia de tendencias universal    ║
║         github: mamboyepez17            ║
╚══════════════════════════════════════════╝
"""


def choose_topic() -> tuple[str, str | None, str | None]:
    console.print("\n[bold]¿Cómo quieres analizar tendencias?[/bold]\n")
    console.print("  [cyan]1[/cyan] — Categoría predefinida")
    console.print("  [cyan]2[/cyan] — Tema libre\n")
    mode = Prompt.ask("Elige", choices=["1", "2"], default="1")

    if mode == "1":
        table = Table(show_header=False, box=None, padding=(0, 2))
        for i, cat in enumerate(CATEGORIES.keys(), 1):
            table.add_row(f"[cyan]{i}[/cyan]", cat)
        console.print(table)
        cat = Prompt.ask(
            "\nCategoría",
            choices=list(CATEGORIES.keys()),
            default="tecnologia",
        )
        return "category", cat, None
    else:
        topic = Prompt.ask("\n¿Sobre qué tema?")
        return "free", None, topic.strip()


def choose_sentiment() -> str:
    console.print("\n[bold]Motor de sentimiento:[/bold]")
    console.print("  [cyan]1[/cyan] — Local (pysentimiento, gratis)")
    console.print("  [cyan]2[/cyan] — Claude API (premium, más preciso)")
    console.print(f"  [dim]Enter = default del .env ({SENTIMENT_ENGINE_DEFAULT})[/dim]\n")
    choice = Prompt.ask("Motor", choices=["1", "2", ""], default="")
    return {"1": "local", "2": "claude"}.get(choice, SENTIMENT_ENGINE_DEFAULT)


def show_results(payload: dict, query: TrendQuery) -> None:
    top = payload["top_trends"]
    ss  = payload["meta"]["sentiment_summary"]
    date = payload["meta"]["date"]

    console.print(f"\n[bold green]✅ Análisis completado[/bold green]")
    console.print(f"📁 JSON:    data/trends_{date}_{query.topic_slug}.json")
    console.print(f"📄 Reporte: data/report_{date}_{query.topic_slug}.md")
    console.print(
        f"\n🧠 Sentimiento: [bold]{ss['overall'].upper()}[/bold] "
        f"(😊{ss['positive']} 😟{ss['negative']} 😐{ss['neutral']})\n"
    )

    console.print(Panel("[bold]🏆 Top 5[/bold]", border_style="yellow"))
    for item in top[:5]:
        s     = item["trend_score"]
        heat  = "🔴" if s >= 75 else ("🟡" if s >= 50 else "🟢")
        s_emo = {"positive": "😊", "negative": "😟", "neutral": "😐"}.get(
            item["sentiment"]["label"], "❓"
        )
        console.print(f"  {item['rank']}. {heat}{s_emo} [bold]{item['title'][:75]}[/bold]")
        console.print(f"     Score: {s}/100 | {item['source']}\n")


def main() -> None:
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
```

---

## PASO 5.3 — Validación del Bloque 5

```bash
cd trendscope

# Test pipeline directo (sin CLI)
python -c "
from core.query import TrendQuery
from core.pipeline import run

query = TrendQuery(mode='category', category='tecnologia', sentiment_engine='local')
payload, report = run(query)

assert payload is not None
assert len(payload['top_trends']) > 0
assert report is not None and len(report) > 100

print('✅ Pipeline end-to-end OK')
print(f'   Fuentes usadas: {payload[\"meta\"][\"sources_used\"]}')
print(f'   Total analizado: {payload[\"meta\"][\"total_analyzed\"]}')
print(f'   Top 1: {payload[\"top_trends\"][0][\"title\"][:60]}')
"

# Test CLI completo
python main.py
# Seleccionar: categoría 'tecnologia' + sentimiento 'local'
# Verificar que genera archivos en data/
```

---

## PASO 5.4 — Actualizar CHANGELOG

```markdown
## [0.6.0] — FECHA — MODELO_USADO

### Añadido
- core/pipeline.py: orquesta scraping → dedup → sentimiento → scoring → output
- main.py: CLI interactivo con rich (categoría + libre, motor sentimiento)

### Pendiente
- Bloque 6: Servidores (API REST + MCP)
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 5

- [ ] Pipeline corre sin errores end-to-end
- [ ] `python main.py` muestra banner, permite elegir tema y motor
- [ ] Se generan archivos JSON y Markdown en `data/`
- [ ] Top 5 se muestra en terminal con scores y sentimiento
- [ ] CHANGELOG actualizado

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 5 COMPLETADO

Pipeline y CLI validados:
- core/pipeline.py ✅ (end-to-end sin errores)
- main.py          ✅ (CLI interactivo funcionando)
- Archivos data/   ✅ (JSON + Markdown generados)

¿Aprobado para continuar al Bloque 6 — Servidores?
```

---

*TrendScope — Bloque 5 de 7 | Siguiente: BLOQUE_6_SERVIDORES.md*

---
---
---

# 🌐 TRENDSCOPE — BLOQUE 6 DE 7
## Servidores: API REST + MCP
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 6 de 7. Construyes los dos servidores:
API REST con FastAPI (para Hermes, Mambo, agentes HTTP) y
servidor MCP (para OpenClaw).

**Prerequisito:** Bloque 5 aprobado.

---

## PASO 6.1 — `server_api.py`

```python
# server_api.py
# API REST — TrendScope accesible por cualquier agente HTTP
# Uso: python server_api.py
# Docs: http://localhost:8000/docs
import asyncio
from pathlib import Path
from fastapi import FastAPI, Query as QParam, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn
from config import API_HOST, API_PORT, CATEGORIES, DATA_DIR
from core.query import TrendQuery
from core.pipeline import run as run_pipeline

app = FastAPI(
    title="TrendScope API",
    description="Inteligencia de tendencias universal — mamboyepez17",
    version="1.0.0",
)


@app.get("/health")
def health():
    """Estado del servicio."""
    return {"status": "ok", "service": "TrendScope", "version": "1.0.0"}


@app.get("/categories")
def get_categories():
    """Lista de categorías predefinidas disponibles."""
    return {
        "categories": list(CATEGORIES.keys()),
        "description": "Pasa una de estas como ?category=nombre",
    }


@app.get("/trends")
def get_trends(
    topic:            str | None = QParam(None, description="Tema libre"),
    category:         str | None = QParam(None, description="Categoría predefinida"),
    geo:              str        = QParam("CO",    description="Código ISO país"),
    sentiment_engine: str        = QParam("local", description="local | claude"),
    top_n:            int        = QParam(25,      description="N° resultados"),
):
    """
    Analiza tendencias y retorna JSON estructurado.
    Usar ?topic=TEMA o ?category=CATEGORIA.
    """
    if not topic and not category:
        raise HTTPException(
            status_code=400,
            detail="Debes pasar 'topic' o 'category'. Ejemplo: ?topic=crypto+Colombia",
        )

    query = TrendQuery(
        mode="category" if category else "free",
        category=category,
        free_topic=topic,
        geo=geo,
        sentiment_engine=sentiment_engine,
        top_n=top_n,
    )

    # Pipeline sincrónico en thread pool para no bloquear FastAPI
    loop = asyncio.new_event_loop()
    try:
        payload, _ = loop.run_until_complete(
            asyncio.get_event_loop().run_in_executor(None, run_pipeline, query)
        )
    finally:
        loop.close()

    return payload


@app.get("/report", response_class=PlainTextResponse)
def get_report(
    topic:    str | None = QParam(None, description="Tema del reporte"),
    category: str | None = QParam(None, description="Categoría del reporte"),
):
    """Retorna el último reporte Markdown generado para un tema."""
    slug = (topic or category or "").replace(" ", "_")[:30]
    reports = sorted(Path(DATA_DIR).glob(f"report_*{slug}*.md"), reverse=True)
    if not reports:
        raise HTTPException(
            status_code=404,
            detail=f"No hay reportes para '{slug}'. Genera uno primero con /trends",
        )
    return reports[0].read_text(encoding="utf-8")


if __name__ == "__main__":
    uvicorn.run("server_api:app", host=API_HOST, port=API_PORT, reload=False)
```

---

## PASO 6.2 — `server_mcp.py`

```python
# server_mcp.py
# Servidor MCP — TrendScope como herramienta para OpenClaw y agentes MCP
# Uso: python server_mcp.py
import json
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from config import CATEGORIES
from core.query import TrendQuery
from core.pipeline import run as run_pipeline

app = Server("trendscope")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_trends",
            description=(
                "Analiza tendencias sobre cualquier tema desde múltiples fuentes "
                "gratuitas (Reddit, Google Trends, Twitter/X, Amazon, TikTok) "
                "con análisis de sentimiento incluido. "
                "Retorna JSON con top tendencias, scores y resumen de sentimiento."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema libre a analizar. Ej: 'crypto Colombia', 'salud mental 2026'",
                    },
                    "category": {
                        "type": "string",
                        "description": "Categoría predefinida: " + ", ".join(CATEGORIES.keys()),
                    },
                    "geo": {
                        "type": "string",
                        "description": "Código país ISO (default: CO)",
                        "default": "CO",
                    },
                    "sentiment_engine": {
                        "type": "string",
                        "enum": ["local", "claude"],
                        "description": "Motor de sentimiento (default: local)",
                        "default": "local",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "N° de tendencias a retornar (default: 25)",
                        "default": 25,
                    },
                },
            },
        ),
        Tool(
            name="get_categories",
            description="Lista las categorías predefinidas disponibles en TrendScope.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_latest_report",
            description="Obtiene el último reporte Markdown generado para un tema.",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Tema del reporte a buscar",
                    }
                },
                "required": ["topic"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "analyze_trends":
        topic    = arguments.get("topic")
        category = arguments.get("category")

        query = TrendQuery(
            mode="category" if category else "free",
            category=category,
            free_topic=topic,
            geo=arguments.get("geo", "CO"),
            sentiment_engine=arguments.get("sentiment_engine", "local"),
            top_n=arguments.get("top_n", 25),
        )

        loop = asyncio.get_event_loop()
        payload, _ = await loop.run_in_executor(None, run_pipeline, query)

        return [TextContent(
            type="text",
            text=json.dumps(payload, ensure_ascii=False, indent=2),
        )]

    elif name == "get_categories":
        return [TextContent(
            type="text",
            text=json.dumps(
                {"categories": list(CATEGORIES.keys())},
                ensure_ascii=False,
                indent=2,
            ),
        )]

    elif name == "get_latest_report":
        from pathlib import Path
        from config import DATA_DIR
        slug = arguments.get("topic", "").replace(" ", "_")[:30]
        reports = sorted(Path(DATA_DIR).glob(f"report_*{slug}*.md"), reverse=True)
        if reports:
            return [TextContent(type="text", text=reports[0].read_text(encoding="utf-8"))]
        return [TextContent(type="text", text=f"No hay reportes para '{slug}'")]

    return [TextContent(type="text", text="Herramienta no encontrada")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

---

## PASO 6.3 — Validación del Bloque 6

```bash
cd trendscope

# Test API REST
python server_api.py &
API_PID=$!
sleep 3

curl -s http://localhost:8000/health | python -m json.tool
curl -s http://localhost:8000/categories | python -m json.tool
curl -s "http://localhost:8000/trends?topic=tecnologia+Colombia&top_n=3&sentiment_engine=local" \
  | python -m json.tool | head -40

kill $API_PID
echo "✅ API REST validada"

# Test MCP (verificar que arranca sin errores)
timeout 5 python server_mcp.py && echo "✅ MCP arrancó OK" || echo "✅ MCP arrancó (timeout esperado en stdio)"
```

---

## PASO 6.4 — Actualizar CHANGELOG

```markdown
## [0.7.0] — FECHA — MODELO_USADO

### Añadido
- server_api.py: FastAPI con /health, /categories, /trends, /report
- server_mcp.py: Servidor MCP con 3 tools (analyze_trends, get_categories, get_latest_report)

### Pendiente
- Bloque 7: Publicación en GitHub
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 6

- [ ] `GET /health` retorna `{"status": "ok"}`
- [ ] `GET /categories` retorna lista de categorías
- [ ] `GET /trends?topic=X` retorna JSON con top_trends
- [ ] `server_mcp.py` arranca sin errores de importación
- [ ] CHANGELOG actualizado

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 6 COMPLETADO

Servidores validados:
- API REST /health      ✅
- API REST /categories  ✅
- API REST /trends      ✅
- MCP server            ✅ (3 tools disponibles)

¿Aprobado para continuar al Bloque 7 — Publicación en GitHub?
```

---

*TrendScope — Bloque 6 de 7 | Siguiente: BLOQUE_7_GITHUB.md*

---
---
---

# 🚀 TRENDSCOPE — BLOQUE 7 DE 7
## Publicación en GitHub
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 7 de 7 — el último. Preparas el repo para publicación:
README público, verificación del .gitignore y push a GitHub.

**Prerequisito:** Bloque 6 aprobado.

**CRÍTICO:** Verificar que `.env`, `data/` y `.context/` están en
`.gitignore` antes del commit. Estos NO deben ir al repo público.

---

## PASO 7.1 — Crear `README.md` público

```markdown
# 📊 TrendScope

> Inteligencia de tendencias universal — analiza cualquier tema desde múltiples fuentes gratuitas con análisis de sentimiento incluido.

## ¿Qué es?

TrendScope agrega señales de tendencias desde Reddit, Google Trends, Twitter/X,
Amazon y TikTok. Puntúa cada señal 0-100 y analiza el sentimiento en español
latinoamericano. Genera JSON para agentes de IA y reportes Markdown para humanos.

## Instalación

```bash
git clone https://github.com/mamboyepez17/trendscope
cd trendscope
pip install -r requirements.txt
pip install git+https://github.com/mamboyepez17/xactions-py.git
cp .env.example .env  # completar con tus credenciales
```

## Uso

### CLI (para humanos)
```bash
python main.py
```

### API REST (para Hermes, Mambo, agentes HTTP)
```bash
python server_api.py
# GET http://localhost:8000/trends?topic=crypto+Colombia
# GET http://localhost:8000/trends?category=tecnologia&sentiment_engine=claude
# GET http://localhost:8000/report?topic=crypto
# Docs: http://localhost:8000/docs
```

### Servidor MCP (para OpenClaw)
```bash
python server_mcp.py
```

## Fuentes de datos
| Fuente | Método | Costo |
|---|---|---|
| Reddit | PRAW + JSON público fallback | Gratis |
| Google Trends | RSS primario + pytrends fallback | Gratis |
| Twitter/X | xactions-py | Gratis |
| Amazon Best Sellers | Scrapling StealthyFetcher | Gratis |
| TikTok Creative Center | Scrapling DynamicFetcher | Gratis |

## Análisis de sentimiento
| Motor | Tecnología | Costo |
|---|---|---|
| `local` | pysentimiento (español latinoamericano) | Gratis |
| `claude` | Claude Haiku API | Bajo costo |

Configurable en `.env` o sobreescribible en cada ejecución desde el CLI.

## Output

Cada análisis genera dos archivos en `data/`:
- `trends_FECHA_TEMA.json` — para agentes de IA
- `report_FECHA_TEMA.md` — reporte legible para humanos

## Relacionados
- [xactions-py](https://github.com/mamboyepez17/xactions-py) — Twitter/X toolkit

## Licencia
MIT
```

---

## PASO 7.2 — Crear `LICENSE`

```
MIT License

Copyright (c) 2026 mamboyepez17

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## PASO 7.3 — Verificar .gitignore antes del commit

```bash
cd trendscope

# CRÍTICO: verificar que estos archivos están excluidos
echo "Verificando .gitignore..."

git check-ignore .env        && echo "✅ .env excluido"        || echo "❌ .env NO excluido — DETENER"
git check-ignore data/       && echo "✅ data/ excluido"       || echo "❌ data/ NO excluido — DETENER"
git check-ignore .context/   && echo "✅ .context/ excluido"   || echo "❌ .context/ NO excluido — DETENER"

# Si alguno falla, revisar .gitignore antes de continuar
```

---

## PASO 7.4 — Commit inicial y push

```bash
cd trendscope
git init
git add .

# Verificar qué va al repo (no debe aparecer .env, data/, .context/)
git status

git commit -m "feat: TrendScope v1.0.0

Infraestructura de inteligencia de tendencias universal.

Fuentes: Reddit, Google Trends RSS, Twitter/X, Amazon, TikTok
Análisis: pysentimiento (local) + Claude Haiku API (premium)
CLI: python main.py — categorías predefinidas + tema libre
API REST: FastAPI /trends /categories /report /health
MCP: 3 tools para OpenClaw (analyze_trends, get_categories, get_latest_report)
Output: JSON para agentes + Markdown para humanos
Scraping: Scrapling (reemplaza Playwright + requests + BS4)

Dependencias: xactions-py (mamboyepez17/xactions-py)"

gh repo create trendscope --public --push --source=.
```

Si `gh` no está instalado:
```bash
# Crear repo manualmente en github.com/new con nombre: trendscope
git remote add origin https://github.com/mamboyepez17/trendscope.git
git branch -M main
git push -u origin main
```

---

## PASO 7.5 — Actualizar CHANGELOG final

```markdown
## [1.0.0] — FECHA — MODELO_USADO

### Añadido
- README.md público con documentación completa
- LICENSE MIT
- Publicado en github.com/mamboyepez17/trendscope

### Estado
PROYECTO COMPLETO v1.0.0
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 7

- [ ] `.env` NO está en el repo (verificado con git check-ignore)
- [ ] `data/` NO está en el repo
- [ ] `.context/` NO está en el repo
- [ ] `README.md` publicado con documentación completa
- [ ] `LICENSE` incluido
- [ ] Repo público en github.com/mamboyepez17/trendscope
- [ ] CHANGELOG actualizado con v1.0.0

## MENSAJE FINAL AL USUARIO

```
🎉 TRENDSCOPE v1.0.0 PUBLICADO

Repo: https://github.com/mamboyepez17/trendscope

Archivos públicos:
- Código fuente completo
- README.md con documentación
- .env.example (template)
- LICENSE MIT

Archivos privados (excluidos del repo):
- .env ✅
- data/ ✅
- .context/ ✅

TrendScope está listo. Los 7 bloques completados.
```

---

*TrendScope — Bloque 7 de 7 | PROYECTO COMPLETO*
