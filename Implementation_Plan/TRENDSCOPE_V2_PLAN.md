# TrendScope V2 — Plan de Hardening y Escalado

> **Versión:** 2.0.0  
> **Fecha:** 2026-02-12  
> **Base:** auditoría de seguridad + calidad + producto sobre v1.5.0 (`7e3dbf5`)  
> **Plan anterior:** `TRENDSCOPE_EVOLUTION_PLAN.md` (bloques 0–10, todos completados)

---

## Filosofía de trabajo (igual que v1)

- Un bloque a la vez. Bloque terminado, probado y commiteado **antes** de pasar al siguiente.
- **Cada bloque tiene su suite de tests.** Si los tests del bloque fallan, NO se avanza.
- Cada tarea es de 2–5 minutos máximo.
- TDD cuando sea posible: test rojo → implementación mínima → test verde.
- Sin features de más (YAGNI). Solo lo que la auditoría pide ahora.
- Commits frecuentes en español + conventional commits (`fix:`, `feat:`, `chore:`, `test:`, `docs:`, `perf:`, `sec:`).
- Tras cada bloque: actualizar `docs/context/CHANGELOG.md` y marcar estado abajo.
- Esperar **APROBADO** del usuario antes del siguiente bloque (o continuar si el usuario autoriza todos de una).

---

## Criterio global de calidad por bloque

Antes de marcar un bloque como `[x]`:

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Todos los tests del repo en verde (los nuevos del bloque + los preexistentes).
- Nada roto en `pytest` (no aceptar “esto ya fallaba antes” sin justificar en el bloque).
- Commit limpio en `main`.

---

## Resumen de bloques

| Bloque | Nombre | Objetivo | Impacto | Prioridad |
|--------|--------|----------|---------|-----------|
| 11 | Corrección crítica de sentimiento + deps | Que el motor de sentimiento funcione y las deps estén declaradas | Crítico | P0 |
| 12 | Seguridad de paths y ficheros | Cerrar path traversal y glob injection | Crítico | P0 |
| 13 | Superficie de API segura | Auth en WS, defaults seguros, validaciones, headers | Crítico | P0 |
| 14 | Pipeline y logging robustos | No destruir loguru, cache key completa, errores WS | Alto | P0 |
| 15 | SQLite concurrente | WAL + busy_timeout en cache y watchlist | Alto | P0 |
| 16 | Docker endurecido | Multi-stage, sin dev tools, healthcheck, caps | Alto | P0 |
| 17 | Rate limit y middleware | Purge de IPs, proxy-aware, compare_digest | Alto | P0 |
| 18 | Rendimiento del pipeline | Dedup/insights, HN paralelo, timeouts, sessions | Alto | P0 |
| 19 | Config coherente y geo dinámico | Unificar settings/config, quitar Colombia/2026 hardcodeados | Medio | P0 |
| 20 | Tests de regresión e integración | Pipeline, scrapers mockeados, app factory, aislamiento | Alto | P0 |
| 21 | Alertas de watchlist (webhooks) | Avisar cuando score/sentiment cruza umbral | Alto | P1 |
| 22 | Cola de trabajos asíncrona | Jobs no bloqueantes + 202 + job_id | Alto | P1 |
| 23 | Paridad MCP ↔ REST | Tools de watchlist/history/narrate/doctor | Medio | P1 |
| 24 | Observabilidad | Métricas, source_errors en payload, retention de history | Medio | P1 |
| 25 | Forecasting básico | EMA / z-score sobre history | Medio | P2 |
| 26 | Multi-tenant y auth de verdad | JWT/OAuth + org_id | Alto | P2 |

**Fase 1 (inmediata):** bloques 11–20 — hardening y correcciones.  
**Fase 2 (producto):** bloques 21–24 — alertas, jobs, MCP, observabilidad.  
**Fase 3 (plataforma):** bloques 25–26 — ML y SaaS.

---

## Estado

- [x] Bloque 11 — Corrección crítica de sentimiento + deps
- [x] Bloque 12 — Seguridad de paths y ficheros
- [ ] Bloque 13 — Superficie de API segura
- [ ] Bloque 14 — Pipeline y logging robustos
- [ ] Bloque 15 — SQLite concurrente
- [ ] Bloque 16 — Docker endurecido
- [ ] Bloque 17 — Rate limit y middleware
- [ ] Bloque 18 — Rendimiento del pipeline
- [ ] Bloque 19 — Config coherente y geo dinámico
- [ ] Bloque 20 — Tests de regresión e integración
- [ ] Bloque 21 — Alertas de watchlist (webhooks)
- [ ] Bloque 22 — Cola de trabajos asíncrona
- [ ] Bloque 23 — Paridad MCP ↔ REST
- [ ] Bloque 24 — Observabilidad
- [ ] Bloque 25 — Forecasting básico
- [ ] Bloque 26 — Multi-tenant y auth de verdad

---

# BLOQUE 11 — Corrección crítica de sentimiento + deps

**Objetivo:** El motor de sentimiento vuelve a funcionar. Dependencias declaradas y coherentes.

