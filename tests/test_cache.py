"""Tests for core/cache.py — in-memory result cache."""
import unittest
import time

from core import cache


class CacheTest(unittest.TestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_set_and_get(self):
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        self.assertEqual(result, {"data": "value"})

    def test_get_missing_returns_none(self):
        self.assertIsNone(cache.get("nonexistent"))

    def test_clear(self):
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        self.assertIsNone(cache.get("key1"))
        self.assertIsNone(cache.get("key2"))

    def test_stats_empty(self):
        s = cache.stats()
        self.assertEqual(s["total_entries"], 0)
        self.assertEqual(s["valid_entries"], 0)

    def test_stats_with_entries(self):
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        s = cache.stats()
        self.assertEqual(s["total_entries"], 2)
        self.assertEqual(s["valid_entries"], 2)

    def test_overwrite(self):
        cache.set("key1", "old")
        cache.set("key1", "new")
        self.assertEqual(cache.get("key1"), "new")


if __name__ == "__main__":
    unittest.main()
