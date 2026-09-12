# TrendScope V5 — Plan de Sentimiento Avanzado

> **Versión:** 5.0.0  
> **Fecha:** 2026-02-12  
> **Base:** v1.8.x / fix de idioma (`34dd794`)  
> **Objetivo:** Sentimiento más útil para trend intel: stance hacia el tema, batch rápido, calibración, cache y agregados por fuente.

---

## Filosofía

- Bloque → tests en verde → commit → siguiente (auto-aprobación).
- Sin APIs de pago. Todo local (pysentimiento + heurística).
- YAGNI: solo lo que mejora la lectura del dashboard/API.

---

## Resumen

| Bloque | Nombre | Objetivo |
|--------|--------|----------|
| 45 | Stance hacia el tema | ¿A favor / en contra / mixto respecto al topic? |
| 46 | Batch + timeout | Analizar 100+ textos sin colgar el pipeline |
| 47 | Calibración de score | Mapear probas → score usable y consistente |
| 48 | Cache de sentimiento | Evitar re-analizar textos idénticos en 5 min |
| 49 | Agregado por fuente | `sentiment_by_source` en insights + payload |
| 50 | Docs (EN) | README: sección sentiment |

---

## Estado

- [ ] 45 — Stance hacia el tema
- [ ] 46 — Batch + timeout
- [ ] 47 — Calibración de score
- [ ] 48 — Cache de sentimiento
- [ ] 49 — Agregado por fuente
- [ ] 50 — Docs (EN)

---

# BLOQUE 45 — Stance hacia el tema

**Objetivo:** Para cada item, `stance`: `support` | `against` | `mixed` | `unknown` respecto al topic.

### Tareas
1. `sentiment/stance.py` — heurística léxica ES/EN alrededor del topic (verbos/adj de apoyo/rechazo + puntuación de sentimiento del texto).
2. Enriquecer items con `stance` y `stance_confidence`.
3. Agregar en `meta`: `stance_summary` (support/against/mixed/unknown counts).
4. Tests unitarios de frases típicas CO/ES.

### Criterio
- Tests verdes.
- Commit: `feat(sentiment): stance hacia el tema`

---

# BLOQUE 46 — Batch + timeout

### Tareas
1. Procesar pysentimiento en batches de N (ej. 32).
2. Timeout global por batch (ej. 20s) → fallback keywords si se pasa.
3. Tests con mock del analyzer.

### Criterio
- Tests verdes.
- Commit: `perf(sentiment): batch y timeout`

---

# BLOQUE 47 — Calibración de score

### Tareas
1. `calibrate_score(label, probas)` → 0–1 consistente (NEU cerca de 0.5).
2. Usar en local_engine (pysentimiento y fallback).
3. Tests de rango y monotonicidad.

### Criterio
- Tests verdes.
- Commit: `feat(sentiment): calibración de score`

---

# BLOQUE 48 — Cache de sentimiento

### Tareas
1. LRU simple en memoria (hash del texto+engine), TTL ~10 min, max 2k entries.
2. Tests de hit/miss.

### Criterio
- Tests verdes.
- Commit: `perf(sentiment): cache LRU`

---

# BLOQUE 49 — Agregado por fuente

### Tareas
1. `insights`: `sentiment_by_source` y `stance_by_source`.
2. Incluir en payload meta.
3. Tests.

### Criterio
- Tests verdes.
- Commit: `feat(insights): sentimiento y stance por fuente`

---

# BLOQUE 50 — Docs

### Tareas
1. README (EN): stance, score, engines.
2. Commit: `docs: sentiment stance and calibration`

---

## Cómo probar al final

```bash
curl "http://localhost:8000/trends?topic=abelardo+de+la+espriella"
# meta.sentiment_summary, meta.stance_summary, per-item stance
```
