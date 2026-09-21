# TrendScope V6 — Comment Intelligence + Dashboard UI

> **Versión:** 6.0.0  
> **Fecha:** 2026-02-12  
> **Base:** v1.8.x / `5edbb04` (parked) → **re-activado**  
> **Ejecución:** bloques con tests en verde → auto-aprobación del agente → commit.  
> **Cierre:** aviso al usuario para prueba manual / visto bueno final.

---

## Filosofía

- Un bloque a la vez. Suite verde = bloque aprobado = commit = siguiente.
- Comentarios = emoción real; el post solo es el contexto.
- IA: solo respuesta visible (nunca reasoning).
- UI: light + dark, gráficos menos “plásticos”, estilo editorial/dinámico.
- Código/comentarios en inglés; este plan en español.

---

## Resumen de bloques

| Bloque | Nombre | Tests |
|--------|--------|-------|
| 47 | Reddit comments mapper (JSON público, sin API de paga) | mock HTTP + parse |
| 48 | X replies via xactions | mock search |
| 49 | Conversation analyzer (acceptance, toxicity, mood + emoji) | unit cases ES/EN |
| 50 | API `/conversation` + `/discover` (Trends global/US/CO) | TestClient |
| 51 | Dashboard UI: theme light/dark + gráficos + card Conversation/Mood | static + endpoint |
| 52 | Narrador DeepSeek sobre conversación (solo respuesta) | dispatch |
| 53 | README EN + changelog + status activo | docs |

---

## Estado

- [x] 47 — Reddit comments mapper
- [x] 48 — X replies
- [x] 49 — Conversation analyzer + mood
- [x] 50 — API conversation + discover
- [x] 51 — Dashboard UI refresh
- [x] 52 — Narrador conversación
- [x] 53 — Docs / status

**Suite:** 327 tests en verde. Esperando prueba manual del usuario.

---

## Detalle de bloques

### 47 — Reddit comments
- `trendscope/scrapers/reddit_comments.py`
- `search_public_posts(query)` + `fetch_comments(post_id)` vía `.json`
- UA + backoff; nunca levanta excepción al pipeline
- Tests: parse de fixtures JSON mock

### 48 — X replies
- `trendscope/scrapers/x_replies.py`
- Para tweets top del tema, obtener replies (xactions si hay cookies)
- Tests: parse/mock

### 49 — Conversation analyzer
- `trendscope/analyzer/conversation.py`
- Por comentario: stance + sentimiento + toxicity léxica ES/EN
- Salida: acceptance_score, mood (`calm|supportive|mixed|hot|toxic|polarized`) + emoji
- Tests de casos representativos

### 50 — API
- `GET /conversation?topic=` — posts + comments + summary mood
- `GET /discover?geo=GLOBAL|US|CO` — temas de Trends
- Tests con stores/HTTP mock

### 51 — Dashboard
- Toggle light/dark (CSS variables, localStorage)
- Paleta más editorial: no solo neón cyan
- Chart.js: tooltips suaves, grid sutil, sin gradientes plásticos
- Cards: Conversation (barras support/against) + Mood grande con emoji
- Tests estáticos: existe theme toggle, no CDN, CSS light

### 52 — Narrador conversación
- Prompt ES: analiza acceptance/mood/frases; nunca pedir “chain of thought”
- DeepSeek solo `content`
- Tests mock

### 53 — Docs
- README EN: conversation, discover, light mode
- Quitar status parked
- CHANGELOG

---

## Criterio final (antes de avisar al usuario)

- `pytest` completo en verde
- Commits empujados a `origin/main`
- Instrucciones de prueba manual en el aviso