**Por qué primero:** Hoy `analyze_items` falla siempre (`from sentiment.…` en vez de `from trendscope.sentiment.…`) y todo se marca `neutral` / `engine="failed"`. Es el bug de mayor impacto del producto.

**Archivos:**
- `trendscope/sentiment/__init__.py`
- `trendscope/core/doctor.py`
- `pyproject.toml`
- `requirements.txt`
- `trendscope/tests/test_sentiment_imports.py` (nuevo)

### Tarea 11.1 — Test rojo del bug
**Archivo:** `trendscope/tests/test_sentiment_imports.py`

```python
"""Regression: sentiment engines must import from trendscope.sentiment, not bare sentiment."""

from trendscope.core.query import TrendQuery
from trendscope.sentiment import analyze_items


def test_local_engine_does_not_fail_silently():
    items = [{"source": "t", "title": "Me encanta este producto increíble"}]
    query = TrendQuery(mode="free", free_topic="test", sentiment_engine="local")
    result = analyze_items(items, query)
    assert result[0]["sentiment_engine"] != "failed"
    assert result[0]["sentiment_label"] in {"positive", "negative", "neutral"}


def test_import_paths_are_package_relative():
    import trendscope.sentiment as pkg
    import inspect

    src = inspect.getsource(pkg)
    assert "from sentiment." not in src
    assert "from trendscope.sentiment." in src or "from ." in src
```

**Verificación:** el test debe fallar (rojo).

### Tarea 11.2 — Arreglar imports de sentimiento
**Archivo:** `trendscope/sentiment/__init__.py`

```python
# ANTES (roto)
from sentiment.claude_engine import analyze
from sentiment.local_engine import analyze

# DESPUÉS
from trendscope.sentiment.claude_engine import analyze
from trendscope.sentiment.local_engine import analyze
```

### Tarea 11.3 — Arreglar import del doctor
**Archivo:** `trendscope/core/doctor.py` (~línea 182)

```python
from trendscope.sentiment.local_engine import _analyze_fallback
```

### Tarea 11.4 — Declarar `requests`
**Archivos:** `pyproject.toml`, `requirements.txt`

- Añadir `requests>=2.31.0` a `dependencies` de pyproject.
- Añadir `requests>=2.31.0` a requirements.txt.

### Tarea 11.5 — Sincronizar requirements.txt con pyproject
`requirements.txt` debe contener todas las deps runtime de `pyproject.toml` (hoy faltan: `pydantic-settings`, `httpx`, `tenacity`, `apscheduler`, `websockets`, `ollama`, `openpyxl`, `requests`).

**Regla de este plan:** pyproject es la fuente de verdad; requirements.txt es un pin/export, no un segundo invento. Comentario en requirements: `# Generated/synced from pyproject.toml`.

### Tarea 11.6 — Comprobar claude path (opcional, sin API key)
Test unitario que solo verifica que el módulo importa:

```python
def test_claude_engine_module_imports():
    from trendscope.sentiment import claude_engine
    assert hasattr(claude_engine, "analyze")
```

### Criterio de aprobación del Bloque 11

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_sentiment_imports.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- `test_local_engine_does_not_fail_silently` en verde.
- Suite completa en verde.
- Commit: `fix(sentiment): imports de paquete y dependencia requests declarada`

**¿Aprobado para continuar al Bloque 12?**

---

# BLOQUE 12 — Seguridad de paths y ficheros

**Objetivo:** Cerrar path traversal en exportaciones y glob injection en `/report`.

**Archivos:**
- `trendscope/core/query.py`
- `trendscope/output/exporter.py`
- `trendscope/output/json_exporter.py`
- `trendscope/output/report_exporter.py`
- `trendscope/server_api.py`
- `trendscope/server_mcp.py`
- `trendscope/core/paths.py` (nuevo, helper compartido)
- `trendscope/tests/test_path_safety.py` (nuevo)

### Tarea 12.1 — Helper de slug seguro
**Archivo nuevo:** `trendscope/core/paths.py`

```python
import re
from pathlib import Path

_SLUG_RE = re.compile(r"[^a-zA-Z0-9_-]+")

def safe_slug(raw: str | None, max_len: int = 30) -> str:
    """Slug seguro para nombres de fichero. Nunca permite '..', '/', '\\', glob chars."""
    if not raw:
        return "general"
    s = _SLUG_RE.sub("_", raw.strip())
    s = s.strip("._-") or "general"
    return s[:max_len]

def safe_data_path(data_dir: Path, filename: str) -> Path:
    """Une filename a data_dir y garantiza que el resultado no escapa del directorio."""
    base = data_dir.resolve()
    path = (base / filename).resolve()
    if not str(path).startswith(str(base)):
        raise ValueError(f"Path escape detected: {filename}")
    return path
```

### Tarea 12.2 — Tests rojos
**Archivo:** `trendscope/tests/test_path_safety.py`

Cubrir:
- `safe_slug("../../etc/passwd")` no contiene `..` ni `/`
- `safe_slug("*")` no contiene `*`
- `safe_slug("[a-z]")` no contiene `[`
- `export_json` con topic malicioso no escribe fuera de `data/`
- `/report?topic=*` no lista todos los reportes (mock data_dir)

