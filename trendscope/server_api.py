# server_api.py
# API REST — TrendScope accesible por cualquier agente HTTP
# Uso: python server_api.py
# Docs: http://localhost:8000/docs
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, Query as QParam, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, HTMLResponse, FileResponse
import uvicorn

from trendscope.config import API_HOST, API_PORT, CATEGORIES, DATA_DIR
from trendscope.core.query import TrendQuery
from trendscope.settings import settings
from trendscope.core.pipeline import run as run_pipeline
from trendscope.core import cache as result_cache
from trendscope.narrator.engine import generate_summary, NARRATIVE_STYLES
from trendscope.output.exporter import export_json, export_csv, export_excel
from trendscope.api.middleware import (
    APIKeyMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    api_key_is_valid,
)
from trendscope.logging_config import setup_logging
from trendscope.watchlist.models import WatchItem
from trendscope.watchlist.store import get_store
from trendscope.watchlist.scheduler import WatchlistScheduler
from trendscope import __version__


from loguru import logger

setup_logging()

watchlist_store = get_store()
watchlist_scheduler = WatchlistScheduler(watchlist_store)


def _warn_if_exposed() -> None:
    if settings.api_host not in {"127.0.0.1", "localhost", "::1"} and not settings.api_key_required:
        logger.warning(
            "API expuesta en {} SIN API key. Configura API_KEY_REQUIRED=true y API_KEYS.",
            settings.api_host,
        )


def _run_pipeline_query(
    topic: str | None,
    category: str | None,
    geo: str = "CO",
    sentiment_engine: str = "local",
    top_n: int = 25,
) -> dict:
    """Valida parámetros y ejecuta el pipeline."""
    if not topic and not category:
        raise HTTPException(
            status_code=400,
            detail="Debes pasar 'topic' o 'category'. Ejemplo: ?topic=crypto+Colombia",
        )

    if category and category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria '{category}' no existe. Usa GET /categories para ver disponibles.",
        )

    query = TrendQuery(
        mode="category" if category else "free",
        category=category,
        free_topic=topic,
        geo=geo,
        sentiment_engine=sentiment_engine,
        top_n=top_n,
    )
    try:
        payload, _ = run_pipeline(query)
    except RuntimeError as e:
        if "saturado" in str(e).lower() or "saturated" in str(e).lower():
            raise HTTPException(status_code=503, detail=str(e)) from e
        raise
    return payload


app = FastAPI(
    title="TrendScope API",
    description="Inteligencia de tendencias universal — mamboyepez17",
    version=__version__,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(APIKeyMiddleware)


@app.on_event("startup")
def start_watchlist_scheduler():
    _warn_if_exposed()
    if settings.watchlist_enabled:
        watchlist_scheduler.start()


@app.on_event("shutdown")
def stop_watchlist_scheduler():
    watchlist_scheduler.stop()


@app.get("/narrate")
def narrate(
    topic: str | None = QParam(None, description="Tema libre a narrar"),
    category: str | None = QParam(None, description="Categoria predefinida"),
    style: str = QParam("executive", description="executive | creative | technical | alert"),
    geo: str = QParam("CO", description="Codigo ISO pais"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
):
    """Genera una narrativa inteligente sobre un tema usando el proveedor configurado."""
    if not topic and not category:
        raise HTTPException(
            status_code=400,
            detail="Debes pasar 'topic' o 'category'. Ejemplo: ?topic=crypto+Colombia&style=executive",
        )

    if category and category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Categoria '{category}' no existe. Usa GET /categories para ver disponibles.",
        )

    if style not in NARRATIVE_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Estilo '{style}' no valido. Opciones: {', '.join(NARRATIVE_STYLES.keys())}",
        )

    payload = _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)
    result = generate_summary(payload, style=style)
    return {
        "topic": topic or category,
        "style": result["style"],
        "provider": result["provider"],
        "model": result["model"],
        "narrative": result["narrative"],
    }


@app.get("/export/json")
def export_json_endpoint(
    topic: str | None = QParam(None, description="Tema libre"),
    category: str | None = QParam(None, description="Categoria predefinida"),
    geo: str = QParam("CO", description="Codigo ISO pais"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
):
    """Exporta el análisis completo a JSON descargable."""
    payload = _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)
    path = export_json(payload)
    return FileResponse(path, filename=path.name, media_type="application/json")


@app.get("/export/csv")
def export_csv_endpoint(
    topic: str | None = QParam(None, description="Tema libre"),
    category: str | None = QParam(None, description="Categoria predefinida"),
    geo: str = QParam("CO", description="Codigo ISO pais"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
):
    """Exporta las tendencias top a CSV descargable."""
    payload = _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)
    path = export_csv(payload)
    return FileResponse(path, filename=path.name, media_type="text/csv")


