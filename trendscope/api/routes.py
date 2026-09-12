"""HTTP routes for TrendScope API (registered by create_app)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Query as QParam,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
)

from trendscope import __version__
from trendscope.api.middleware import api_key_is_valid
from trendscope.config import CATEGORIES, DATA_DIR
from trendscope.core import cache as result_cache
from trendscope.core.pipeline import run as run_pipeline
from trendscope.core.query import TrendQuery
from trendscope.narrator.engine import NARRATIVE_STYLES, generate_summary
from trendscope.output.exporter import export_csv, export_excel, export_json
from trendscope.settings import settings
from trendscope.watchlist.models import WatchItem


def _org_id(request) -> str:
    return getattr(request.state, "org_id", None) or "default"


def _run_pipeline_query(
    topic: str | None,
    category: str | None,
    geo: str = "CO",
    sentiment_engine: str = "local",
    top_n: int = 25,
) -> dict:
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


def register_routes(app: FastAPI, state) -> None:
    # state.store / state.scheduler se resuelven en cada request (inyectable en tests)

    @app.get("/narrate")
    def narrate(
        topic: str | None = QParam(None, description="Tema libre a narrar"),
        category: str | None = QParam(None, description="Categoria predefinida"),
        style: str = QParam(
            "executive", description="executive | creative | technical | alert"
        ),
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
            media_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )

    @app.get("/health", tags=["ops"])
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

    @app.get("/metrics", tags=["ops"])
    def metrics():
        """Métricas ligeras en texto Prometheus-compatible."""
        from trendscope.core.metrics import render_prometheus

        return PlainTextResponse(render_prometheus(), media_type="text/plain")

    @app.get("/metrics.json")
    def metrics_json():
        from trendscope.core.metrics import snapshot

        return snapshot()

    @app.post("/admin/prune-history")
    def prune_history(
        keep_days: int = QParam(90, ge=1, le=3650),
        keep_payload_days: int = QParam(14, ge=1, le=3650),
    ):
        """Retención de history: borra filas viejas y limpia payloads antiguos."""
        return state.store.prune_history(
            keep_days=keep_days, keep_payload_days=keep_payload_days
        )

    @app.get("/categories")
    def get_categories():
        """Lista de categorias predefinidas disponibles."""
        return {
            "categories": list(CATEGORIES.keys()),
            "description": "Pasa una de estas como ?category=nombre",
        }

    @app.get("/trends", tags=["trends"], summary="Analyze a topic or category")
    def get_trends(
        request: Request,
        topic: str | None = QParam(None, description="Tema libre"),
        category: str | None = QParam(None, description="Categoria predefinida"),
        geo: str = QParam("CO", description="Codigo ISO pais"),
        sentiment_engine: str = QParam("local", description="local | claude"),
        top_n: int = QParam(25, ge=1, le=100, description="Numero de resultados"),
        async_mode: bool = QParam(
            False, alias="async", description="Si true, devuelve 202 + job_id"
        ),
    ):
        """Analiza tendencias y retorna JSON estructurado."""
        if async_mode:
            if not topic and not category:
                raise HTTPException(status_code=400, detail="topic o category requerido")
            from trendscope.jobs.store import submit_analysis_job

            job_id = submit_analysis_job(
                "trends",
                topic,
                category,
                geo=geo,
                sentiment_engine=sentiment_engine,
                top_n=top_n,
                org_id=_org_id(request),
            )
            return JSONResponse(
                status_code=202,
                content={
                    "job_id": job_id,
                    "status": "pending",
                    "poll": f"/jobs/{job_id}",
                },
            )
        return _run_pipeline_query(topic, category, geo, sentiment_engine, top_n)

    @app.get("/jobs/{job_id}", tags=["jobs"], summary="Poll async job status")
    def get_job(request: Request, job_id: str):
        """Consulta el estado de un job asíncrono."""
        from trendscope.jobs.store import get_job_store, job_to_public

        job = get_job_store().get(job_id, org_id=_org_id(request))
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job_to_public(job)

    @app.get("/jobs/{job_id}/events", tags=["jobs"], summary="SSE job progress")
    async def job_events(request: Request, job_id: str):
        """Server-Sent Events: emite el estado del job hasta done/error."""
        import asyncio
        import json as json_mod

        from fastapi.responses import StreamingResponse

        from trendscope.jobs.store import get_job_store, job_to_public

        store = get_job_store()

        async def gen():
            last_status = None
            for _ in range(240):  # ~2 min max
                job = store.get(job_id, org_id=_org_id(request))
                if not job:
                    yield f"event: error\ndata: {json_mod.dumps({'error': 'Job not found'})}\n\n"
                    return
                pub = job_to_public(job)
                if pub["status"] != last_status:
                    last_status = pub["status"]
                    yield f"event: status\ndata: {json_mod.dumps(pub)}\n\n"
                if pub["status"] in {"done", "error"}:
                    yield f"event: final\ndata: {json_mod.dumps(pub)}\n\n"
                    return
                await asyncio.sleep(0.5)
            yield f"event: timeout\ndata: {json_mod.dumps({'error': 'timeout'})}\n\n"

        return StreamingResponse(gen(), media_type="text/event-stream")

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
        dashboard_path = Path(__file__).resolve().parent.parent / "dashboard.html"
        if dashboard_path.exists():
            return HTMLResponse(
                content=dashboard_path.read_text(encoding="utf-8"),
                media_type="text/html",
            )
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
        q1 = TrendQuery(
            mode="free", free_topic=topic1, sentiment_engine=sentiment_engine
        )
        q2 = TrendQuery(
            mode="free", free_topic=topic2, sentiment_engine=sentiment_engine
        )
        payload1, _ = run_pipeline(q1)
        payload2, _ = run_pipeline(q2)
        return {
            "topic1": {"name": topic1, "data": payload1},
            "topic2": {"name": topic2, "data": payload2},
        }

    @app.post("/watchlist")
    def create_watch_item(
        request: Request,
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
        alert_webhook: str | None = QParam(
            None, description="HTTPS webhook URL for alerts"
        ),
        alert_min_score: float | None = QParam(
            None, ge=0, le=100, description="Alert if top_score >= this"
        ),
        alert_sentiment_flip: bool = QParam(False, description="Alert on sentiment flip"),
        digest_webhook: str | None = QParam(
            None, description="HTTPS webhook URL for periodic digests"
        ),
        digest_interval_hours: int = QParam(
            24, ge=1, le=168, description="Digest interval in hours"
        ),
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
            digest_webhook=digest_webhook,
            digest_interval_hours=digest_interval_hours,
            org_id=_org_id(request),
        )
        item = state.store.add(item)
        state.scheduler.refresh()
        return item

    @app.get("/watchlist", tags=["watchlist"])
    def list_watch_items(request: Request):
        """List all watchlist items (scoped to caller org)."""
        items = state.store.list_all(org_id=_org_id(request))
        return {"items": [item.__dict__ for item in items]}

    @app.get("/watchlist/stats")
    def watchlist_stats():
        """Get watchlist and history aggregate stats."""
        return state.store.get_stats()

    @app.get("/watchlist/{item_id}")
    def get_watch_item(request: Request, item_id: int):
        """Get a single watchlist item."""
        item = state.store.get(item_id, org_id=_org_id(request))
        if not item:
            raise HTTPException(status_code=404, detail="Watch item not found")
        return item

    @app.put("/watchlist/{item_id}")
    def update_watch_item(
        request: Request,
        item_id: int,
        topic: str = QParam(..., description="Topic to monitor"),
        category: str | None = QParam(None, description="Predefined category (optional)"),
        geo: str = QParam("CO", description="ISO country code"),
        sentiment_engine: str = QParam("local", description="local | claude"),
        interval_minutes: int = QParam(
            60, ge=5, le=1440, description="Analysis interval in minutes"
        ),
        active: bool = QParam(True, description="Whether the item is active"),
    ):
        """Update a watchlist item."""
        existing = state.store.get(item_id, org_id=_org_id(request))
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
            org_id=_org_id(request),
        )
        item = state.store.update(item)
        state.scheduler.refresh()
        return item

    @app.delete("/watchlist/{item_id}")
    def delete_watch_item(request: Request, item_id: int):
        """Delete a watchlist item."""
        if not state.store.delete(item_id, org_id=_org_id(request)):
            raise HTTPException(status_code=404, detail="Watch item not found")
        state.scheduler.refresh()
        return {"status": "ok", "deleted": item_id}

    @app.post("/watchlist/{item_id}/run")
    def run_watch_item_now(
        request: Request,
        item_id: int,
        background: bool = QParam(False, description="Run as background job"),
    ):
        """Run analysis for a watchlist item immediately."""
        item = state.store.get(item_id, org_id=_org_id(request))
        if not item:
            raise HTTPException(status_code=404, detail="Watch item not found")
        if background:
            from concurrent.futures import ThreadPoolExecutor

            def _bg():
                state.scheduler._analyze_item(item)

            ThreadPoolExecutor(max_workers=1, thread_name_prefix="wl-run").submit(_bg)
            return JSONResponse(
                status_code=202, content={"status": "accepted", "topic": item.topic}
            )
        state.scheduler._analyze_item(item)
        return {"status": "ok", "topic": item.topic}

    @app.get("/history")
    def get_history(
        request: Request,
        topic: str | None = QParam(None, description="Filter by topic"),
        days: int = QParam(7, description="Number of days to look back"),
        limit: int = QParam(100, description="Maximum records to return"),
    ):
        """Get historical analysis records (scoped to caller org)."""
        records = state.store.get_history(
            topic=topic, days=days, limit=limit, org_id=_org_id(request)
        )
        return {
            "topic": topic,
            "days": days,
            "count": len(records),
            "records": [record.__dict__ for record in records],
        }

    @app.get("/forecast", tags=["watchlist"], summary="EMA / velocity / breakout")
    def get_forecast(
        request: Request,
        topic: str = QParam(..., description="Topic to forecast"),
        days: int = QParam(30, ge=1, le=365, description="Lookback window in days"),
    ):
        """EMA, velocity y detección de breakout sobre el historial de un tema."""
        from trendscope.analyzer.forecast import forecast_topic

        result = forecast_topic(
            state.store, topic, days=days, org_id=_org_id(request)
        )
        if not result:
            raise HTTPException(
                status_code=404, detail=f"No history for topic '{topic}'"
            )
        return result

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Real-time analysis via WebSocket."""
        if settings.api_key_required:
            token = websocket.query_params.get("api_key") or websocket.headers.get(
                "x-api-key"
            )
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
                    await websocket.send_json(
                        {"error": "top_n must be between 1 and 100"}
                    )
                    continue

                if sentiment_engine not in {"local", "claude"}:
                    await websocket.send_json(
                        {"error": "sentiment_engine must be local or claude"}
                    )
                    continue

                if not (len(geo) == 2 and geo.isalpha()):
                    await websocket.send_json(
                        {"error": "geo must be a 2-letter ISO code"}
                    )
                    continue

                if not topic and not category:
                    await websocket.send_json(
                        {"error": "topic or category required"}
                    )
                    continue

                if category and category not in CATEGORIES:
                    await websocket.send_json(
                        {"error": f"Unknown category: {category}"}
                    )
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
