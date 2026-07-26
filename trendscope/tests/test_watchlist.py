"""Tests for trendscope/watchlist/store.py."""
import tempfile
import unittest
from pathlib import Path

from trendscope.watchlist.models import WatchItem
from trendscope.watchlist.store import WatchlistStore


class WatchlistStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = WatchlistStore(db_path=self.tmp.name)

    def tearDown(self):
        try:
            self.store.path.unlink(missing_ok=True)
        except PermissionError:
            pass

    def test_add_and_get(self):
        item = WatchItem(
            id=None,
            topic="crypto Colombia",
            category=None,
            geo="CO",
            interval_minutes=30,
            sentiment_engine="local",
        )
        saved = self.store.add(item)
        self.assertIsNotNone(saved.id)
        fetched = self.store.get(saved.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.topic, "crypto Colombia")
        self.assertTrue(fetched.active)

    def test_list_active(self):
        item1 = WatchItem(
            id=None,
            topic="crypto",
            category=None,
            geo="CO",
            interval_minutes=60,
            sentiment_engine="local",
            active=True,
        )
        item2 = WatchItem(
            id=None,
            topic="politics",
            category=None,
            geo="CO",
            interval_minutes=60,
            sentiment_engine="local",
            active=False,
        )
        self.store.add(item1)
        self.store.add(item2)
        active = self.store.list_active()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].topic, "crypto")

    def test_update(self):
        item = WatchItem(
            id=None,
            topic="old",
            category=None,
            geo="CO",
            interval_minutes=60,
            sentiment_engine="local",
        )
        saved = self.store.add(item)
        saved.topic = "new"
        saved.interval_minutes = 15
        self.store.update(saved)
        fetched = self.store.get(saved.id)
        self.assertEqual(fetched.topic, "new")
        self.assertEqual(fetched.interval_minutes, 15)

    def test_delete(self):
        item = WatchItem(
            id=None,
            topic="delete",
            category=None,
            geo="CO",
            interval_minutes=60,
            sentiment_engine="local",
        )
        saved = self.store.add(item)
        self.assertTrue(self.store.delete(saved.id))
        self.assertIsNone(self.store.get(saved.id))
        self.assertFalse(self.store.delete(99999))

    def test_save_and_get_history(self):
        payload = {
            "meta": {
                "query": {"topic": "crypto", "geo": "CO"},
                "total_analyzed": 10,
                "sentiment_summary": {"positive": 5, "negative": 2, "neutral": 3},
            },
            "top_trends": [
                {"title": "Bitcoin", "trend_score": 95},
            ],
        }
        record = self.store.save_history(payload)
        self.assertIsNotNone(record.id)
        records = self.store.get_history(topic="crypto", days=7)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].topic, "crypto")
        self.assertEqual(records[0].total_signals, 10)

    def test_stats(self):
        self.store.add(
            WatchItem(
                id=None,
                topic="crypto",
                category=None,
                geo="CO",
                interval_minutes=60,
                sentiment_engine="local",
            )
        )
        stats = self.store.get_stats()
        self.assertEqual(stats["total_watchlist"], 1)
        self.assertEqual(stats["active_watchlist"], 1)


if __name__ == "__main__":
    unittest.main()
