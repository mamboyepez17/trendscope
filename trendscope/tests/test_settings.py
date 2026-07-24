"""Tests para trendscope/settings.py."""
import unittest

from trendscope.settings import Settings


class SettingsTest(unittest.TestCase):
    def test_defaults(self):
        s = Settings(_env_file=None)
        self.assertEqual(s.geo_target, "CO")
        self.assertEqual(s.top_n, 25)
        self.assertEqual(s.sentiment_engine, "local")
        self.assertTrue(s.ollama_enabled)
        self.assertEqual(s.ollama_model, "qwen3.5:9b")
        self.assertEqual(s.cache_ttl_seconds, 300)

    def test_env_override(self):
        s = Settings(_env_file=None, geo_target="US", top_n=50)
        self.assertEqual(s.geo_target, "US")
        self.assertEqual(s.top_n, 50)


if __name__ == "__main__":
    unittest.main()
