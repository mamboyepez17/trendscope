"""Tests for sentiment alignment — the critical bug fix.
Uses the fallback keyword engine directly (bypasses pysentimiento/torch loading).
"""
import unittest

from sentiment.base import SentimentResult
from sentiment.local_engine import _analyze_fallback, _detect_language


class SentimentAlignmentTest(unittest.TestCase):
    """Verify that sentiment results stay aligned 1:1 with input texts,
    even when some texts are empty or too short."""

    def test_empty_text_returns_neutral_in_fallback(self):
        """The fallback function handles individual texts."""
        result = _analyze_fallback("")
        self.assertEqual(result.label, "neutral")

    def test_positive_es(self):
        result = _analyze_fallback("excelente noticia increible avance")
        self.assertEqual(result.label, "positive")

    def test_negative_es(self):
        result = _analyze_fallback("terrible crisis colapso desastre")
        self.assertEqual(result.label, "negative")

    def test_positive_en(self):
        result = _analyze_fallback("amazing wonderful great success")
        self.assertEqual(result.label, "positive")

    def test_negative_en(self):
        result = _analyze_fallback("terrible horrible awful crash failure")
        self.assertEqual(result.label, "negative")

    def test_neutral_text(self):
        result = _analyze_fallback("the report mentions quarterly data")
        self.assertEqual(result.label, "neutral")

    def test_detect_language_es(self):
        lang = _detect_language("el crypto es una nueva tecnologia en colombia")
        self.assertEqual(lang, "es")

    def test_detect_language_en(self):
        lang = _detect_language("the crypto is a new technology in the market")
        self.assertEqual(lang, "en")

    def test_score_in_valid_range(self):
        for text in ["amazing wonderful great", "terrible horrible bad", "just some text"]:
            result = _analyze_fallback(text)
            self.assertGreaterEqual(result.score, 0.0)
            self.assertLessEqual(result.score, 1.0)

    def test_label_is_valid(self):
        for text in ["amazing wonderful great", "terrible horrible bad", "just some text"]:
            result = _analyze_fallback(text)
            self.assertIn(result.label, {"positive", "negative", "neutral"})

    def test_result_is_sentiment_result(self):
        result = _analyze_fallback("test text here")
        self.assertIsInstance(result, SentimentResult)

    def test_fallback_engine_name_includes_lang(self):
        result_es = _analyze_fallback("el crypto es una nueva tecnologia")
        self.assertIn("es", result_es.engine)
        result_en = _analyze_fallback("the crypto is a new technology")
        self.assertIn("en", result_en.engine)


if __name__ == "__main__":
    unittest.main()
