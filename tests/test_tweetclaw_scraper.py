import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.query import TrendQuery
import scrapers.tweetclaw as tweetclaw


class TweetClawScraperTest(unittest.TestCase):
    def test_loads_nested_tweets(self) -> None:
        payload = {
            "data": {
                "tweets": [
                    {
                        "id": "123",
                        "text": "crypto Colombia adoption is rising",
                        "like_count": "120",
                        "retweet_count": 7,
                        "reply_count": 3,
                        "author": {"followers_count": "4500"},
                    }
                ]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tweetclaw.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            query = TrendQuery(mode="free", free_topic="crypto Colombia")
            with patch.object(tweetclaw, "TWEETCLAW_RESULTS_FILE", str(path)):
                results = tweetclaw.run(query)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source"], "tweetclaw")
        self.assertEqual(results[0]["keyword"], "crypto Colombia")
        self.assertEqual(results[0]["likes"], 120)
        self.assertEqual(results[0]["retweets"], 7)
        self.assertEqual(results[0]["replies"], 3)
        self.assertEqual(results[0]["user_followers"], 4500)
        self.assertEqual(results[0]["url"], "https://twitter.com/i/web/status/123")

    def test_missing_file_returns_empty_list(self) -> None:
        query = TrendQuery(mode="free", free_topic="crypto Colombia")
        with patch.object(tweetclaw, "TWEETCLAW_RESULTS_FILE", "/tmp/not-a-trendscope-file.json"):
            self.assertEqual(tweetclaw.run(query), [])


if __name__ == "__main__":
    unittest.main()
