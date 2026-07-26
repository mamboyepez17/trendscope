"""Tests para trendscope/narrator/engine.py."""
import unittest
from unittest.mock import patch, MagicMock

from trendscope.narrator.engine import generate_summary, NARRATIVE_STYLES


class NarratorTest(unittest.TestCase):
    def test_narrative_disabled(self):
        payload = {"meta": {"query": {}}}
        with patch("trendscope.narrator.engine.settings.narrative_enabled", False):
            result = generate_summary(payload)
        self.assertEqual(result["provider"], "none")
        self.assertIn("deshabilitado", result["narrative"].lower())

    def test_invalid_provider(self):
        payload = {"meta": {"query": {}}}
        with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
            with patch("trendscope.narrator.engine.settings.narrator_provider", "unknown"):
                result = generate_summary(payload)
        self.assertIn("no soportado", result["narrative"].lower())

    def test_none_provider_returns_statistical_summary(self):
        payload = {
            "meta": {"query": {"topic": "crypto", "geo": "CO"}, "total_analyzed": 10},
            "top_trends": [
                {"title": "Bitcoin", "trend_score": 90, "source": "reddit"}
            ],
        }
        with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
            with patch("trendscope.narrator.engine.settings.narrator_provider", "none"):
                result = generate_summary(payload)
        self.assertEqual(result["provider"], "none")
        self.assertIn("Bitcoin", result["narrative"])

    def test_openrouter_missing_key(self):
        payload = {"meta": {"query": {}}}
        with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
            with patch("trendscope.narrator.engine.settings.narrator_provider", "openrouter"):
                with patch("trendscope.narrator.engine.settings.openrouter_api_key", ""):
                    result = generate_summary(payload)
        self.assertEqual(result["provider"], "openrouter")
        self.assertTrue(result.get("error"))
        self.assertIn("OpenRouter", result["narrative"])

    @patch("trendscope.narrator.engine._call_openrouter")
    def test_openrouter_success(self, mock_call):
        mock_call.return_value = "Resumen ejecutivo generado."
        payload = {
            "meta": {"query": {"topic": "crypto", "geo": "CO"}, "total_analyzed": 5},
            "top_trends": [],
        }
        with patch("trendscope.narrator.engine.settings.narrative_enabled", True):
            with patch("trendscope.narrator.engine.settings.narrator_provider", "openrouter"):
                with patch("trendscope.narrator.engine.settings.openrouter_api_key", "fake-key"):
                    result = generate_summary(payload, style="executive")
        self.assertEqual(result["narrative"], "Resumen ejecutivo generado.")
        self.assertEqual(result["provider"], "openrouter")
        self.assertEqual(result["style"], "executive")
        self.assertEqual(result["model"], "deepseek/deepseek-chat-v3-0324:free")

    def test_styles_dictionary(self):
        self.assertIn("executive", NARRATIVE_STYLES)
        self.assertIn("creative", NARRATIVE_STYLES)
        self.assertIn("technical", NARRATIVE_STYLES)
        self.assertIn("alert", NARRATIVE_STYLES)


if __name__ == "__main__":
    unittest.main()
