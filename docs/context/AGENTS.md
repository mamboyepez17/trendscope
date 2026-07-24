# TrendScope — Guía para Modelos de IA

## Para cualquier modelo que trabaje aquí
Opus 4, MiMo, DeepSeek, Haiku, o cualquier otro.
Leer este archivo ANTES de tocar cualquier código.

## Checklist obligatorio al abrir el proyecto
1. Leer PROJECT.md — qué es y para qué sirve
2. Leer ARCHITECTURE.md — estructura y flujo de datos
3. Leer CHANGELOG.md — qué está hecho y qué falta
4. Leer WORKING_STYLE.md — reglas y convenciones
5. Identificar en qué bloque trabajar
6. Nunca asumir — si no está claro, revisar los .context/

## Sistema de bloques — OBLIGATORIO respetar

| Bloque | Contenido | Criterio de aprobación |
|---|---|---|
| 0 | .context/ | 5 archivos existen con contenido |
| 1 | Base: estructura, config, query | Imports limpios, .env carga |
| 2 | 5 scrapers | Cada uno devuelve list[dict] |
| 3 | Scorer + sentimiento | Items entran, salen puntuados |
| 4 | JSON + Markdown output | Archivos generados en data/ |
| 5 | Pipeline + CLI | python main.py corre end-to-end |
| 6 | API REST + MCP | Endpoints y tools responden |
| 7 | GitHub | Repo limpio, sin archivos privados |

**NUNCA avanzar al siguiente bloque sin aprobación del usuario.**

## Reglas de código
- Python 3.10+ únicamente — sin JavaScript, Node, npm
- `pip install --break-system-packages` en Linux
- Credenciales SIEMPRE en .env, nunca en código
- Scrapling para todo scraping HTTP y browser
- loguru para logs, nunca print() en producción
- Type hints en todas las funciones
- Cada scraper: try/except propio, retorna [] si falla

## Reglas de archivos
- `.env` → nunca al repo
- `data/` → nunca al repo
- `.context/` → nunca al repo
- Solo `.env.example` va al repo como template

## Al completar cada bloque
1. Verificar criterio de aprobación del bloque
2. Actualizar CHANGELOG.md con lo que se hizo
3. Reportar al usuario con el mensaje estándar
4. Esperar APROBADO antes de continuar

## Mensaje estándar de completitud

```
BLOQUE X COMPLETADO

[lista de lo que se creó/hizo]

¿Aprobado para continuar al Bloque X+1?
```

## Prioridades de debugging

Cuando algo falla, diagnosticar en este orden:

1. **Credenciales** — ¿.env existe? ¿las variables están seteadas?
2. **Conectividad** — ¿el sitio responde? ¿hay bloqueo geo?
3. **Rate limit** — ¿se excedió el límite? Revisar logs de retry
4. **Selector roto** — ¿el sitio cambió su HTML? (Scrapling debería adaptarse)
5. **Dependencia** — ¿la librería está instalada? ¿versión correcta?
6. **Lógica** — solo después de descartar todo lo anterior

## Cómo agregar un nuevo scraper

1. Crear `scrapers/nombre_fuente.py`
2. Implementar `def run(query: TrendQuery) -> list[dict]`
3. Wrap en try/except, retornar [] si falla
4. Registrar en `scrapers/__init__.py`
5. Agregar al pipeline en `core/pipeline.py`
6. Documentar rate limits en ARCHITECTURE.md
7. Testear aislado antes de integrar