### Tarea 12.3 — Usar `safe_slug` en `TrendQuery.topic_slug`
**Archivo:** `trendscope/core/query.py`

```python
from trendscope.core.paths import safe_slug

@property
def topic_slug(self) -> str:
    return safe_slug(self.free_topic or self.category or "general")
```

### Tarea 12.4 — Sanitizar nombres en exporters
**Archivos:** `exporter.py`, `json_exporter.py`, `report_exporter.py`

Sustituir `topic.replace(' ', '_')[:30]` por `safe_slug(topic)` y validar con `safe_data_path` antes de `write_text` / `open` / `wb.save`.

### Tarea 12.5 — Sanitizar `/report` y MCP
**Archivos:** `server_api.py:217-226`, `server_mcp.py`

- Slug = `safe_slug(...)`
- No interpolar glob con input del usuario: listar ficheros y filtrar con `in name` sobre el slug ya sanitizado, o construir patrón solo con caracteres alfanuméricos.

### Criterio de aprobación del Bloque 12

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_path_safety.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `sec(paths): slug seguro y cierre de path traversal / glob injection`

**¿Aprobado para continuar al Bloque 13?**

---

# BLOQUE 13 — Superficie de API segura

**Objetivo:** Defaults seguros, auth en WebSocket, validaciones de entrada, security headers.

**Archivos:**
- `trendscope/settings.py`
- `trendscope/api/middleware.py`
- `trendscope/server_api.py`
- `.env.example`
- `trendscope/tests/test_api_security.py` (nuevo)

### Tarea 13.1 — Defaults seguros de red
**Archivos:** `settings.py`, `.env.example`

| Setting | Hoy | Nuevo default | Nota |
|---|---|---|---|
| `api_host` | `0.0.0.0` | `127.0.0.1` | Docker puede override a `0.0.0.0` en compose |
| `api_key_required` | `False` | se mantiene False en dev local, pero… | …si `api_host` es `0.0.0.0` y no hay keys, **log warning fuerte** al arrancar |
| `api_keys` | `""` | filtrar strings vacíos al split | hoy `""` produce `{""}` |

**Nueva regla en startup:**

```python
if settings.api_host not in {"127.0.0.1", "localhost"} and not settings.api_key_required:
    logger.warning("API expuesta en {} SIN API key. Configura API_KEY_REQUIRED=true y API_KEYS.", settings.api_host)
```

### Tarea 13.2 — API key constant-time
**Archivo:** `middleware.py`

```python
import hmac

keys = {k.strip() for k in settings.api_keys.split(",") if k.strip()}
if not api_key or not any(hmac.compare_digest(api_key, k) for k in keys):
    return 401
```

### Tarea 13.3 — Auth del WebSocket
**Archivo:** `server_api.py` (`/ws`)

- Si `api_key_required`:
  - Aceptar API key por query `?api_key=` **o** header `X-API-Key` (browser WS no puede headers).
  - Validar **antes** de `await websocket.accept()`.
  - Si falla: `await websocket.close(code=1008)`.

### Tarea 13.4 — Validar parámetros del WS
- `top_n = int(...)` con try/except → error JSON, no crash.
- `top_n` con `ge=1, le=100`.
- `sentiment_engine` in `{"local", "claude"}`.
- `geo` con regex `^[A-Z]{2}$` (o allowlist).

### Tarea 13.5 — Límites en endpoints HTTP
En todos los `top_n: int = QParam(...)`:

```python
top_n: int = QParam(25, ge=1, le=100)
interval_minutes: int = QParam(60, ge=5, le=1440)
```

(Decisión: mínimo de intervalo de watchlist = 5 minutos para evitar DoS vía scheduler.)

### Tarea 13.6 — Security headers
**Archivo:** `middleware.py` o nuevo `api/security_headers.py`

```python
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path == "/dashboard":
        response.headers["Content-Security-Policy"] = "default-src 'self'; img-src 'self' data:; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'"
    return response
```

> Nota: el dashboard usa Chart.js desde CDN — el CSP debe permitirlo explícitamente o migrar el script a local (preferible a futuro).

### Tarea 13.7 — No filtrar config sensible en `/health` y `/doctor`
- `/health`: quitar `api_key_required` del payload público (o proteger).
- `/doctor`: no mostrar longitudes de cookies; solo `"twitter": "configured" | "missing"`.
- `/doctor` pasa a requerir API key si está activada (hoy está en el allowlist solo `/health` `/docs` `/openapi.json` — **quitar `/doctor` del libre acceso implícito**; el allowlist actual no lo incluye, OK, pero hay que verificar).

### Tarea 13.8 — Tests
**Archivo:** `trendscope/tests/test_api_security.py`

- API key con `hmac` rechaza wrong key / acepta good key.
- Keys vacías se filtran (`API_KEYS=""` → 401 si required).
- `top_n=0` y `top_n=1000` → 422.
- `interval_minutes=1` → 422.
- WS sin key cuando required → closed.
- Response tiene `X-Content-Type-Options: nosniff`.
- `/health` no expone campos sensibles.

### Criterio de aprobación del Bloque 13

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_api_security.py trendscope/tests/test_middleware.py trendscope/tests/test_websocket.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `sec(api): auth WS, validaciones, headers y defaults seguros`

