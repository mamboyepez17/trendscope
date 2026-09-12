# server_api.py
# API REST — TrendScope accesible por cualquier agente HTTP
# Uso: python server_api.py
# Docs: http://localhost:8000/docs
#
# Compat: `from trendscope.server_api import app, watchlist_store`
# Preferir `create_app()` en tests nuevos (sin side-effects).

from trendscope.api.factory import AppState, create_app
from trendscope.config import API_HOST, API_PORT
from trendscope.core.pipeline import run as run_pipeline
from trendscope.settings import settings
from trendscope.watchlist.scheduler import WatchlistScheduler
from trendscope.watchlist.store import get_store

# App por defecto para uvicorn y tests legacy.
# El store se crea al construir AppState; los tests pueden inyectar otro vía create_app().
app = create_app(configure_logging=True)

# Compatibilidad con tests que parchean watchlist_store / watchlist_scheduler
watchlist_store = app.state.ts.store
watchlist_scheduler = app.state.ts.scheduler


def run():
    import uvicorn

    uvicorn.run("trendscope.server_api:app", host=API_HOST, port=API_PORT, reload=False)


if __name__ == "__main__":
    run()
