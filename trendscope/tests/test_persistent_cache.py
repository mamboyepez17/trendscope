"""Tests para trendscope/core/persistent_cache.py."""
import unittest
import tempfile
import time
from pathlib import Path

from trendscope.core.persistent_cache import PersistentCache


class PersistentCacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.tmp_dir) / "test_cache.db"
        self.cache = PersistentCache(db_path=self.db_path, ttl=1)

    def tearDown(self):
        # Windows puede retener handles de SQLite; tolerar fallo de limpieza.
        try:
            self.db_path.unlink(missing_ok=True)
            self.db_path.parent.rmdir()
        except PermissionError:
            pass

    def test_set_and_get(self):
        self.cache.set("k1", {"a": 1})
        self.assertEqual(self.cache.get("k1"), {"a": 1})

    def test_expired_returns_none(self):
        self.cache.set("k1", {"a": 1})
        time.sleep(1.1)
        self.assertIsNone(self.cache.get("k1"))

    def test_clear(self):
        self.cache.set("k1", 1)
        self.cache.clear()
        self.assertIsNone(self.cache.get("k1"))

    def test_stats(self):
        self.cache.set("k1", 1)
        self.cache.set("k2", 2)
        s = self.cache.stats()
        self.assertEqual(s["total_entries"], 2)
        self.assertEqual(s["valid_entries"], 2)
        self.assertEqual(s["ttl_seconds"], 1)

    def test_cleanup(self):
        self.cache.set("k1", 1)
        time.sleep(1.1)
        self.cache.set("k2", 2)
        removed = self.cache.cleanup()
        self.assertEqual(removed, 1)
        self.assertIsNone(self.cache.get("k1"))
        self.assertEqual(self.cache.get("k2"), 2)


if __name__ == "__main__":
    unittest.main()