**¿Aprobado para continuar al Bloque 14?**

---

# BLOQUE 14 — Pipeline y logging robustos

**Objetivo:** El pipeline no destruye el logging global; cache key completa; WebSocket no revienta silencioso.

**Archivos:**
- `trendscope/core/pipeline.py`
- `trendscope/server_api.py`
- `trendscope/logging_config.py`
- `trendscope/tests/test_pipeline_logging.py` (nuevo)

### Tarea 14.1 — Dejar de mutar sinks de loguru
**Archivo:** `pipeline.py:71-73, 117-119`

**Eliminar** `logger.remove()` / re-add. Sustituir por silenciado local de scrapers o simplemente no tocar el logger global.

Opción mínima y segura:

```python
# NO hacer esto:
# logger.remove()
# logger.add(lambda msg: None, level="ERROR")

# Mejor: un contexto que no toca sinks globales
from contextlib import contextmanager

@contextmanager
def _quiet_scraper_logs():
    # Solo subir nivel temporal si hace falta; NO remove()
    yield
```

Si se necesita silencio visual en CLI, usar `logger.disable("trendscope.scrapers")` / `enable` en finally, o flag `verbose` del pipeline. **Nunca** `logger.remove()` sin restaurar los sinks originales.

### Tarea 14.2 — Cache key completa
**Archivo:** `pipeline.py:63`

```python
from hashlib import sha1
kw = "|".join(query.keywords)
cache_key = f"{query.mode}:{query.category or query.free_topic}:{query.geo}:{query.sentiment_engine}:{query.top_n}:{sha1(kw.encode()).hexdigest()[:10]}"
```

### Tarea 14.3 — WebSocket resiliente
**Archivo:** `server_api.py`

- `asyncio.get_running_loop()` en vez de `get_event_loop()`.
- try/except alrededor de `run_pipeline` → `send_json({"error": ...})` y seguir en el bucle (no matar la conexión).
- Timeout del pipeline (ej. 120s) con `asyncio.wait_for`.

### Tarea 14.4 — Límite de concurrencia del pipeline en API
**Archivo:** `server_api.py`

- `asyncio.Semaphore` o `threading.Semaphore` compartida (ej. max 2 pipelines en paralelo).
- Si está saturado: HTTP 503 con `Retry-After`.

### Tarea 14.5 — Tests
- Tras llamar `pipeline.run` (mock scrapers), los sinks de loguru siguen existentes (`len(logger._core.handlers) >= 1` o test de que `data/trendscope.log` sigue creciendo con `setup_logging`).
- Distinto `top_n` → distinta cache key.
- WS con pipeline que lanza excepción → cliente recibe `{"error": ...}`, conexión sigue viva.

### Criterio de aprobación del Bloque 14

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `fix(pipeline): preserva loguru sinks, cache key completa, WS resiliente`

**¿Aprobado para continuar al Bloque 15?**

---

# BLOQUE 15 — SQLite concurrente

**Objetivo:** Cache y watchlist sobreviven a API + scheduler + threads.

**Archivos:**
- `trendscope/core/persistent_cache.py`
- `trendscope/watchlist/store.py`
- `trendscope/tests/test_sqlite_concurrency.py` (nuevo)

### Tarea 15.1 — PRAGMAs (copiar patrón de `xactions/db.py`)
En `_init_db` y/o apertura de conexión de ambos stores:

```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=10000")
conn.execute("PRAGMA synchronous=NORMAL")
```

### Tarea 15.2 — Lazy singleton del cache
**Archivo:** `persistent_cache.py`

Hoy `cache = PersistentCache()` abre DB al importar. Cambiar a lazy:

```python
_cache: PersistentCache | None = None

def get_cache() -> PersistentCache:
    global _cache
    if _cache is None:
        _cache = PersistentCache()
    return _cache
```

`core/cache.py` re-exporta desde el getter. Tests pueden inyectar path tmp.

### Tarea 15.3 — No borrar en `get()`
Dejar el delete-on-read; el `cleanup()` periódico bastará. (Opcional: schedule de cleanup en startup.)

### Tarea 15.4 — Tests
- Dos hilos escribiendo/leyendo en `PersistentCache` del mismo path no lanzan `sqlite3.OperationalError: database is locked` (con busy_timeout).
- Mismo para `WatchlistStore` (history write + list_active read).
- `get_cache()` no abre fichero hasta la primera llamada.

### Criterio de aprobación del Bloque 15

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_sqlite_concurrency.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `fix(db): WAL y busy_timeout en cache y watchlist`

**¿Aprobado para continuar al Bloque 16?**

---

# BLOQUE 16 — Docker endurecido

**Objetivo:** Imagen de producción mínima y compose seguro.

**Archivos:**
- `Dockerfile`
- `docker-compose.yml`
- `.env.example` (API_HOST para Docker)
- `docs/context/ARCHITECTURE.md` (nota de deploy)

### Tarea 16.1 — Multi-stage Dockerfile
Stage build: gcc/g++, instalar deps.  
Stage runtime: solo wheels, sin compiladores, sin `[dev]`, `pip install --no-cache-dir .` (no editable).

