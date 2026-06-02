# sentiment/local_engine.py
# pysentimiento — entrenado en espanol latinoamericano
# 100% gratuito, corre en CPU o GPU
# Fallback: analisis basico por keywords si pysentimiento no esta disponible
from loguru import logger
from sentiment.base import SentimentResult

# Modelos cargados una sola vez (lazy loading)
_sentiment_model = None
_emotion_model = None
_use_fallback = False


# Keywords para el fallback basico de sentimiento
_POSITIVE_WORDS = {
    "excelente", "increible", "genial", "bueno", "mejor", "perfecto",
    "encanta", "recomiendo", "fantastico", "maravilloso", "feliz", "gran",
    "innovador", "revolucionario", "impresionante", "love", "great", "best",
    "amazing", "awesome", "excellent", "wonderful", "fantastic", "good",
    "top", "trending", "popular", "viral", "boom", "record",
}
_NEGATIVE_WORDS = {
    "terrible", "horrible", "malo", "peor", "fraude", "estafa", "odio",
    "decepcionante", "basura", "inutil", "caro", "fallo", "error",
    "problema", "crisis", "colapso", "caida", "bad", "worst", "hate",
    "scam", "fraud", "disappointing", "awful", "broken", "crash",
    "fear", "danger", "warning", "alert",
}


def _load() -> None:
    """Carga modelos de pysentimiento o activa fallback."""
    global _sentiment_model, _emotion_model, _use_fallback
    if _sentiment_model is not None or _use_fallback:
        return

    try:
        from pysentimiento import create_analyzer
        logger.info("Cargando modelos locales de sentimiento (pysentimiento)...")
        _sentiment_model = create_analyzer("sentiment", lang="es")
        _emotion_model = create_analyzer("emotion", lang="es")
        logger.success("Modelos locales cargados OK")
    except ImportError:
        logger.warning(
            "pysentimiento no disponible (Python 3.14 incompatible) "
            "-> usando analisis por keywords como fallback"
        )
        _use_fallback = True
    except Exception as e:
        logger.warning(f"Error cargando pysentimiento: {e} -> usando fallback keywords")
        _use_fallback = True


def _analyze_fallback(text: str) -> SentimentResult:
    """Analisis basico de sentimiento por keywords cuando pysentimiento no esta."""
    words = set(text.lower().split())
    pos_count = len(words & _POSITIVE_WORDS)
    neg_count = len(words & _NEGATIVE_WORDS)

    if pos_count > neg_count:
        label = "positive"
        score = min(0.95, 0.6 + pos_count * 0.1)
    elif neg_count > pos_count:
        label = "negative"
        score = min(0.95, 0.6 + neg_count * 0.1)
    else:
        label = "neutral"
        score = 0.5

    return SentimentResult(
        text=text[:100],
        label=label,
        score=score,
        engine="local_fallback",
        emotions={},
    )


def analyze(texts: list[str]) -> list[SentimentResult]:
    """Analiza sentimiento de una lista de textos."""
    _load()
    results: list[SentimentResult] = []

    LABEL_MAP = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}

    for text in texts:
        if not text or len(text.strip()) < 3:
            continue
        try:
            text_clean = text[:512]  # Limite del modelo

            if _use_fallback:
                results.append(_analyze_fallback(text_clean))
            else:
                sent = _sentiment_model.predict(text_clean)
                emo = _emotion_model.predict(text_clean)

                results.append(SentimentResult(
                    text=text[:100],
                    label=LABEL_MAP.get(sent.output, "neutral"),
                    score=max(sent.probas.values()),
                    engine="local",
                    emotions=dict(emo.probas),
                ))
        except Exception as e:
            logger.warning(f"Local sentiment '{text[:40]}': {e}")
            # En caso de error individual, usar fallback para ese texto
            results.append(_analyze_fallback(text))

    return results
