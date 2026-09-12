# TrendScope V3 — Plan de Plataforma (siguiente nivel)

> **Versión:** 3.0.0  
> **Fecha:** 2026-02-12  
> **Base:** v1.7.0 / plan V2 completo (`4cd7054`)  
> **Planes anteriores:**  
> - `TRENDSCOPE_EVOLUTION_PLAN.md` (bloques 0–10)  
> - `TRENDSCOPE_V2_PLAN.md` (bloques 11–26)

---

## Filosofía

- Un bloque a la vez. **Auto-aprobación**: si la suite del bloque está en verde, se commita y se avanza.
- Si un test falla, se corrige y se re-ejecuta **antes** de avanzar.
- TDD cuando sea posible.
- Commits: `feat:` / `fix:` / `sec:` / `perf:` / `test:` / `chore:` / `docs:`.
- Actualizar checklist + CHANGELOG al cerrar cada bloque.
- Sin servicios externos obligatorios: Redis/Postgres/JWT son **opcionales** con fallback local.

---

## Resumen de bloques

| Bloque | Nombre | Objetivo | Impacto |
|--------|--------|----------|---------|
| 27 | App factory sin side-effects | `create_app()`, tests aislados, arranque limpio | Alto |
| 28 | Aislamiento por org | `org_id` en watchlist/history/jobs | Alto |
| 29 | Rate limit por org + key | Cuotas por tenant, no solo IP | Alto |
| 30 | Source health runtime | Score de fiabilidad por fuente en `/trends` y routing | Alto |
| 31 | Dashboard endurecido | Auth del dashboard, CSP estricto, Chart.js local | Medio |
| 32 | Modelos tipados de payload | TypedDict/pydantic para trends y meta | Medio |
| 33 | SSE / progreso de jobs | `GET /jobs/{id}/events` (Server-Sent Events) | Medio |
| 34 | Adaptador de datos GDELT | Fuente gratis adicional (news global) | Alto |
| 35 | Digest de exportaciones | Programar envío de resumen a webhook/Slack | Medio |
| 36 | Interfaz repository Postgres-ready | Abstract store + driver SQLite (sin migrar aún) | Medio |
| 37 | Observabilidad OpenAPI mejorada | Ejemplos, errores estándar, versionado de API | Bajo |
| 38 | Benchmarks y budgets de latencia | Guardrails de perf en CI (marca slow) | Bajo |

**Fase A (plataforma core):** 27–30  
**Fase B (producto/expansión):** 31–35  
**Fase C (infra madura):** 36–38

---

## Estado

- [x] Bloque 27 — App factory sin side-effects
- [x] Bloque 28 — Aislamiento por org
- [x] Bloque 29 — Rate limit por org + key
- [x] Bloque 30 — Source health runtime
- [x] Bloque 31 — Dashboard endurecido
- [x] Bloque 32 — Modelos tipados de payload
- [x] Bloque 33 — SSE / progreso de jobs
- [x] Bloque 34 — Adaptador de datos GDELT
- [x] Bloque 35 — Digest de exportaciones
- [x] Bloque 36 — Interfaz repository Postgres-ready
- [x] Bloque 37 — Observabilidad OpenAPI mejorada
- [x] Bloque 38 — Benchmarks y budgets de latencia

---

# BLOQUE 27 — App factory sin side-effects

**Objetivo:** `server_api.py` deja de crear store/scheduler al importar. `create_app()` para tests y prod.

**Archivos:**
- `trendscope/server_api.py` (o `trendscope/api/app.py`)
- `trendscope/tests/conftest.py`
- tests existentes que importan `app`

### Tareas
1. Extraer `create_app() -> FastAPI` que:
   - Crea store/scheduler/jobs por instancia (inyectables).
   - Registra middlewares y rutas.
   - Usa lifespan en vez de `@app.on_event`.
2. `app = create_app()` al final solo si `__name__` entrypoint o para compat.
3. Tests usan `create_app()` con stores en `tmp_path`.
4. Migrar tests de API a factory (watchlist, websocket, jobs, api_security).

### Criterio
- `pytest trendscope/tests/` en verde.
- Importar `trendscope.server_api` no abre `data/*.db` (test).
- Commit: `refactor(api): create_app() sin side-effects al importar`

---

# BLOQUE 28 — Aislamiento por org

**Objetivo:** Cada API key/org ve solo sus datos de watchlist/history/jobs.

**Archivos:**
- `trendscope/watchlist/store.py`
- `trendscope/jobs/store.py`
- `trendscope/server_api.py`
- `trendscope/tests/test_org_isolation.py`

### Tareas
1. Columna `org_id TEXT NOT NULL DEFAULT 'default'` en watchlist, history, jobs.
2. Endpoints leen `request.state.org_id` (default `"default"` si no hay auth).
3. Filtros: `list`, `get`, `history`, `jobs` por org.
4. Items creados con el org del caller.
5. Migración ALTER TABLE + tests de aislamiento (orgA no ve orgB).

### Criterio
- Tests de aislamiento en verde.
- Commit: `feat(tenant): org_id en watchlist, history y jobs`

---

# BLOQUE 29 — Rate limit por org + key

**Objetivo:** Cuotas por tenant además de por IP.