```dockerfile
# --- build ---
FROM python:3.11-slim AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY trendscope/ ./trendscope/
RUN pip install --no-cache-dir --prefix=/install .

# --- runtime ---
FROM python:3.11-slim
WORKDIR /app
COPY --from=build /install /usr/local
COPY trendscope/ ./trendscope/
COPY pyproject.toml README.md ./
RUN useradd -m -u 1000 trendscope && mkdir -p /app/data && chown -R trendscope:trendscope /app
USER trendscope
EXPOSE 8000
CMD ["trendscope-api"]
```

(Ajustar a la realidad de deps nativas: si scrapling necesita algo raro, documentar extra stage opcional.)

### Tarea 16.2 — Compose endurecido
```yaml
services:
  trendscope:
    build: .
    ports:
      - "${API_PORT:-8000}:8000"
    env_file:
      - path: .env
        required: false
    environment:
      API_HOST: 0.0.0.0
      DATA_DIR: /app/data
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    mem_limit: 1g
    cpus: "1.5"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
```

> `env_file` required:false evita fallo si no hay `.env` (compose v2.24+). Alternativa documentada: `touch .env`.

### Tarea 16.3 — Documentar override de host
En `.env.example`: comentar que en Docker `API_HOST=0.0.0.0` es intencional y que debe ir con API keys si se expone.

### Tarea 16.4 — Verificación (manual / semi-automatizada)
```bash
docker compose build
docker compose up -d
curl -f http://localhost:8000/health
docker compose ps   # healthy
docker compose down
```

No hay unit tests de Docker; el criterio es build + healthcheck OK. Añadir step opcional en CI (futuro).

### Criterio de aprobación del Bloque 16

- `docker compose build` exitoso.
- Contenedor `healthy`.
- Imagen sin `pytest`/`ruff`/`mypy` (`docker run --rm <img> python -c "import pytest"` debe fallar).
- Commit: `chore(docker): multi-stage, sin dev tools, compose hardening`

**¿Aprobado para continuar al Bloque 17?**

---

# BLOQUE 17 — Rate limit y middleware

**Objetivo:** Rate limiter que no hace memory leak y entiende proxies.

**Archivos:**
- `trendscope/api/middleware.py`
- `trendscope/settings.py` (opcional: `trusted_proxy_ips`)
- `trendscope/tests/test_middleware.py` (extender)

### Tarea 17.1 — Purge de IPs viejas
- Almacenar `dict[str, deque[float]]` o similar.
- En cada request (o cada N requests) borrar keys cuya ventana esté vacía.
- Evitar crecimiento unbounded.

### Tarea 17.2 — Client IP proxy-aware
```python
# Solo si estamos detrás de proxy confiable (config)
xff = request.headers.get("X-Forwarded-For")
if settings.trust_proxy_headers and xff:
    client_ip = xff.split(",")[0].strip()
else:
    client_ip = request.client.host if request.client else "unknown"
```

Default `trust_proxy_headers = False`.

### Tarea 17.3 — Headers de rate limit (UX)
En respuestas 200 y 429:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `Retry-After` en 429

### Tarea 17.4 — Tests
- Ventana deslizante: N requests OK, N+1 → 429, tras avanzar el tiempo → OK de nuevo (inyectar reloj o parchear `time.time`).
- IP vieja se purga (assert `_requests` no crece indefinidamente con IPs rotativas).
- Con `trust_proxy_headers=True`, X-Forwarded-For determina el bucket.
- Headers presentes.

### Criterio de aprobación del Bloque 17

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_middleware.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `fix(api): rate limit sin memory leak, proxy-aware y headers`

**¿Aprobado para continuar al Bloque 18?**

---

# BLOQUE 18 — Rendimiento del pipeline

**Objetivo:** Bajar latencia y CPU sin cambiar el producto.

**Archivos:**
- `trendscope/analyzer/deduplicator.py`
- `trendscope/analyzer/insights.py`
- `trendscope/scrapers/hackernews.py`
- `trendscope/scrapers/amazon.py`
- `trendscope/scrapers/google_trends.py`
- `trendscope/core/pipeline.py`
- `trendscope/core/http.py` (nuevo, Session compartida)
- `trendscope/tests/test_perf_pipeline.py` (nuevo)

### Tarea 18.1 — Session HTTP compartida
**Archivo nuevo:** `trendscope/core/http.py`

```python
import requests
from threading import local

_tls = local()

def get_session() -> requests.Session:
    s = getattr(_tls, "session", None)
    if s is None:
        s = requests.Session()
        s.headers["User-Agent"] = "TrendScope/1.5.0"
        _tls.session = s
    return s
```

Usar en scrapers HTTP (reddit, hn, youtube, google RSS, tiktok) en lugar de `requests.get` sueltos.

### Tarea 18.2 — Deduplicador más barato
- Pre-filtro: solo comparar near-dup si comparten ≥N tokens (ej. 3) o longitud similar.
- O usar `difflib` solo contra los últimos K similares del mismo source, no todo el set.
- Mantener el 72% actual de umbral.

**Test:** con 500 items sintéticos, el dedup tarda < 1s (medición simple con `time.perf_counter`).

