"""Twitter query construction and relevance filtering."""

from trendscope.scrapers.twitter import _is_relevant, _twitter_query


def test_mult_word_topic_is_quoted():
    assert _twitter_query("Abelardo de la Espriella") == '"Abelardo de la Espriella"'


def test_single_word_not_quoted():
    assert _twitter_query("crypto") == "crypto"


def test_no_lang_operator():
    q = _twitter_query("crypto Colombia")
    assert "lang:" not in q


def test_relevance_requires_keyword_token():
    assert _is_relevant("Abelardo de la Espriella habla de paz", "Abelardo de la Espriella")
    assert not _is_relevant("GPT-5 is here rolling out", "Abelardo de la Espriella")


def test_live_parser_without_lang_garbage():
    # Unit-level: query helper never injects lang operators
    for topic in ("crypto Colombia", "Abelardo de la Espriella", "AI"):
        assert "OR lang" not in _twitter_query(topic)
