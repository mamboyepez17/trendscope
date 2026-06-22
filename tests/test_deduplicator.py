"""Tests for analyzer/deduplicator.py — cross-source deduplication."""
import unittest

from analyzer.deduplicator import deduplicate, _similarity, _normalize_text, _text_hash


class DeduplicatorTest(unittest.TestCase):
    def test_exact_duplicates_removed(self):
        items = [
            {"title": "Bitcoin reaches new high"},
            {"title": "Bitcoin reaches new high"},  # exact dup
            {"title": "Ethereum merges to PoS"},
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 2)

    def test_near_duplicates_removed(self):
        items = [
            {"title": "Bitcoin reaches new all-time high today"},
            {"title": "Bitcoin reaches new all-time high"},  # near dup (>72%)
        ]
        result = deduplicate(items, threshold=0.72)
        self.assertEqual(len(result), 1)

    def test_different_items_kept(self):
        items = [
            {"title": "Bitcoin reaches new high"},
            {"title": "Ethereum merges to PoS"},
            {"title": "Solana network outage reported"},
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 3)

    def test_empty_text_skipped(self):
        items = [
            {"title": ""},
            {"title": "  "},
            {"title": "ab"},  # too short (< 3)
            {"title": "Real trend"},
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 1)

    def test_preserves_first_occurrence(self):
        items = [
            {"title": "Trend A", "source": "reddit"},
            {"title": "Trend A", "source": "twitter"},  # dup, should be removed
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "reddit")  # first kept

    def test_similarity_function(self):
        self.assertGreater(_similarity("hello world", "hello world"), 0.99)
        self.assertLess(_similarity("hello world", "goodbye universe"), 0.5)

    def test_normalize_text(self):
        self.assertEqual(_normalize_text("  Hello   World  "), "hello world")
        self.assertEqual(_normalize_text("UPPER"), "upper")

    def test_text_hash_consistency(self):
        h1 = _text_hash("Hello World")
        h2 = _text_hash("  hello   world  ")  # normalized = same
        self.assertEqual(h1, h2)

    def test_keyword_field_used(self):
        """Dedup should use 'keyword' field when 'title' is missing."""
        items = [
            {"keyword": "crypto trending"},
            {"keyword": "crypto trending"},  # dup
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 1)

    def test_text_field_used(self):
        """Dedup should use 'text' field when 'title' and 'keyword' are missing."""
        items = [
            {"text": "some tweet about crypto"},
            {"text": "some tweet about crypto"},  # dup
        ]
        result = deduplicate(items)
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