### Tarea 18.3 — Insights O(n) aproximado
- Índice invertido palabra→índices de item; co-ocurrencias una sola pasada.

### Tarea 18.4 — HN: fetch paralelo o Algolia batch
- ThreadPool de 8 para los item ids, o una sola query Algolia que traiga el top.

### Tarea 18.5 — Amazon con timeout
- `StealthyFetcher.fetch(..., timeout=45)` si la API lo soporta; si no, `concurrent.futures` con timeout duro de 45s y `[]` al expirar.
- Quitar el `sleep` tras el fetch (inútil).

### Tarea 18.6 — Google Trends: pytrends solo si RSS vacío
- Si RSS ya devolvió items, no llamar a pytrends (ahorra ~3s+ y 429s).

### Tarea 18.7 — Twitter: backoff entre keywords
- `time.sleep(1.5)` entre keywords; abortar serie al primer `RateLimitError`.

### Tarea 18.8 — `max_workers` del pipeline
- Subir a 6 o aislar Amazon en future con timeout propio.

### Tarea 18.9 — Tests de perf/regresión
- Dedup 500 items < 1s.
- HN mock: no hace más de 2 roundtrips (o 1 con Algolia).
- Amazon timeout devuelve `[]` en < 50s (test marcado `slow` o mock del fetcher).

### Criterio de aprobación del Bloque 18

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_perf_pipeline.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `perf(pipeline): sessions, dedup/insights, HN paralelo, timeouts`

**¿Aprobado para continuar al Bloque 19?**

---

# BLOQUE 19 — Config coherente y geo dinámico

**Objetivo:** Una sola fuente de verdad de config; keywords que respetan geo y año.

**Archivos:**
- `trendscope/settings.py`
- `trendscope/config.py`
- `trendscope/core/query.py`
- `.env.example`
- `trendscope/tests/test_query_geo.py` (nuevo)

### Tarea 19.1 — Alinear Ollama
- `.env.example`: `OLLAMA_ENABLED=false` (como settings).
- O settings default `true` si prefieres el example — **elegir uno y documentarlo**. Decisión: default `false` (opt-in, menos ruido en instalaciones nuevas).

### Tarea 19.2 — Keywords de free topic sin hardcode
**Archivo:** `query.py`

```python
from datetime import datetime

@property
def keywords(self) -> list[str]:
    if self.mode == "category" and self.category in CATEGORIES:
        return CATEGORIES[self.category]
    if self.mode == "free" and self.free_topic:
        t = self.free_topic.strip()
        year = datetime.now().year
        return [t, f"{t} {self.geo}", f"{t} {year}", f"tendencias {t}"]
    return []
```

### Tarea 19.3 — `config.py` como proxy vivo (opcional mínimo)
No reescribir todo: como mínimo, los scrapers que importan `TWITTER_AUTH_TOKEN` etc. pueden seguir. Documentar en ARCHITECTURE que `settings` es canónico y `config.py` es re-export legacy.

Si hay tiempo: convertir constantes críticas a properties que lean `settings.*`.

### Tarea 19.4 — Completar `.env.example`
Añadir: `DATA_DIR`, `OPENROUTER_SITE_URL`, `OPENROUTER_SITE_NAME`, `TRUST_PROXY_HEADERS`.

### Tarea 19.5 — Typo `CACHET_TTL_SECONDS` en config (si existe)
Renombrar a `CACHE_TTL_SECONDS` y actualizar usos.

### Tarea 19.6 — Tests
- `TrendQuery(geo="MX", free_topic="café")` → keywords incluyen `"café MX"`, no `"café Colombia"` hardcodeado.
- Año = `datetime.now().year`.
- `.env.example` contiene las claves de settings (test de cobertura de docs o checklist manual).

### Criterio de aprobación del Bloque 19

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_query_geo.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `fix(config): geo/año dinámicos y defaults coherentes`

**¿Aprobado para continuar al Bloque 20?**

---

# BLOQUE 20 — Tests de regresión e integración

**Objetivo:** Que un bug como el de sentimiento no vuelva a pasar desapercibido. Aislamiento de tests.

**Archivos:**
- `trendscope/tests/test_pipeline_unit.py` (nuevo)
- `trendscope/tests/conftest.py` (nuevo o extender)
- `trendscope/server_api.py` (app factory si hace falta)
- `trendscope/tests/test_watchlist_api.py` (aislar DB)
- `.github/workflows/tests.yml`

### Tarea 20.1 — App factory / evitar side effects al import
- `server_api.py`: store y scheduler se crean en `create_app()` o en startup, no a nivel de módulo si rompe tests.
- Mínimo viable: fixtures de pytest que parcheen `get_store()` a tmp_path.

### Tarea 20.2 — Tests de pipeline con scrapers mockeados
```python
def test_pipeline_end_to_end_mocked(monkeypatch, tmp_path):
    # mockear cada scraper.run -> items sintéticos
    # mockear cache path a tmp_path
    payload, report = run_pipeline(query)
    assert payload["top_trends"]
    assert payload["meta"]["sentiment_summary"]["engine"] != "failed"
```

