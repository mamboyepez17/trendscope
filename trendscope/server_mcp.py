# server_mcp.py
# Servidor MCP — TrendScope como herramienta para agentes MCP
# Uso: python server_mcp.py
# Compatible con MCP SDK 2.x (MCPServer)
import asyncio

from mcp.server.mcpserver import MCPServer

from trendscope.config import CATEGORIES
from trendscope.core.pipeline import run as run_pipeline
from trendscope.core.query import TrendQuery

app = MCPServer("trendscope")


def _query(topic=None, category=None, geo="CO", days=None, lang=None,
           sentiment_engine="local", top_n=25, llm_provider=None, llm_model=None) -> TrendQuery:
    from trendscope.config import MAX_AGE_DAYS

    return TrendQuery(
        mode="category" if category else "free",
        category=category,
        free_topic=topic,
        geo=(geo or "CO").upper(),
        sentiment_engine=sentiment_engine,
        top_n=max(1, min(100, int(top_n))),
        max_age_days=max(1, min(30, int(days or MAX_AGE_DAYS))),
        lang=lang or None,
        llm_provider=llm_provider or None,
        llm_model=llm_model or None,
    )


@app.tool()
async def analyze_trends(
    topic: str | None = None,
    category: str | None = None,
    geo: str = "CO",
    days: int | None = None,
    lang: str | None = None,
    sentiment_engine: str = "local",
    top_n: int = 25,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> dict:
    """Analiza cómo se siente la gente sobre un tema (topic o category).

    geo: país ISO (CO, US, BR…). days: ventana reciente 1-30. lang: idioma de
    etiquetas es/en/pt. sentiment_engine: local | claude | llm (con
    llm_provider/llm_model: openai, claude, deepseek, qwen, glm, kimi, mimo…).
    """
    query = _query(topic, category, geo, days, lang, sentiment_engine, top_n, llm_provider, llm_model)
    loop = asyncio.get_running_loop()
    payload, _ = await loop.run_in_executor(None, run_pipeline, query)
    return payload


@app.tool()
def get_categories() -> dict:
    """Lista las categorias predefinidas disponibles."""
    return {"categories": list(CATEGORIES.keys())}


@app.tool()
def get_latest_report(topic: str) -> str:
    """Obtiene el ultimo reporte Markdown generado para un tema."""
    from pathlib import Path

    from trendscope.config import DATA_DIR
    from trendscope.core.paths import safe_slug

    slug = safe_slug(topic)
    reports = sorted(
        (p for p in Path(DATA_DIR).glob("report_*.md") if slug in p.name),
        reverse=True,
    )
    if reports:
        return reports[0].read_text(encoding="utf-8")
    return f"No hay reportes para '{slug}'"


@app.tool()
async def narrate_trends(
    topic: str | None = None,
    category: str | None = None,
    style: str = "executive",
    geo: str = "CO",
    days: int | None = None,
    lang: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> dict:
    """Resumen con IA (executive/creative/technical/alert) en el idioma pedido.

    llm_provider/llm_model eligen la IA (por defecto la de LLM_PROVIDER).
    """
    query = _query(topic, category, geo, days, lang)
    loop = asyncio.get_running_loop()
    payload, _ = await loop.run_in_executor(None, run_pipeline, query)
    from trendscope.narrator.engine import generate_summary

    return generate_summary(payload, style=style, provider=llm_provider, model=llm_model)


@app.tool()
async def compare_topics(topic1: str, topic2: str, geo: str = "CO", days: int | None = None,
                         lang: str | None = None) -> dict:
    """Compara dos temas lado a lado (mismo país, ventana e idioma)."""
    loop = asyncio.get_running_loop()

    def _run_both():
        q1 = _query(topic1, None, geo, days, lang)
        q2 = _query(topic2, None, geo, days, lang)
        p1, _ = run_pipeline(q1)
        p2, _ = run_pipeline(q2)
        return {
            "topic1": {"name": topic1, "data": p1},
            "topic2": {"name": topic2, "data": p2},
        }

    return await loop.run_in_executor(None, _run_both)


@app.tool()
def doctor() -> dict:
    """Diagnostica el estado de todas las fuentes de datos."""
    from trendscope.core.doctor import check_all

    return check_all()


@app.tool()
def watchlist_add(
    topic: str,
    category: str | None = None,
    geo: str = "CO",
    interval_minutes: int = 60,
    alert_webhook: str | None = None,
    alert_min_score: float | None = None,
    alert_sentiment_flip: bool = False,
) -> dict:
    """Agrega un tema a la watchlist de monitoreo recurrente."""
    from dataclasses import asdict

    from trendscope.watchlist.models import WatchItem
    from trendscope.watchlist.store import get_store

    store = get_store()
    item = WatchItem(
        id=None,
        topic=topic,
        category=category,
        geo=geo,
        sentiment_engine="local",
        interval_minutes=max(5, min(1440, int(interval_minutes))),
        active=True,
        alert_webhook=alert_webhook,
        alert_min_score=alert_min_score,
        alert_sentiment_flip=alert_sentiment_flip,
    )
    item = store.add(item)
    return asdict(item)


@app.tool()
def watchlist_list() -> dict:
    """Lista los temas monitorizados en la watchlist."""
    from dataclasses import asdict

    from trendscope.watchlist.store import get_store

    items = get_store().list_all()
    return {"items": [asdict(i) for i in items]}


@app.tool()
def watchlist_run(item_id: int) -> dict:
    """Ejecuta el análisis de un item de la watchlist ahora mismo."""
    from trendscope.watchlist.scheduler import get_scheduler
    from trendscope.watchlist.store import get_store

    store = get_store()
    item = store.get(int(item_id))
    if not item:
        return {"error": f"Watch item {item_id} not found"}
    get_scheduler()._analyze_item(item)
    return {"status": "ok", "topic": item.topic}


@app.tool()
def history_get(
    topic: str | None = None,
    days: int = 7,
    limit: int = 20,
) -> dict:
    """Obtiene el historial de análisis (sin payload completo)."""
    from dataclasses import asdict

    from trendscope.watchlist.store import get_store

    records = get_store().get_history(topic=topic, days=int(days), limit=int(limit))
    return {
        "count": len(records),
        "records": [{**asdict(r), "payload_json": None} for r in records],
    }


async def main_async() -> None:
    await app.run_stdio_async()


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
