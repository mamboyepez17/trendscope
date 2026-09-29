# sentiment/local_engine.py
# Soporte bilingue: espanol latinoamericano + ingles
# pysentimiento (lang="es" y lang="en") + fallback por keywords
from loguru import logger
from trendscope.sentiment.base import SentimentResult

# Modelos cargados una sola vez (lazy loading)
_sentiment_model_es = None
_sentiment_model_en = None
_emotion_model_es = None
_emotion_model_en = None
_use_fallback = False


# Palabras comunes en espanol para deteccion de idioma
_SPANISH_INDICATORS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "es",
    "que", "por", "para", "con", "como", "pero", "mas", "este", "esta",
    "son", "fue", "ser", "tiene", "han", "hay", "muy", "tambien", "sobre",
    "nuevo", "nueva", "mejor", "puede", "todos", "todo", "entre", "desde",
    "qué", "cuál", "cómo", "quién", "dónde", "cuándo", "porque", "aunque",
    "después", "antes", "mismo", "otra", "otro", "cada", "toda", "todo",
    "gobierno", "presidente", "país", "ciudad", "semana", "mañana", "ayer",
    "odio", "amor", "bueno", "buena", "malo", "mala", "grande", "pequeño",
}


def _strip_accents(s: str) -> str:
    import unicodedata

    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


def _detect_language(text: str) -> str:
    """
    Detecta idioma basado en stopwords, acentos y pistas léxicas.
    Retorna 'es' o 'en'. Por defecto 'es' (proyecto LatAm-first).
    """
    if not text or len(text.strip()) < 3:
        return "es"
    raw = text.lower()
    # Acentos del español (áéíóúñü) son señal fuerte
    if any(ch in raw for ch in "áéíóúñ¿¡"):
        return "es"
    words = set(_strip_accents(text).split())
    words_raw = set(raw.split())
    # Unir stopwords normalizadas y crudas
    pool = words | words_raw
    spanish_count = len(pool & _SPANISH_INDICATORS)
    english_markers = {
        "the", "and", "is", "are", "was", "were", "this", "that",
        "with", "for", "from", "have", "has", "will", "can", "about",
    }
    english_count = len(pool & english_markers)
    if spanish_count >= 1 and spanish_count >= english_count:
        return "es"
    if english_count >= 2:
        return "en"
    if spanish_count >= 1:
        return "es"
    # Default LatAm-first
    return "es"


def _load() -> None:
    """Carga modelos de pysentimiento o activa fallback."""
    global _sentiment_model_es, _sentiment_model_en
    global _emotion_model_es, _emotion_model_en, _use_fallback

    if _sentiment_model_es is not None or _use_fallback:
        return

    try:
        from pysentimiento import create_analyzer
        logger.info("Cargando modelos bilingues de sentimiento (pysentimiento)...")
        _sentiment_model_es = create_analyzer("sentiment", lang="es")
        _emotion_model_es = create_analyzer("emotion", lang="es")
        _sentiment_model_en = create_analyzer("sentiment", lang="en")
        _emotion_model_en = create_analyzer("emotion", lang="en")
        logger.success("Modelos bilingues (ES + EN) cargados OK")
    except ImportError:
        logger.warning(
            "pysentimiento no disponible (Python 3.14 incompatible) "
            "-> usando analisis por keywords bilingue como fallback"
        )
        _use_fallback = True
    except Exception as e:
        logger.warning(f"Error cargando pysentimiento: {e} -> usando fallback keywords")
        _use_fallback = True


def _analyze_fallback(text: str) -> SentimentResult:
    """Sentimiento por léxico bilingüe (tildes, puntuación, negación, emojis).

    Usa el detector de emociones: polaridad = alegría − (enojo+tristeza+miedo).
    """
    from trendscope.sentiment.cache import calibrate_score
    from trendscope.sentiment.emotions import analyze_text

    lang = _detect_language(text)
    emo = analyze_text(text)
    if emo.polarity >= 0.15:
        label = "positive"
    elif emo.polarity <= -0.15:
        label = "negative"
    else:
        label = "neutral"
    score = 0.5 if label == "neutral" else min(0.95, 0.55 + abs(emo.polarity) * 0.45)

    return SentimentResult(
        text=text[:100],
        label=label,
        score=calibrate_score(label, score),
        engine=f"local_fallback_{lang}",
        emotions={k: v for k, v in emo.distribution.items() if k != "neutral" and v > 0},
    )


def analyze(texts: list[str], batch_size: int = 32, batch_timeout: float = 20.0) -> list[SentimentResult]:
    """Analiza sentimiento de una lista de textos (autodeteccion ES/EN).

    - Cache LRU por texto
    - Batches para no saturar el modelo
    - Timeout por batch → fallback keywords
    """
    import time as _time

    from trendscope.sentiment.cache import cache_get, cache_set, calibrate_score

    _load()
    results: list[SentimentResult] = []

    LABEL_MAP = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}

    def _one(text: str) -> SentimentResult:
        if not text or len(text.strip()) < 3:
            return SentimentResult(
                text="",
                label="neutral",
                score=0.5,
                engine="local_skipped",
                emotions={},
            )
        engine_tag = "fallback" if _use_fallback else "pysentimiento"
        cached = cache_get(text, engine_tag)
        if cached is not None:
            return cached

        try:
            text_clean = text[:512]
            lang = _detect_language(text_clean)

            if _use_fallback:
                result = _analyze_fallback(text_clean)
            else:
                if lang == "es":
                    sent_model = _sentiment_model_es
                    emo_model = _emotion_model_es
                else:
                    sent_model = _sentiment_model_en
                    emo_model = _emotion_model_en

                sent = sent_model.predict(text_clean)
                emo = emo_model.predict(text_clean)
                label = LABEL_MAP.get(sent.output, "neutral")
                raw_p = max(sent.probas.values())
                result = SentimentResult(
                    text=text[:100],
                    label=label,
                    score=calibrate_score(label, raw_p),
                    engine=f"local_{lang}",
                    emotions=dict(emo.probas),
                )
            cache_set(text, engine_tag, result)
            return result
        except Exception as e:
            logger.warning(f"Local sentiment '{text[:40]}': {e}")
            return _analyze_fallback(text)

    # Procesar por batches (modelo transformers más estable así)
    for start in range(0, len(texts), batch_size):
        chunk = texts[start : start + batch_size]
        t0 = _time.perf_counter()
        for idx, text in enumerate(chunk):
            if _time.perf_counter() - t0 > batch_timeout:
                # Timeout: resto con fallback rápido (por posición, no por valor)
                for rest in chunk[idx:]:
                    results.append(_analyze_fallback(rest))
                break
            results.append(_one(text))

    return results
