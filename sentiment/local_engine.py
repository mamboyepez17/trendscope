# sentiment/local_engine.py
# Soporte bilingue: espanol latinoamericano + ingles
# pysentimiento (lang="es" y lang="en") + fallback por keywords
from loguru import logger
from sentiment.base import SentimentResult

# Modelos cargados una sola vez (lazy loading)
_sentiment_model_es = None
_sentiment_model_en = None
_emotion_model_es = None
_emotion_model_en = None
_use_fallback = False


# --- Keywords para fallback bilingue ---

_POSITIVE_ES = {
    "excelente", "increible", "genial", "bueno", "mejor", "perfecto",
    "encanta", "recomiendo", "fantastico", "maravilloso", "feliz", "gran",
    "innovador", "revolucionario", "impresionante", "hermoso", "brillante",
    "logro", "exito", "victoria", "avance", "progreso", "crecimiento",
    "oportunidad", "beneficio", "positivo", "optimista", "esperanza",
}

_NEGATIVE_ES = {
    "terrible", "horrible", "malo", "peor", "fraude", "estafa", "odio",
    "decepcionante", "basura", "inutil", "caro", "fallo", "error",
    "problema", "crisis", "colapso", "caida", "desastre", "peligro",
    "muerto", "muerte", "guerra", "violencia", "miedo", "panico",
    "rechazo", "fracaso", "perdida", "deuda", "quiebra", "corrupcion",
}

_POSITIVE_EN = {
    "love", "great", "best", "amazing", "awesome", "excellent", "wonderful",
    "fantastic", "good", "perfect", "brilliant", "outstanding", "superb",
    "incredible", "beautiful", "success", "win", "winning", "growth",
    "breakthrough", "innovative", "revolutionary", "impressive", "top",
    "trending", "popular", "viral", "boom", "record", "achievement",
    "opportunity", "benefit", "positive", "optimistic", "hope", "excited",
}

_NEGATIVE_EN = {
    "bad", "worst", "hate", "terrible", "horrible", "awful", "poor",
    "scam", "fraud", "disappointing", "broken", "crash", "fail", "failure",
    "fear", "danger", "warning", "alert", "crisis", "collapse", "dead",
    "death", "war", "violence", "panic", "loss", "debt", "bankruptcy",
    "corruption", "disaster", "threat", "risk", "decline", "recession",
    "layoff", "fired", "scandal", "controversy", "outrage", "angry",
}

# Palabras comunes en espanol para deteccion de idioma
_SPANISH_INDICATORS = {
    "el", "la", "los", "las", "un", "una", "de", "del", "en", "es",
    "que", "por", "para", "con", "como", "pero", "mas", "este", "esta",
    "son", "fue", "ser", "tiene", "han", "hay", "muy", "tambien", "sobre",
    "nuevo", "nueva", "mejor", "puede", "todos", "todo", "entre", "desde",
}


def _detect_language(text: str) -> str:
    """
    Detecta idioma basado en palabras comunes.
    Retorna 'es' o 'en'.
    """
    words = set(text.lower().split())
    spanish_count = len(words & _SPANISH_INDICATORS)
    # Si tiene 2+ palabras tipicas del espanol, es espanol
    if spanish_count >= 2:
        return "es"
    return "en"


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
    """Analisis basico de sentimiento por keywords bilingue."""
    lang = _detect_language(text)
    words = set(text.lower().split())

    if lang == "es":
        pos_count = len(words & _POSITIVE_ES) + len(words & _POSITIVE_EN)
        neg_count = len(words & _NEGATIVE_ES) + len(words & _NEGATIVE_EN)
    else:
        pos_count = len(words & _POSITIVE_EN) + len(words & _POSITIVE_ES)
        neg_count = len(words & _NEGATIVE_EN) + len(words & _NEGATIVE_ES)

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
        engine=f"local_fallback_{lang}",
        emotions={},
    )


def analyze(texts: list[str]) -> list[SentimentResult]:
    """Analiza sentimiento de una lista de textos (autodeteccion ES/EN)."""
    _load()
    results: list[SentimentResult] = []

    LABEL_MAP = {"POS": "positive", "NEG": "negative", "NEU": "neutral"}

    for text in texts:
        # Mantener alineacion 1:1 con los items: si el texto es vacio o
        # muy corto, devolver neutral en lugar de saltarlo (sino se
        # desalinean los resultados con los items originales).
        if not text or len(text.strip()) < 3:
            results.append(SentimentResult(
                text="",
                label="neutral",
                score=0.5,
                engine="local_skipped",
                emotions={},
            ))
            continue
        try:
            text_clean = text[:512]
            lang = _detect_language(text_clean)

            if _use_fallback:
                results.append(_analyze_fallback(text_clean))
            else:
                # Seleccionar modelo segun idioma detectado
                if lang == "es":
                    sent_model = _sentiment_model_es
                    emo_model = _emotion_model_es
                else:
                    sent_model = _sentiment_model_en
                    emo_model = _emotion_model_en

                sent = sent_model.predict(text_clean)
                emo = emo_model.predict(text_clean)

                results.append(SentimentResult(
                    text=text[:100],
                    label=LABEL_MAP.get(sent.output, "neutral"),
                    score=max(sent.probas.values()),
                    engine=f"local_{lang}",
                    emotions=dict(emo.probas),
                ))
        except Exception as e:
            logger.warning(f"Local sentiment '{text[:40]}': {e}")
            results.append(_analyze_fallback(text))

    return results
