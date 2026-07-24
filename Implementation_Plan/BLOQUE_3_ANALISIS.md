# 🧠 TRENDSCOPE — BLOQUE 3 DE 7
## Análisis: Scorer + Deduplicador + Sentimiento
## Autor: mamboyepez17

---

## INSTRUCCIONES PARA EL AGENTE

Este es el Bloque 3 de 7. Construyes el cerebro analítico de TrendScope:
deduplicación cross-fuente, análisis de sentimiento (local + Claude) y
scoring unificado 0-100.

**Prerequisito:** Bloque 2 aprobado.

**Reglas:**
- Sentimiento local con pysentimiento (gratis, español latinoamericano)
- Sentimiento premium con Claude Haiku API
- El scorer usa el sentimiento como bonus/penalización en el score
- Si el sentimiento falla → marcar neutral y continuar
- NO pasar al Bloque 4 sin confirmación del usuario

---

## PASO 3.1 — `analyzer/deduplicator.py`

```python
# analyzer/deduplicator.py
from difflib import SequenceMatcher
from loguru import logger


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(items: list[dict], threshold: float = 0.72) -> list[dict]:
    """
    Elimina items con texto muy similar entre fuentes.
    Threshold 0.72 = 72% de similitud para considerar duplicado.
    Mantiene el primero (mayor score al llegar ordenado por fuente).
    """
    seen: list[str] = []
    result: list[dict] = []

    for item in items:
        text = (
            item.get("title") or
            item.get("keyword") or
            item.get("text") or
            ""
        ).strip()

        if not text or len(text) < 3:
            continue

        is_duplicate = any(_similarity(text, s) > threshold for s in seen)
        if not is_duplicate:
            seen.append(text)
            result.append(item)

    removed = len(items) - len(result)
    logger.info(f"Deduplicación: {removed} duplicados removidos → {len(result)} únicos")
    return result
```

---

## PASO 3.2 — `sentiment/base.py`

```python
# sentiment/base.py
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class SentimentResult:
    """Resultado estándar de análisis de sentimiento."""
    text: str
    label: Literal["positive", "negative", "neutral"]
    score: float           # 0.0 a 1.0 — confianza
    engine: str            # "local" | "claude" | "failed"
    emotions: dict = field(default_factory=dict)


SENTIMENT_EMOJI: dict[str, str] = {
    "positive": "😊",
    "negative": "😟",
    "neutral":  "😐",
}


def format_sentiment(result: SentimentResult) -> str:
    emoji = SENTIMENT_EMOJI.get(result.label, "❓")
    return f"{emoji} {result.label} ({result.score:.0%})"
```

---

## PASO 3.3 — `sentiment/local_engine.py`

```python
# sentiment/local_engine.py
# pysentimiento — entrenado en español latinoamericano
# 100% gratuito, corre en CPU o GPU (RTX 5060 compatible)
from loguru import logger
from sentiment.base import SentimentResult

# Modelos cargados una sola vez (lazy loading)
_sentiment_model = None
_emotion_model   = None


def _load() -> None:
    global _sentiment_model, _emotion_model
    if _sentiment_model is None:
        try:
            from pysentimiento import create_analyzer
            logger.info("Cargando modelos locales de sentimiento...")
            _sentiment_model = create_analyzer("sentiment", lang="es")
            _emotion_model   = create_analyzer("emotion",   lang="es")
            logger.success("Modelos locales cargados ✅")
        except Exception as e:
            logger.error(f"Error cargando pysentimiento: {e}")
            raise


def analyze(texts: list[str]) -> list[SentimentResult]:
    _load()
    results: list[SentimentResult] = []

    LABEL_MAP = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}

    for text in texts:
        if not text or len(text.strip()) < 3:
            continue
        try:
            text_clean = text[:512]  # Límite del modelo
            sent = _sentiment_model.predict(text_clean)
            emo  = _emotion_model.predict(text_clean)

            results.append(SentimentResult(
                text=text[:100],
                label=LABEL_MAP.get(sent.output, "neutral"),
                score=max(sent.probas.values()),
                engine="local",
                emotions=dict(emo.probas),
            ))
        except Exception as e:
            logger.warning(f"Local sentiment '{text[:40]}': {e}")

    return results
```