@app.get("/export/xlsx")
def export_excel_endpoint(
    topic: str | None = QParam(None, description="Tema libre"),
    category: str | None = QParam(None, description="Categoria predefinida"),
    geo: str = QParam("CO", description="Codigo ISO pais"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
):
    """Exporta las tendencias top a Excel (.xlsx) descargable."""
    payload = _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)
    path = export_excel(payload)
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.get("/health")
def health():
    """Estado del servicio con información de configuración."""
    return {
        "status": "ok",
        "service": "TrendScope",
        "version": __version__,
        "narrator_provider": settings.narrator_provider,
        "narrative_enabled": settings.narrative_enabled,
        "sentiment_engine_default": settings.sentiment_engine,
    }


@app.get("/categories")
def get_categories():
    """Lista de categorias predefinidas disponibles."""
    return {
        "categories": list(CATEGORIES.keys()),
        "description": "Pasa una de estas como ?category=nombre",
    }


@app.get("/trends")
def get_trends(
    topic: str | None = QParam(None, description="Tema libre"),
    category: str | None = QParam(None, description="Categoria predefinida"),
    geo: str = QParam("CO", description="Codigo ISO pais"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
):
    """
    Analiza tendencias y retorna JSON estructurado.
    Usar ?topic=TEMA o ?category=CATEGORIA.
    """
    return _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)


@app.get("/report", response_class=PlainTextResponse)
def get_report(
    topic: str | None = QParam(None, description="Tema del reporte"),
    category: str | None = QParam(None, description="Categoria del reporte"),
):
    """Retorna el ultimo reporte Markdown generado para un tema."""
    from trendscope.core.paths import safe_slug

    slug = safe_slug(topic or category or "")
    data_path = Path(DATA_DIR)

    if not data_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No hay reportes generados aun. Genera uno primero con GET /trends",
        )

    # Filtrar por substring sobre nombres ya existentes (sin glob con input del usuario)
    reports = sorted(
        (p for p in data_path.glob("report_*.md") if slug in p.name),
        reverse=True,
    )
    if not reports:
        raise HTTPException(
            status_code=404,
            detail=f"No hay reportes para '{slug}'. Genera uno primero con GET /trends",
        )
    return reports[0].read_text(encoding="utf-8")


@app.get("/cache/stats")
def cache_stats():
    """Retorna estadisticas del cache de resultados."""
    return result_cache.stats()


@app.delete("/cache")
def cache_clear():
    """Limpia todo el cache de resultados."""
    result_cache.clear()
    return {"status": "ok", "message": "Cache limpiado"}


@app.get("/dashboard")
def get_dashboard():
    """Sirve el dashboard web HTML."""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    dashboard_path = Path(__file__).parent / "dashboard.html"
    if dashboard_path.exists():
        return HTMLResponse(content=dashboard_path.read_text(encoding="utf-8"), media_type="text/html")
    raise HTTPException(status_code=404, detail="dashboard.html no encontrado")


@app.get("/doctor")
def doctor():
    """Diagnostica el estado de todas las fuentes de TrendScope."""
    from trendscope.core.doctor import check_all
    return check_all()


@app.get("/compare")
def compare_topics(
    topic1: str = QParam(..., description="Primer tema a comparar"),
    topic2: str = QParam(..., description="Segundo tema a comparar"),
    sentiment_engine: str = QParam("local", description="local | claude"),
):
    """Compara dos temas lado a lado."""
    q1 = TrendQuery(mode="free", free_topic=topic1, sentiment_engine=sentiment_engine)
    q2 = TrendQuery(mode="free", free_topic=topic2, sentiment_engine=sentiment_engine)

    payload1, _ = run_pipeline(q1)
    payload2, _ = run_pipeline(q2)

    return {
        "topic1": {"name": topic1, "data": payload1},
        "topic2": {"name": topic2, "data": payload2},
    }


@app.post("/watchlist")
def create_watch_item(
    topic: str = QParam(..., description="Topic to monitor"),
    category: str | None = QParam(None, description="Predefined category (optional)"),
    geo: str = QParam("CO", description="ISO country code"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    interval_minutes: int = QParam(
        settings.watchlist_default_interval_minutes,
        ge=5,
        le=1440,
        description="Analysis interval in minutes",
    ),
    alert_webhook: str | None = QParam(None, description="HTTPS webhook URL for alerts"),
    alert_min_score: float | None = QParam(None, ge=0, le=100, description="Alert if top_score >= this"),
    alert_sentiment_flip: bool = QParam(False, description="Alert on sentiment flip"),
):
    """Add a topic to the watchlist."""
    if category and category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{category}' does not exist. Use GET /categories",
        )
    item = WatchItem(
        id=None,
        topic=topic,
        category=category,
        geo=geo,
        sentiment_engine=sentiment_engine,
        interval_minutes=interval_minutes,
        active=True,
        alert_webhook=alert_webhook,
        alert_min_score=alert_min_score,
        alert_sentiment_flip=alert_sentiment_flip,
    )
    item = watchlist_store.add(item)
    watchlist_scheduler.refresh()
    return item


