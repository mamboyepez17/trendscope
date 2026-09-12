# TrendScope V4 — Plan de Producto Ejecutable (demo & ops)

> **Versión:** 4.0.0  
> **Fecha:** 2026-02-12  
> **Base:** v1.8.x / plan V3 completo (`dbcae01`+)  
> **Objetivo:** Que TrendScope se pueda *probar de verdad* — doctor, smoke, demo offline, CLI de ops, y documentación final.

---

## Filosofía

- Bloque → tests en verde → commit → siguiente (auto-aprobación).
- Sin servicios externos obligatorios. El live smoke usa la red solo si el usuario lo pide.
- Commits: `feat:` / `fix:` / `docs:` / `test:` / `chore:`.

---

## Resumen

| Bloque | Nombre | Objetivo |
|--------|--------|----------|
| 39 | CLI `doctor` + `smoke` | Comandos de diagnóstico y smoke test de un vistazo |
| 40 | Demo offline | Dataset sembrado para ver pipeline + dashboard sin red |
| 41 | Validación de config al arrancar | Avisos claros de `.env` incompleto / API expuesta |
| 42 | Informe de smoke | `GET /smoke` + resumen legible para el usuario |
| 43 | Live smoke (opcional) | Ejecutar pipeline real con `.env` del usuario, reporte |
| 44 | README final + guía de prueba | Cómo probarlo en 5 minutos (EN) |

---

## Estado

- [x] 39 — CLI doctor + smoke
- [x] 40 — Demo offline
- [x] 41 — Validación de config
- [x] 42 — Informe de smoke
- [x] 43 — Live smoke
- [ ] 44 — README + guía de prueba

---

# BLOQUE 39 — CLI doctor + smoke

**Objetivo:** `trendscope doctor` y `trendscope smoke` desde consola.

### Tareas
1. Añadir entry point `trendscope` CLI con subcomandos o flags: `--doctor`, `--smoke`.
2. `doctor` imprime el reporte con rich.
3. `smoke` ejecuta pipeline mockeado/ligero (sin depender de todas las fuentes) y reporta OK/FAIL.
4. Tests: import de funciones, output smoke con scrapers mock.

### Criterio
- `pytest` verde.
- Commit: `feat(cli): doctor y smoke`

---

# BLOQUE 40 — Demo offline

**Objetivo:** Datos de ejemplo para ver dashboard/pipeline sin scraping real.

### Tareas
1. `trendscope/demo/seed.py` — payload de ejemplo realista (varios sources, scores, sentimiento).
2. Endpoint `GET /demo` carga el payload y lo sirve (o lo mete en cache).
3. Test del endpoint.

### Criterio
- Tests verdes.
- Commit: `feat(demo): payload de ejemplo offline`

---

# BLOQUE 41 — Validación de config

**Objetivo:** Al arrancar la API, avisos claros si falta config o la API está expuesta sin keys.

### Tareas
1. `validate_settings()` → lista de warnings/errors (host expuesto, keys vacías, etc.).
2. Llamar en lifespan de `create_app`.
3. Tests.

### Criterio
- Tests verdes.
- Commit: `feat(ops): validación de settings al arrancar`

---

# BLOQUE 42 — Informe de smoke

**Objetivo:** Endpoint que devuelva un resumen ejecutable: health, fuentes, config, demo.

### Tareas
1. `GET /smoke` → `{status, version, sources, doctor_summary, demo_ok, warnings}`
2. Test con doctor mockeado.

### Criterio
- Tests verdes.
- Commit: `feat(api): endpoint /smoke`

---

# BLOQUE 43 — Live smoke

**Objetivo:** Comando que ejecute un pipeline real limitado (1 keyword, fuentes ligeras) y guarde reporte.

### Tareas
1. `trendscope smoke --live` o `run_live_smoke()` que fuerza fuentes ligeras (HN, GDELT, Google RSS) y top_n pequeño.
2. No publica nada; solo lee. Documentar que Twitter solo se usa si hay cookies.
3. Test con scrapers mockeados del path live.

### Criterio
- Tests verdes.
- Commit: `feat(smoke): live smoke limitado`

---

# BLOQUE 44 — README + guía de prueba

**Objetivo:** Sección “Try it in 5 minutes” en inglés con doctor, demo, smoke y dashboard.

### Tareas
1. Actualizar README (EN).
2. Commit: `docs: guía de prueba en 5 minutos`

---

## Cómo probar al final (resumen para el usuario)

```bash
cd trendscope
# venv + install (ver README)
trendscope --doctor
trendscope --smoke
trendscope-api
# → http://localhost:8000/dashboard
# → http://localhost:8000/demo
# → http://localhost:8000/smoke
# live (opcional, usa .env):
trendscope --smoke --live
```