---

## PASO 3.4 — `sentiment/claude_engine.py`

```python
# sentiment/claude_engine.py
# Claude Haiku — análisis premium, bajo costo por token
import json
from loguru import logger
from config import ANTHROPIC_API_KEY
from sentiment.base import SentimentResult


def analyze(texts: list[str]) -> list[SentimentResult]:
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY no configurada en .env")
        return []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        results: list[SentimentResult] = []
        batch_size = 10

        for i in range(0, len(texts), batch_size):
            batch = [t[:300] for t in texts[i:i + batch_size] if t and len(t.strip()) > 3]
            if not batch:
                continue

            prompt = (
                "Analiza el sentimiento de estos textos en español latinoamericano.\n"
                "Responde SOLO con un JSON array sin explicaciones ni markdown.\n"
                "Formato por item:\n"
                '{"label":"positive|negative|neutral","score":0.0-1.0,'
                '"emotions":{"joy":0.0,"anger":0.0,"fear":0.0,"sadness":0.0,"surprise":0.0}}\n\n'
                f"Textos:\n{json.dumps(batch, ensure_ascii=False)}"
            )

            response = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            raw = response.content[0].text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)

            for idx, item in enumerate(parsed):
                if idx < len(batch):
                    results.append(SentimentResult(
                        text=batch[idx][:100],
                        label=item.get("label", "neutral"),
                        score=float(item.get("score", 0.5)),
                        engine="claude",
                        emotions=item.get("emotions", {}),
                    ))

        logger.success(f"Claude sentiment: {len(results)} textos analizados")
        return results

    except Exception as e:
        logger.error(f"Claude sentiment engine: {e}")
        return []
```

---

## PASO 3.5 — `sentiment/__init__.py`

```python
# sentiment/__init__.py
from loguru import logger
from sentiment.base import SentimentResult
from core.query import TrendQuery


def analyze_items(items: list[dict], query: TrendQuery) -> list[dict]:
    """
    Entry point unificado de sentimiento.
    Analiza todos los items y los enriquece con label, score y emotions.
    Si el engine falla, marca todos como neutral y continúa.
    """
    engine = query.sentiment_engine
    texts = [
        (item.get("title") or item.get("keyword") or item.get("text") or "")[:300]
        for item in items
    ]

    logger.info(f"Analizando sentimiento: {len(texts)} items con motor '{engine}'")

    try:
        if engine == "claude":
            from sentiment.claude_engine import analyze
        else:
            from sentiment.local_engine import analyze

        results = analyze(texts)

        # Enriquecer items originales
        for i, result in enumerate(results):
            if i < len(items):
                items[i]["sentiment_label"]  = result.label
                items[i]["sentiment_score"]  = result.score
                items[i]["sentiment_engine"] = result.engine
                items[i]["emotions"]         = result.emotions

        # Items sin resultado de sentimiento → neutral
        for item in items:
            if "sentiment_label" not in item:
                item["sentiment_label"]  = "neutral"
                item["sentiment_score"]  = 0.5
                item["sentiment_engine"] = engine
                item["emotions"]         = {}

    except Exception as e:
        logger.error(f"Sentimiento falló completamente: {e} → marcando todo neutral")
        for item in items:
            item["sentiment_label"]  = "neutral"
            item["sentiment_score"]  = 0.5
            item["sentiment_engine"] = "failed"
            item["emotions"]         = {}

    return items
```

---

## PASO 3.6 — `analyzer/scorer.py`

