"""Conversation analyzer unit tests."""

from trendscope.analyzer.conversation import analyze_conversation, classify_comment


def test_classify_support_es():
    info = classify_comment("Apoyo total, excelente trabajo del presidente")
    assert info["stance"] == "support"


def test_classify_against_es():
    info = classify_comment("Qué desastre, rechazo total esta corrupción")
    assert info["stance"] == "against"


def test_classify_toxic():
    info = classify_comment("Eres un imbécil malparido basura")
    assert info["toxic"] is True or info["hot"] is True


def test_mood_supportive():
    comments = [
        {"kind": "comment", "text": "Excelente noticia, apoyo la medida"},
        {"kind": "comment", "text": "Gran trabajo y orgullo nacional"},
        {"kind": "comment", "text": "Me parece genial y lo celebro"},
    ]
    s = analyze_conversation(comments)
    assert s["mood"] in {"supportive", "calm"}
    assert s["emoji"] in {"😊", "😌"}
    assert s["acceptance_score"] > 0


def test_mood_toxic():
    comments = [
        {"kind": "comment", "text": "imbécil basura mierda malparido"},
        {"kind": "comment", "text": "idiota estúpido asco de gente"},
        {"kind": "comment", "text": "gonorrea malparido ladrón corrupto"},
    ]
    s = analyze_conversation(comments)
    assert s["mood"] in {"toxic", "hot"}
    assert s["toxic"] >= 1
    assert s["emoji"] in {"🤬", "😠", "⚠️"}


def test_mood_polarized():
    comments = [
        {"kind": "comment", "text": "Apoyo total, excelente"},
        {"kind": "comment", "text": "Gran victoria, orgullo"},
        {"kind": "comment", "text": "Rechazo absoluto, desastre y fracaso"},
        {"kind": "comment", "text": "Corrupción y protesta, indignación"},
        {"kind": "comment", "text": "Mejor gobierno, bravo"},
        {"kind": "comment", "text": "Renuncia, críticas duras"},
    ]
    s = analyze_conversation(comments)
    assert s["support"] >= 2 and s["against"] >= 2
    assert s["mood"] in {"polarized", "hot", "mixed"}


def test_acceptance_formula():
    comments = [
        {"kind": "comment", "text": "excelente apoyo"},
        {"kind": "comment", "text": "desastre rechazo"},
    ]
    s = analyze_conversation(comments)
    assert s["total"] >= 2
    assert -1.0 <= s["acceptance_score"] <= 1.0
