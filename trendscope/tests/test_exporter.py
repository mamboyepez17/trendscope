"""Tests para trendscope/output/exporter.py."""
import json
import tempfile
import unittest
from pathlib import Path

from trendscope.output.exporter import export_csv, export_excel, export_json


class ExporterTest(unittest.TestCase):
    def _sample_payload(self):
        return {
            "meta": {
                "query": {"topic": "crypto Colombia", "geo": "CO"},
                "total_analyzed": 10,
                "sentiment_summary": {
                    "positive": 6,
                    "negative": 2,
                    "neutral": 2,
                    "compound": 0.25,
                },
            },
            "top_trends": [
                {
                    "title": "Bitcoin sube",
                    "source": "reddit",
                    "url": "https://reddit.com/r/example",
                    "trend_score": 95,
                    "sentiment": "positive",
                    "sentiment_score": 0.8,
                    "likes": 100,
                },
                {
                    "title": "Ethereum dudas",
                    "source": "twitter",
                    "url": "",
                    "trend_score": 70,
                    "sentiment": "negative",
                    "sentiment_score": -0.4,
                },
            ],
        }

    def test_export_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = self._sample_payload()
            path = export_json(payload, filename="test.json", output_dir=tmp_path)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["query"]["topic"], "crypto Colombia")

    def test_export_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = self._sample_payload()
            path = export_csv(payload, filename="test.csv", output_dir=tmp_path)
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8-sig")
            self.assertIn("Bitcoin sube", text)
            self.assertIn("reddit", text)

    def test_export_excel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = self._sample_payload()
            path = export_excel(payload, filename="test.xlsx", output_dir=tmp_path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 0)

    def test_export_empty_trends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload = {"meta": {"query": {"topic": "empty"}, "total_analyzed": 0}, "top_trends": []}
            path = export_csv(payload, filename="empty.csv", output_dir=tmp_path)
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