```python
# analyzer/scorer.py
import re
from datetime import datetime, timezone
from loguru import logger
from core.query import TrendQuery


def _score_by_source(item: dict) -> float:
    """Puntuación base según la fuente del item."""
    source = item.get("source", "")

    if source == "reddit":
        upvotes  = min(item.get("score", 0), 50000)
        ratio    = item.get("upvote_ratio", 0.5)
        comments = min(item.get("comments", 0), 5000)
        # Bonus por recencia
        created = item.get("created_utc", 0)
        hours_old = (datetime.now(timezone.utc).timestamp() - created) / 3600 if created else 999
        recency = 15 if hours_old < 6 else (8 if hours_old < 24 else 0)
        return (upvotes / 50000 * 35) + (ratio * 25) + (comments / 5000 * 25) + recency

    elif source == "google_trends_rss":
        t = item.get("approx_traffic", "0").replace("+", "").replace(",", "")
        try:
            traffic = int(re.sub(r"[^0-9]", "", t) or "0")
            return min(85, traffic / 100000 * 85)
        except Exception:
            return 60.0

    elif source == "google_trends_pytrends":
        return min(80, item.get("avg_interest_7d", 0) * 0.8)

    elif source == "twitter":
        likes     = min(item.get("likes", 0), 10000)
        retweets  = min(item.get("retweets", 0), 5000)
        followers = min(item.get("user_followers", 0), 1000000)
        return (likes / 10000 * 40) + (retweets / 5000 * 35) + (followers / 1000000 * 25)

    elif source == "amazon_bestsellers":
        rank_str = item.get("rank", "#99")
        rank_num = int(re.sub(r"[^0-9]", "", rank_str) or "99")
        return max(0, 100 - rank_num * 1.5)

    elif source == "tiktok_trending":
        return 65.0

    return 0.0


def score_item(item: dict, query: TrendQuery) -> float:
    score = _score_by_source(item)
    kws   = [k.lower() for k in query.keywords]

    # Bonus por relevancia con las keywords de la query
    text = (item.get("title") or item.get("keyword") or item.get("text") or "").lower()
    if kws:
        matches = sum(1 for k in kws if k in text)
        score = min(100, score + matches * 8)

    # Bonus/penalización por sentimiento
    sentiment = item.get("sentiment_label", "neutral")
    if sentiment == "positive":
        score = min(100, score + 5)
    elif sentiment == "negative":
        score = max(0, score - 3)

    return round(score, 2)


def enrich_and_score(items: list[dict], query: TrendQuery) -> list[dict]:
    for item in items:
        item["trend_score"] = score_item(item, query)
        item["scored_at"]   = datetime.now(timezone.utc).isoformat()

    scored = sorted(items, key=lambda x: x["trend_score"], reverse=True)
    if scored:
        logger.success(
            f"Scoring: {len(scored)} items | "
            f"Top score: {scored[0]['trend_score']} | "
            f"'{(scored[0].get('title') or scored[0].get('keyword',''))[:50]}'"
        )
    return scored
```

---

## PASO 3.7 — Validación del Bloque 3