**Archivos:**
- `trendscope/api/middleware.py`
- `trendscope/settings.py` (`org_rate_limit`)
- `trendscope/tests/test_org_rate_limit.py`

### Tareas
1. Bucket por `org:{org_id}` además de IP.
2. Si no hay org (sin auth), solo IP.
3. Headers reflejan el límite aplicado.
4. Tests: org A no consume cuota de org B.

### Criterio
- Tests en verde.
- Commit: `feat(api): rate limit por org además de IP`

---

# BLOQUE 30 — Source health runtime

**Objetivo:** Cada request reporta salud de fuentes; se puede degradar la peor fuente.

**Archivos:**
- `trendscope/core/source_health.py`
- `trendscope/core/pipeline.py`
- `trendscope/tests/test_source_health.py`

### Tareas
1. Registro en memoria: éxitos/fallos/latencia por fuente (EMA).
2. `payload.meta.source_health` = score 0–1 por fuente.
3. Si score < 0.2 → skip (ahorrar tiempo) con flag config `SOURCE_HEALTH_SKIP=true`.
4. Tests con scrapers mockeados.

### Criterio
- Tests en verde.
- Commit: `feat(pipeline): source health runtime y skip de fuentes muertas`

---

# BLOQUE 31 — Dashboard endurecido

**Objetivo:** Dashboard usable con auth y CSP sin CDN si es posible.

### Tareas
1. Servir Chart.js desde `/static/chart.umd.min.js` (vendor local) o inline si tamaño lo permite.
2. CSP: `script-src 'self'` sin CDN.
3. Si `api_key_required`, dashboard pide key y la envía en fetch/WS.
4. Tests estáticos del CSP + flujo de key.

### Criterio
- Tests en verde.
- Commit: `sec(dashboard): CSP estricto y auth de API key`

---

# BLOQUE 32 — Modelos tipados de payload

### Tareas
1. `trendscope/models/payload.py` con TypedDict o pydantic v2 para TrendItem, Meta, Payload.
2. Usar en json_exporter y endpoints donde sea barato.
3. Tests de validación mínima.

### Criterio
- Tests en verde.
- Commit: `feat(models): payload tipado para export y API`

---

# BLOQUE 33 — SSE / progreso de jobs

### Tareas
1. `GET /jobs/{id}/events` con `text/event-stream`.
2. Emite `status` cada 0.5s hasta done/error (poll DB).
3. Test con job mock.

### Criterio
- Tests en verde.
- Commit: `feat(jobs): SSE de progreso`

---

# BLOQUE 34 — Adaptador GDELT

### Tareas
1. `scrapers/gdelt.py` usando GDELT DOC API (gratis, sin key).
2. Registrar en SOURCES.
3. Tests mock de parseo + doctor check.

### Criterio
- Tests en verde.
- Commit: `feat(scraper): GDELT news como fuente adicional`

---

# BLOQUE 35 — Digest de exportaciones

### Tareas
1. Watch item con `digest_webhook` + `digest_cron` (o interval diario).
2. Tras N runs o diario, POST resumen (top 10 + sentimiento + forecast).
3. Reutilizar alerts anti-SSRF.

### Criterio
- Tests en verde.
- Commit: `feat(digest): envío periódico de resumen a webhook`

---

# BLOQUE 36 — Repository Postgres-ready

### Tareas
1. `WatchlistRepository` ABC con los métodos actuales.
2. `SqliteWatchlistRepository` implementa.
3. `get_store()` devuelve la implementación; documentar cómo colgar Postgres.
4. Tests de interfaz con la implementación SQLite.

### Criterio
- Tests en verde.
- Commit: `refactor(store): interfaz repository lista para Postgres`

---

# BLOQUE 37 — OpenAPI mejorada

### Tareas
1. `responses` en endpoints principales (404, 429, 401).
2. Tags y summary consistentes.
3. Test de `/openapi.json` contiene paths nuevos.

### Criterio
- Tests en verde.
- Commit: `docs(api): OpenAPI con tags, summaries y errores`

---

# BLOQUE 38 — Benchmarks de latencia

### Tareas
1. Tests marcados `@pytest.mark.slow` midiendo dedup 5k, insights 1k, pipeline mock.
2. Budgets: dedup 5k < 3s, insights 1k < 1s.
3. CI job opcional (no bloqueante) o solo local.

### Criterio
- Tests en verde (los no-slow siempre).
- Commit: `test(perf): budgets de latencia con marca slow`

---

## Criterio de Done global V3

- [ ] App factory sin side-effects
- [ ] Multi-tenant real (org en datos + rate limit)
- [ ] Source health visible y usable
- [ ] Dashboard con CSP/auth
- [ ] Payload tipado
- [ ] Jobs con SSE
- [ ] +1 fuente (GDELT)
- [ ] Digest periódico
- [ ] Repository interface
- [ ] OpenAPI y perf budgets

## Cómo continuar

1. Primer bloque `[ ]` de este archivo.
2. Implementar → tests → si verde: checklist `[x]` + CHANGELOG + commit.
3. Siguiente bloque.
4. Push al final de la fase o cuando el usuario lo pida.

---

*Plan V3 generado sobre v1.7.0. Actualizar estado al completar cada bloque.*
