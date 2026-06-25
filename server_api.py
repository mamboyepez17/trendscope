# server_api.py
# API REST — TrendScope accesible por cualquier agente HTTP
# Uso: python server_api.py
# Docs: http://localhost:8000/docs
import threading
from pathlib import Path

from fastapi import FastAPI, Query as QParam, HTTPException
from fastapi.responses import PlainTextResponse, HTMLResponse
import uvicorn

from config import API_HOST, API_PORT, CATEGORIES, DATA_DIR
from core.query import TrendQuery
from core.pipeline import run as run_pipeline
from core import cache as result_cache

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
    top_n: int = QParam(25, description="Numero de resultados"),
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

    # Pipeline sincronico (FastAPI corre en threadpool por defecto para sync endpoints)
    payload, _ = run_pipeline(query)
    return payload


@app.get("/report", response_class=PlainTextResponse)
def get_report(
    topic: str | None = QParam(None, description="Tema del reporte"),
    category: str | None = QParam(None, description="Categoria del reporte"),
):
    """Retorna el ultimo reporte Markdown generado para un tema."""
    slug = (topic or category or "").replace(" ", "_")[:30]
    data_path = Path(DATA_DIR)

    if not data_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No hay reportes generados aun. Genera uno primero con GET /trends",
        )

    reports = sorted(data_path.glob(f"report_*{slug}*.md"), reverse=True)
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
    from core.doctor import check_all
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


if __name__ == "__main__":
    uvicorn.run("server_api:app", host=API_HOST, port=API_PORT, reload=False)