```bash
cd trendscope

# Test deduplicador
python -c "
from analyzer.deduplicator import deduplicate

items = [
    {'source': 'reddit', 'title': 'Los mejores gadgets del 2026'},
    {'source': 'twitter', 'text': 'Los mejores gadgets del 2026'},  # duplicado
    {'source': 'google_trends_rss', 'keyword': 'inteligencia artificial Colombia'},
    {'source': 'amazon_bestsellers', 'title': 'Auriculares inalámbricos Sony'},
]
result = deduplicate(items)
print(f'✅ Deduplicador: {len(items)} → {len(result)} items únicos')
assert len(result) == 3, 'Debe eliminar 1 duplicado'
print('   Assertion OK')
"

# Test sentimiento local
python -c "
from sentiment.local_engine import analyze

texts = [
    'Me encanta este producto, es increíble',
    'Terrible experiencia, muy decepcionante',
    'El producto llegó a tiempo',
]
results = analyze(texts)
print(f'✅ Sentimiento local: {len(results)} resultados')
for r in results:
    print(f'   {r.label} ({r.score:.0%}) — {r.text[:40]}')
"

# Test sentimiento integrado (analyze_items)
python -c "
from core.query import TrendQuery
from sentiment import analyze_items

query = TrendQuery(mode='free', free_topic='tecnologia', sentiment_engine='local')
items = [
    {'source': 'reddit', 'title': 'Nueva IA revoluciona el mercado'},
    {'source': 'twitter', 'text': 'Precios de tecnología por las nubes, indignante'},
    {'source': 'google_trends_rss', 'keyword': 'gadgets Colombia 2026'},
]
enriched = analyze_items(items, query)
print(f'✅ analyze_items: {len(enriched)} items enriquecidos')
for item in enriched:
    print(f'   {item[\"sentiment_label\"]} ({item[\"sentiment_score\"]:.0%}) — {(item.get(\"title\") or item.get(\"keyword\",\"\"))[:40]}')
"

# Test scorer completo
python -c "
from core.query import TrendQuery
from sentiment import analyze_items
from analyzer.scorer import enrich_and_score

query = TrendQuery(mode='category', category='tecnologia', sentiment_engine='local')
items = [
    {'source': 'reddit', 'title': 'Los mejores gadgets IA 2026', 'score': 5000, 'upvote_ratio': 0.95, 'comments': 300, 'created_utc': 0},
    {'source': 'google_trends_rss', 'keyword': 'inteligencia artificial', 'approx_traffic': '500K+'},
    {'source': 'amazon_bestsellers', 'title': 'Echo Dot 5ta generación', 'rank': '#3'},
    {'source': 'tiktok_trending', 'keyword': 'gadgetsIA'},
]
items = analyze_items(items, query)
scored = enrich_and_score(items, query)
print(f'✅ Scorer: {len(scored)} items puntuados')
for item in scored:
    title = item.get('title') or item.get('keyword','')
    print(f'   [{item[\"trend_score\"]:5.1f}] {item[\"sentiment_label\"]:8} — {title[:50]}')
"
```

---

## PASO 3.8 — Actualizar CHANGELOG

```markdown
## [0.4.0] — FECHA — MODELO_USADO

### Añadido
- analyzer/deduplicator.py: elimina duplicados cross-fuente (threshold 72%)
- sentiment/base.py: SentimentResult dataclass estándar
- sentiment/local_engine.py: pysentimiento español latinoamericano (lazy loading)
- sentiment/claude_engine.py: Claude Haiku API en batches de 10
- sentiment/__init__.py: analyze_items() entry point unificado con fallback neutral
- analyzer/scorer.py: scoring 0-100 por fuente + bonus keywords + bonus sentimiento

### Pendiente
- Bloque 4: Output (JSON exporter + Markdown report)
```

---

## ✅ CRITERIOS DE APROBACIÓN — BLOQUE 3

- [ ] Deduplicador elimina correctamente duplicados similares
- [ ] Sentimiento local analiza textos en español ✅
- [ ] `analyze_items()` enriquece items con label + score + emotions
- [ ] Si sentimiento falla → todos quedan como "neutral" sin romper nada
- [ ] Scorer produce valores 0-100 correctos por fuente
- [ ] Items positivos tienen score ligeramente mayor que neutrales
- [ ] CHANGELOG actualizado

## MENSAJE FINAL AL USUARIO

```
✅ BLOQUE 3 COMPLETADO

Componentes validados:
- Deduplicador    ✅ (elimina duplicados cross-fuente)
- Sentimiento local ✅ (pysentimiento español)
- analyze_items() ✅ (enriquece con label + emotions)
- Scorer          ✅ (0-100 con bonus sentimiento)

¿Aprobado para continuar al Bloque 4 — Output?
```

---

*TrendScope — Bloque 3 de 7 | Siguiente: BLOQUE_4_OUTPUT.md*
