"""Tests for analyzer/scorer.py — trend scoring logic."""
import unittest

from core.query import TrendQuery
from analyzer.scorer import score_item, enrich_and_score


class ScorerTest(unittest.TestCase):
    def setUp(self):
        self.query = TrendQuery(mode="free", free_topic="crypto Colombia")

    def test_reddit_score(self):
        item = {
            "source": "reddit",
            "title": "Crypto adoption in Colombia is growing fast",
            "score": 5000,
            "comments": 300,
            "upvote_ratio": 0.95,
            "created_utc": 0,  # very old -> no recency bonus
        }
        score = score_item(item, self.query)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_google_trends_rss_score(self):
        item = {
            "source": "google_trends_rss",
            "keyword": "crypto",
            "approx_traffic": "500K+",
        }
        score = score_item(item, self.query)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_twitter_score(self):
        item = {
            "source": "twitter",
            "text": "crypto Colombia adoption rising",
            "likes": 5000,
            "retweets": 2000,
            "user_followers": 100000,
        }
        score = score_item(item, self.query)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 100)

    def test_amazon_score(self):
        item = {
            "source": "amazon_bestsellers",
            "title": "Crypto hardware wallet",
            "rank": "#1",
        }
        score = score_item(item, self.query)
        self.assertGreaterEqual(score, 95)  # rank #1 -> high score

    def test_tiktok_score(self):
        item = {
            "source": "tiktok_trending",
            "keyword": "crypto",
            "video_count": 500000,
        }
        score = score_item(item, self.query)
        self.assertGreater(score, 50)
        self.assertLessEqual(score, 100)

    def test_keyword_bonus(self):
        """Items matching query keywords should get a bonus."""
        item_no_match = {
            "source": "reddit",
            "title": "Random topic unrelated to query",
            "score": 1000,
            "comments": 50,
            "upvote_ratio": 0.8,
            "created_utc": 0,
        }
        item_match = {
            "source": "reddit",
            "title": "crypto Colombia is amazing",
            "score": 1000,
            "comments": 50,
            "upvote_ratio": 0.8,
            "created_utc": 0,
        }
        score_no = score_item(item_no_match, self.query)
        score_yes = score_item(item_match, self.query)
        self.assertGreater(score_yes, score_no)

    def test_enrich_and_score_orders_by_score(self):
        items = [
            {"source": "reddit", "title": "low score", "score": 10, "comments": 1, "upvote_ratio": 0.5, "created_utc": 0},
            {"source": "reddit", "title": "high score crypto", "score": 40000, "comments": 4000, "upvote_ratio": 0.98, "created_utc": 0},
        ]
        scored = enrich_and_score(items, self.query)
        self.assertEqual(scored[0]["title"], "high score crypto")
        self.assertGreater(scored[0]["trend_score"], scored[1]["trend_score"])

    def test_empty_items(self):
        scored = enrich_and_score([], self.query)
        self.assertEqual(scored, [])


if __name__ == "__main__":
    unittest.main()
