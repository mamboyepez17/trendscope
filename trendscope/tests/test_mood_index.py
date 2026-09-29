"""Índice de Ánimo: emociones por comentario + agregación ponderada."""

from trendscope.analyzer.mood_index import compute_mood_index, is_opinion, media_tone
from trendscope.core.text import mentions, topic_tokens
from trendscope.sentiment import enrich_emotions
from trendscope.sentiment.emotions import analyze_text, blend, from_model_probas


def _c(text, author="", score=0, source="reddit_comment"):
    return {"source": source, "kind": "comment", "text": text, "author": author, "score": score}


# ── Emociones por texto ──────────────────────────────────────────────────────

def test_anger_with_slang_and_emoji():
    r = analyze_text("Qué rabia, estos ladrones nos roban 😡")
    assert r.dominant == "anger"
    assert r.polarity < -0.5


def test_sadness():
    assert analyze_text("Me pone muy triste lo que pasó 😢").dominant == "sadness"


def test_joy_colombian_slang_accents_and_punctuation():
    assert analyze_text("Qué chimba, me encanta!!").dominant == "joy"
    assert analyze_text("Este producto es increíble!").dominant == "joy"
    assert analyze_text("Excelente.").dominant == "joy"


def test_fear():
    assert analyze_text("Tengo miedo de lo que viene con la inflación").dominant == "fear"


def test_neutral_news_style():
    r = analyze_text("El ministro habló hoy en rueda de prensa")
    assert r.dominant == "neutral"
    assert r.polarity == 0


def test_negation_flips_joy_and_silences_fear():
    assert analyze_text("No estoy feliz con esto").polarity < 0
    assert analyze_text("No tengo miedo").dominant == "neutral"


def test_no_substring_false_positives():
    # "pesar" (a pesar de), "contra" (encontrar/contrato), "pena" (vale la pena)
    r = analyze_text("A pesar de todo, voy a encontrar un contrato que vale la pena")
    assert r.dominant == "neutral"


def test_model_probas_mapping_and_blend():
    model = from_model_probas({"joy": 0.1, "anger": 0.2, "disgust": 0.5, "others": 0.2})
    assert model["anger"] > 0.6  # disgust → enojo
    mixed = blend(analyze_text("gracias 😊").distribution, model)
    assert abs(sum(mixed.values()) - 1.0) < 1e-6


# ── Agregación ────────────────────────────────────────────────────────────────

def test_angry_crowd():
    items = [_c(t, author=f"u{i}") for i, t in enumerate([
        "Qué rabia con este gobierno de ladrones 😡",
        "Indignante, estoy harto de tanta corrupción",
        "Son unos corruptos, me da asco",
        "Pésimo, una vergüenza total 🤬",
        "El precio subió otra vez, qué rabia",
    ])]
    enrich_emotions(items)
    mi = compute_mood_index(items, topic="gobierno")
    assert mi["mood"] == "angry"
    assert mi["label"] == "Enojados"
    assert mi["net_score"] < -30
    assert mi["emotions"]["anger"] > mi["emotions"]["joy"]
    assert "anger" in mi["quotes"]
    assert mi["sample_size"] == 5


def test_happy_crowd():
    items = [_c(t, author=f"u{i}") for i, t in enumerate([
        "Me encanta, excelente noticia 😍",
        "Qué chimba, felicitaciones!!",
        "Gracias por esto, muy bueno",
        "Genial, lo recomiendo 👏",
    ])]
    enrich_emotions(items)
    mi = compute_mood_index(items)
    assert mi["mood"] == "happy"
    assert mi["net_score"] > 30
    assert mi["headline"].startswith("La gente se siente mayormente contenta")


def test_divided_crowd():
    items = [_c(t, author=f"u{i}") for i, t in enumerate([
        "Me encanta, excelente 😍", "Genial, felicitaciones 👏", "Qué chimba!!",
        "Qué rabia, son ladrones 😡", "Pésimo, una vergüenza 🤬", "Estoy harto, indignante",
    ])]
    enrich_emotions(items)
    mi = compute_mood_index(items)
    assert mi["mood"] == "divided"
    assert mi["polarization"] >= 0.35


def test_one_author_one_vote():
    spam = [_c("Excelente, me encanta 😍", author="bot") for _ in range(20)]
    real = [_c(t, author=f"u{i}") for i, t in enumerate([
        "Qué rabia, ladrones 😡", "Indignante, estoy harto", "Una vergüenza 🤬",
    ])]
    items = spam + real
    enrich_emotions(items)
    mi = compute_mood_index(items)
    # 20 mensajes de una misma cuenta no pueden ganarle a 3 personas distintas
    assert mi["net_score"] < 0


def test_news_excluded_from_public_mood():
    news = [{"source": "google_news", "title": "Excelente logro histórico, gran victoria"}]
    assert not is_opinion(news[0])
    mi = compute_mood_index(news)
    assert mi["mood"] == "quiet" and mi["sample_size"] == 0
    assert media_tone(news)["n"] == 1


def test_engagement_capped():
    items = [
        _c("Me encanta 😍", author="a", score=1_000_000),
        _c("Qué rabia 😡", author="b"), _c("Indignante 😡", author="c"),
        _c("Una vergüenza 🤬", author="d"), _c("Estoy harto 😤", author="e"),
        _c("Pésimo servicio 👎", author="f"), _c("Me da asco 🤮", author="g"),
    ]
    enrich_emotions(items)
    # Un comentario viral pesa como máx. 4×, no aplasta a los demás
    assert compute_mood_index(items)["net_score"] < 0


def test_confidence_and_margin_reported():
    items = [_c("Me encanta 😍", author=f"u{i}") for i in range(3)]
    enrich_emotions(items)
    mi = compute_mood_index(items)
    assert mi["confidence"] == "baja"
    assert mi["margin"] is not None


# ── Menciones del tema ───────────────────────────────────────────────────────

def test_short_topic_matches_whole_words_only():
    toks = topic_tokens("IA")
    assert toks == ["ia"]
    assert mentions("La IA cambia todo", toks)
    assert not mentions("Noticias de Colombia", toks)


def test_long_topic_prefix_variants():
    toks = topic_tokens("Colombia")
    assert mentions("El pueblo colombiano opina", toks)


def test_mood_label_respects_index_sign():
    # Alegría es la mayor porción individual, pero las negativas juntas pesan más:
    # el ánimo no puede salir "Contentos" con índice negativo.
    items = [_c(t, author=f"u{i}") for i, t in enumerate([
        "Me encanta 😍", "Excelente 👏", "Qué chimba!!",
        "Qué rabia 😡", "Indignante",
        "Tengo miedo 😰", "Me preocupa mucho",
        "Qué triste 😢", "Me duele ver esto",
    ])]
    enrich_emotions(items)
    mi = compute_mood_index(items)
    if mi["net_score"] < 0:
        assert mi["mood"] in {"angry", "sad", "afraid", "divided"}
    assert not (mi["mood"] == "happy" and mi["net_score"] < 0)


def test_mixed_opinion_plurals():
    r = analyze_text("hay cosas buenas y cosas malas")
    assert r.dominant == "neutral" or abs(r.polarity) < 0.3
