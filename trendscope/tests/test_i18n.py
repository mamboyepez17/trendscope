"""Cualquier país: idioma, léxicos regionales, léxico propio, ediciones."""

import json
from unittest.mock import patch

from trendscope.core.locale import (
    country_subreddits,
    google_news_edition,
    language_for,
    ui_language,
)
from trendscope.sentiment.emotions import analyze_text, clear_cache
from trendscope.sentiment.lang import detect


def test_language_by_country():
    assert language_for("CO") == "es" and language_for("br") == "pt"
    assert language_for("FR") == "fr" and language_for("JP") == "en"
    assert ui_language(None, "BR") == "pt" and ui_language(None, "DE") == "en"
    assert ui_language("en", "CO") == "en"


def test_google_news_editions():
    assert google_news_edition("CO") == {"hl": "es-419", "gl": "CO", "ceid": "CO:es-419"}
    assert google_news_edition("ES")["ceid"] == "ES:es"
    assert google_news_edition("BR")["ceid"] == "BR:pt-419"
    assert google_news_edition("US")["ceid"] == "US:en"
    assert google_news_edition("DE")["ceid"] == "DE:de"


def test_detect_six_languages():
    assert detect("Estou muito feliz com isso, não acredito") == "pt"
    assert detect("Je ne suis pas content avec ce gouvernement") == "fr"
    assert detect("Ich bin nicht zufrieden mit der Regierung") == "de"
    assert detect("Non sono contento di questo governo") == "it"
    assert detect("I am not happy with this government") == "en"
    assert detect("No estoy contento con este gobierno") == "es"


def test_emotions_in_other_languages():
    assert analyze_text("Estou com muita raiva, que vergonha", geo="BR").dominant == "anger"
    assert analyze_text("J'ai peur de la crise", geo="FR").dominant == "fear"
    assert analyze_text("Ich bin so traurig", geo="DE").dominant == "sadness"
    assert analyze_text("Sono felice, grazie!", geo="IT").dominant == "joy"


def test_regional_slang_only_in_its_country():
    assert analyze_text("Qué chimba de concierto", geo="CO").dominant == "joy"
    assert analyze_text("Qué chimba de concierto", geo="MX").dominant == "neutral"
    assert analyze_text("Está bien chido", geo="MX").dominant == "joy"
    assert analyze_text("Fiquei puto com isso", geo="BR").dominant == "anger"


def test_custom_lexicon_file(tmp_path):
    path = tmp_path / "lex.json"
    path.write_text(json.dumps({"*": {"joy": ["bakaan"]}, "CO": {"anger": ["uyyyy"]}}), "utf-8")
    try:
        with patch("trendscope.settings.settings.custom_lexicon_path", str(path)):
            clear_cache()
            assert analyze_text("esto es bakaan", geo="MX").dominant == "joy"
            assert analyze_text("uyyyy no", geo="CO").dominant == "anger"
            assert analyze_text("uyyyy no", geo="MX").dominant == "neutral"
    finally:
        clear_cache()


def test_country_subreddits():
    assert country_subreddits("co") == ["Colombia"]
    assert country_subreddits("ZZ") == []


def test_multiword_slang_phrases():
    assert analyze_text("El concierto estuvo poca madre", geo="MX").dominant == "joy"
    assert analyze_text("Tô de saco cheio desse governo", geo="BR").dominant == "anger"
    assert analyze_text("El concierto estuvo poca madre", geo="CO").dominant == "neutral"


def test_example_lexicon_file_is_valid():
    from pathlib import Path

    path = Path("docs/lexicon.example.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        with patch("trendscope.settings.settings.custom_lexicon_path", str(path)):
            clear_cache()
            assert analyze_text("Me dio mucho culillo esa noticia", geo="CO").dominant == "fear"
            assert analyze_text("Qué nota de partido", geo="CO").dominant == "joy"
    finally:
        clear_cache()
    assert set(data) <= {"*", "es", "en", "pt", "fr", "de", "it", "CO", "MX", "BR"}