### Tarea 20.3 — Test de alineación de sentimiento ya cubierto (B1)
Asegurar que `test_sentiment_imports.py` sigue en CI.

### Tarea 20.4 — Tests de watchlist aislados
- DB en `tmp_path`.
- No tocar `data/watchlist.db` del dev.

### Tarea 20.5 — Tests de cache con reloj inyectado
- Eliminar `time.sleep(1.1)` de TTL tests → `freezegun` o `monkeypatch` de `time.time`.

### Tarea 20.6 — CI más completa
`.github/workflows/tests.yml`:
- pytest (ya)
- `ruff check trendscope`
- opcional: `mypy trendscope` (puede empezar en non-blocking)

Alinear matrix: `requires-python >=3.10` ⇒ añadir 3.10 o subir floor a 3.11.

### Criterio de aprobación del Bloque 20

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
.venv\Scripts\python.exe -m ruff check trendscope
```

- Suite verde dos veces seguidas (sin side effects).
- Commit: `test: pipeline mockeado, aislamiento de DB, CI con ruff`

**¿Aprobado para continuar al Bloque 21?**

---

# BLOQUE 21 — Alertas de watchlist (webhooks)

**Objetivo:** De “monitoreo pasivo” a “me avisa cuando pasa algo”. Primer diferenciador de producto P1.

**Archivos:**
- `trendscope/watchlist/alerts.py` (nuevo)
- `trendscope/watchlist/store.py` (columna opcional `alert_webhook`, `alert_min_score`)
- `trendscope/watchlist/scheduler.py` (evaluar alertas tras cada run)
- `trendscope/server_api.py` (campos en POST/PUT watchlist)
- `trendscope/settings.py`
- `trendscope/tests/test_alerts.py` (nuevo)

### Tarea 21.1 — Modelo de reglas
```python
@dataclass
class AlertRule:
    webhook_url: str | None = None
    min_score: float | None = None          # avisar si top_score >= min_score
    sentiment_flip: bool = False            # avisar si overall pasa de + a - o viceversa
    min_volume: int | None = None
```

### Tarea 21.2 — Evaluador
Tras `save_history(payload)`:
1. Comparar con la historia previa del mismo topic (último registro).
2. Si se cumple alguna regla → POST JSON al webhook (timeout 5s, log si falla, nunca romper el job).

Payload del webhook:
```json
{
  "topic": "...",
  "geo": "CO",
  "top_score": 87.2,
  "previous_score": 41.0,
  "sentiment": "positive",
  "triggered_by": ["min_score"],
  "analyzed_at": "..."
}
```

### Tarea 21.3 — Config
- `ALERTS_ENABLED=true`
- `ALERTS_TIMEOUT_SECONDS=5`
- Allowlist opcional de hosts de webhook (SSRF: no permitir `169.254.169.254` etc. — validar esquema http/https y bloquear IPs link-local/metadata).

### Tarea 21.4 — Migración SQLite
`ALTER TABLE watchlist ADD COLUMN alert_webhook TEXT` (IF NOT EXISTS pattern / try-except OperationalError).

### Tarea 21.5 — Tests
- Score cruza umbral → webhook mock (`responses`/`respx`) llamado una vez.
- Score no cruza → no llama.
- Webhook caído → job no lanza excepción.
- SSRF: webhook `http://169.254.169.254/` rechazado.

### Criterio de aprobación del Bloque 21

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_alerts.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `feat(alerts): webhooks de watchlist con umbrales y anti-SSRF`

**¿Aprobado para continuar al Bloque 22?**

---

# BLOQUE 22 — Cola de trabajos asíncrona

**Objetivo:** `/trends`, `/narrate`, `/export/*` y `watchlist/{id}/run` no bloquean minutos.

**Decisión de stack (mínimo viable sin Redis):**  
Fase A (este bloque): cola en-proceso con `BackgroundTasks` / `ThreadPoolExecutor` + estado en SQLite (`jobs` table).  
Fase B (bloque futuro o P2): Redis + RQ/arq si hay multi-worker.

**Archivos:**
- `trendscope/jobs/store.py`, `trendscope/jobs/runner.py` (nuevos)
- `trendscope/server_api.py`
- `trendscope/tests/test_jobs.py` (nuevo)

### Tarea 22.1 — Tabla `jobs`
```
id, kind, topic, status(pending|running|done|error),
created_at, started_at, finished_at, result_path, error
```

### Tarea 22.2 — Endpoints
- `GET /trends?topic=X&async=true` → `202 {job_id}`
- `GET /jobs/{id}`
- `POST /watchlist/{id}/run` → `202 {job_id}` en vez de sync minutes
- WS: push `{"type":"job_done", "job_id": ...}` cuando termine (opcional en este bloque)

### Tarea 22.3 — Tests
- `async=true` devuelve 202 y job pasa a done (con scrapers mock).
- Job en error → status=error y `error` relleno.
- Sync path sigue funcionando (compatibilidad).

### Criterio de aprobación del Bloque 22

```cmd
.venv\Scripts\python.exe -m pytest trendscope/tests/test_jobs.py -v
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
```

- Commit: `feat(jobs): análisis asíncronos con job_id`

