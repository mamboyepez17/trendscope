"""Tests for core/query.py — TrendQuery dataclass."""
import unittest

from trendscope.core.query import TrendQuery


class QueryTest(unittest.TestCase):
    def test_category_keywords(self):
        q = TrendQuery(mode="category", category="crypto")
        kws = q.keywords
        self.assertIn("crypto Colombia", kws)
        self.assertIn("bitcoin tendencias", kws)

    def test_free_topic_keywords(self):
        from datetime import datetime

        q = TrendQuery(mode="free", free_topic="IA generativa", geo="CO")
        kws = q.keywords
        year = str(datetime.now().year)
        self.assertIn("IA generativa", kws)
        self.assertIn("IA generativa CO", kws)
        self.assertIn(f"IA generativa {year}", kws)
        self.assertIn("tendencias IA generativa", kws)

    def test_subreddits_for_category(self):
        q = TrendQuery(mode="category", category="crypto")
        subs = q.subreddits
        self.assertIn("CryptoCurrency", subs)
        self.assertIn("Bitcoin", subs)

    def test_subreddits_default_for_free(self):
        q = TrendQuery(mode="free", free_topic="random topic")
        subs = q.subreddits
        self.assertIn("worldnews", subs)
        self.assertIn("technology", subs)

    def test_display_name_category(self):
        q = TrendQuery(mode="category", category="tecnologia")
        self.assertEqual(q.display_name, "Categoria: tecnologia")

    def test_display_name_free(self):
        q = TrendQuery(mode="free", free_topic="machine learning")
        self.assertEqual(q.display_name, "Tema libre: machine learning")

    def test_topic_slug(self):
        q = TrendQuery(mode="free", free_topic="crypto Colombia 2026")
        self.assertEqual(q.topic_slug, "crypto_Colombia_2026")

    def test_topic_slug_truncation(self):
        q = TrendQuery(mode="free", free_topic="a" * 50)
        self.assertLessEqual(len(q.topic_slug), 30)

    def test_empty_keywords_for_unknown_category(self):
        q = TrendQuery(mode="category", category="nonexistent")
        self.assertEqual(q.keywords, [])


if __name__ == "__main__":
    unittest.main()