@app.get("/watchlist")
def list_watch_items():
    """List all watchlist items."""
    items = watchlist_store.list_all()
    return {"items": [item.__dict__ for item in items]}


@app.get("/watchlist/stats")
def watchlist_stats():
    """Get watchlist and history aggregate stats."""
    return watchlist_store.get_stats()


@app.get("/watchlist/{item_id}")
def get_watch_item(item_id: int):
    """Get a single watchlist item."""
    item = watchlist_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return item


@app.put("/watchlist/{item_id}")
def update_watch_item(
    item_id: int,
    topic: str = QParam(..., description="Topic to monitor"),
    category: str | None = QParam(None, description="Predefined category (optional)"),
    geo: str = QParam("CO", description="ISO country code"),
    sentiment_engine: str = QParam("local", description="local | claude"),
    interval_minutes: int = QParam(60, ge=5, le=1440, description="Analysis interval in minutes"),
    active: bool = QParam(True, description="Whether the item is active"),
):
    """Update a watchlist item."""
    existing = watchlist_store.get(item_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Watch item not found")
    item = WatchItem(
        id=item_id,
        topic=topic,
        category=category,
        geo=geo,
        sentiment_engine=sentiment_engine,
        interval_minutes=interval_minutes,
        active=active,
    )
    item = watchlist_store.update(item)
    watchlist_scheduler.refresh()
    return item


@app.delete("/watchlist/{item_id}")
def delete_watch_item(item_id: int):
    """Delete a watchlist item."""
    if not watchlist_store.delete(item_id):
        raise HTTPException(status_code=404, detail="Watch item not found")
    watchlist_scheduler.refresh()
    return {"status": "ok", "deleted": item_id}


@app.post("/watchlist/{item_id}/run")
def run_watch_item_now(item_id: int):
    """Run analysis for a watchlist item immediately."""
    item = watchlist_store.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Watch item not found")
    watchlist_scheduler._analyze_item(item)
    return {"status": "ok", "topic": item.topic}


@app.get("/history")
def get_history(
    topic: str | None = QParam(None, description="Filter by topic"),
    days: int = QParam(7, description="Number of days to look back"),
    limit: int = QParam(100, description="Maximum records to return"),
):
    """Get historical analysis records."""
    records = watchlist_store.get_history(topic=topic, days=days, limit=limit)
    return {
        "topic": topic,
        "days": days,
        "count": len(records),
        "records": [record.__dict__ for record in records],
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time analysis via WebSocket.

    Send a JSON message with {topic, category?, geo?, sentiment_engine?, top_n?}.
    If API keys are required, pass ?api_key=... on the WS URL or X-API-Key header.
    """
    if settings.api_key_required:
        token = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
        if not api_key_is_valid(token):
            await websocket.close(code=1008)
            return

    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            try:
                params = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            topic = params.get("topic")
            category = params.get("category")
            geo = str(params.get("geo", "CO") or "CO").upper()
            sentiment_engine = params.get("sentiment_engine", "local")

            try:
                top_n = int(params.get("top_n", 25))
            except (TypeError, ValueError):
                await websocket.send_json({"error": "top_n must be an integer"})
                continue

            if not 1 <= top_n <= 100:
                await websocket.send_json({"error": "top_n must be between 1 and 100"})
                continue

            if sentiment_engine not in {"local", "claude"}:
                await websocket.send_json({"error": "sentiment_engine must be local or claude"})
                continue

            if not (len(geo) == 2 and geo.isalpha()):
                await websocket.send_json({"error": "geo must be a 2-letter ISO code"})
                continue

            if not topic and not category:
                await websocket.send_json({"error": "topic or category required"})
                continue

            if category and category not in CATEGORIES:
                await websocket.send_json({"error": f"Unknown category: {category}"})
                continue

            query = TrendQuery(
                mode="category" if category else "free",
                category=category,
                free_topic=topic,
                geo=geo,
                sentiment_engine=sentiment_engine,
                top_n=top_n,
            )

            try:
                loop = asyncio.get_running_loop()
                payload, _ = await asyncio.wait_for(
                    loop.run_in_executor(None, run_pipeline, query),
                    timeout=120,
                )
                await websocket.send_json(payload)
            except TimeoutError:
                await websocket.send_json({"error": "Pipeline timeout (120s)"})
            except Exception as e:
                await websocket.send_json({"error": f"Pipeline error: {e}"})
    except WebSocketDisconnect:
        pass


def run():
    import uvicorn
    uvicorn.run("trendscope.server_api:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    run()