---

# BLOQUE 23 — Paridad MCP ↔ REST

**Objetivo:** El agente MCP pueda hacer lo mismo que la API: watchlist, history, narrate, doctor, compare.

**Archivos:**
- `trendscope/server_mcp.py`
- `trendscope/tests/test_mcp_tools.py` (nuevo)

### Tareas
- Tools: `analyze_topic`, `get_narrative`, `compare_topics`, `doctor`, `watchlist_add`, `watchlist_list`, `watchlist_run`, `history_get`.
- Reutilizar las mismas funciones internas que la API (no duplicar lógica).
- Documentar en `SKILL.md`.

### Criterio de aprobación
Tests de cada tool con mocks. Commit: `feat(mcp): paridad de tools con REST`

---

# BLOQUE 24 — Observabilidad

**Objetivo:** Saber qué falla y cuánto tarda sin abrir logs a mano.

### Tareas
1. `source_errors` en `payload.meta`: `{ "reddit": "403", "amazon": "timeout" }`.
2. Tabla métricas ligera o counters en `/metrics` (prometheus-client opcional / texto simple).
3. Retención de `history`: job que borra payloads > N días (ej. 90) dejando el resumen.
4. `request_id` en logs de API.

### Criterio de aprobación
- `/trends` incluye `meta.source_errors`.
- Test de retención.
- Commit: `feat(ops): source_errors, métricas y retención de history`

---

# BLOQUE 25 — Forecasting básico (P2)

### Tareas
1. Tabla time-series compacta: `topic, geo, analyzed_at, top_score, volume, pos/neg/neu`.
2. EMA + velocity (Δscore / Δt) por topic.
3. Detección de breakout: z-score > 2 sobre la serie.
4. Campo en insights: `"forecast": {"trend": "rising", "velocity": 3.2, "breakout": true}`.

### Criterio de aprobación
Tests con serie sintética. Commit: `feat(ml): EMA, velocity y breakout sobre history`

---

# BLOQUE 26 — Multi-tenant y auth de verdad (P2)

### Tareas
1. Modelo `org` + `api_key` con scopes (`trends:read`, `watchlist:write`).
2. JWT (o Auth0/Clerk/Supabase) para dashboard.
3. `org_id` en watchlist y history.
4. Rate limit por key/org, no solo por IP.
5. Billing stub (Stripe) fuera de este bloque salvo que se pida.

### Criterio de aprobación
Tests de scopes y aislamiento entre orgs. Commit: `feat(auth): multi-tenant y scopes`

---

## Orden de ejecución recomendado

```
FASE 1 — Hardening (obligatorio antes de exponer o escalar)
  11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20
        ↑
   ~1–2 sesiones de trabajo concentradas

FASE 2 — Producto
  21 (alertas) → 22 (jobs) → 23 (MCP) → 24 (observabilidad)

FASE 3 — Plataforma
  25 (forecasting) → 26 (multi-tenant)
```

## Definición de Done global (Fase 1)

- [ ] Sentimiento real (no `failed`) en pipeline y doctor
- [ ] Sin path traversal ni glob injection
- [ ] Auth en HTTP y WS cuando está activada; defaults no exponen la API
- [ ] Logging estable tras N pipelines
- [ ] SQLite con WAL
- [ ] Docker multi-stage + healthcheck
- [ ] Rate limit sin leak
- [ ] Pipeline más rápido (dedup/insights/HN/timeouts)
- [ ] Geo/año dinámicos
- [ ] Suite de tests de regresión en CI (pytest + ruff)

## Cómo continuar sin perder contexto

1. Abrir este archivo y ver el primer bloque `[ ]`.
2. Leer solo ese bloque (objetivo, tareas, criterio).
3. Implementar tarea a tarea; no empezar la siguiente hasta verde la anterior.
4. Ejecutar la suite completa del bloque.
5. Actualizar `docs/context/CHANGELOG.md` con la versión del bloque.
6. Marcar `[x]` y commit.
7. Pedir APROBADO (o continuar si el usuario autorizó todos).
8. Avanzar al siguiente bloque.

**Ficheros de contexto a re-leer si se pierde el hilo:**
- `docs/context/PROJECT.md` — qué es TrendScope
- `docs/context/ARCHITECTURE.md` — estructura
- `docs/context/WORKING_STYLE.md` — convenciones
- `docs/context/AGENTS.md` — reglas para modelos
- `Implementation_Plan/TRENDSCOPE_V2_PLAN.md` — este plan
- `Implementation_Plan/TRENDSCOPE_EVOLUTION_PLAN.md` — v1 (histórico, 0–10 done)

---

## Fuera de alcance de este plan (explícito)

- Migración a Postgres (se hará cuando el bloque de jobs/multi-replica lo exija; hoy WAL + single-node basta).
- Redis/Celery (Fase B del bloque 22 o plan v3).
- Nuevos scrapers (LinkedIn, Bluesky, etc.) — solo tras Fase 1.
- Rediseño visual del dashboard.
- Marketplace / billing.

---

*Plan generado a partir de la auditoría 2026-02-12 sobre `7e3dbf5`. Actualizar el estado de bloques al completar cada uno.*
