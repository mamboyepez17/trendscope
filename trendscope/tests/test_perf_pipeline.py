"""Performance-oriented tests for pipeline components."""

import time
from pathlib import Path

from trendscope.analyzer.deduplicator import deduplicate
from trendscope.core.http import get_session


def test_dedup_500_items_under_1s():
    items = []
    for i in range(500):
        items.append(
            {
                "source": f"s{i % 5}",
                "title": f"unique topic number {i} about crypto markets and AI",
            }
        )
    # 20 near-dups
    for i in range(20):
        items.append(
            {
                "source": "dup",
                "title": "unique topic number 1 about crypto markets and AI",
            }
        )

    start = time.perf_counter()
    result = deduplicate(items)
    elapsed = time.perf_counter() - start
    assert len(result) < len(items)
    assert elapsed < 1.0, f"dedup took {elapsed:.3f}s"


def test_dedup_exact_duplicates_removed():
    items = [
        {"source": "a", "title": "Bitcoin hits new high"},
        {"source": "b", "title": "bitcoin hits new high"},
    ]
    assert len(deduplicate(items)) == 1


def test_session_is_reusable():
    s1 = get_session()
    s2 = get_session()
    assert s1 is s2


def test_amazon_has_timeout_wrapper():
    src = Path("trendscope/scrapers/amazon.py").read_text(encoding="utf-8")
    assert "timeout" in src
    assert "time.sleep" not in src


def test_google_trends_pytrends_only_if_rss_empty():
    src = Path("trendscope/scrapers/google_trends.py").read_text(encoding="utf-8")
    assert "if not results" in src


def test_hn_top_uses_threadpool():
    src = Path("trendscope/scrapers/hackernews.py").read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" in src


def test_twitter_has_backoff():
    src = Path("trendscope/scrapers/twitter.py").read_text(encoding="utf-8")
    assert "time.sleep" in src


def test_emerging_detector_handles_many_items():
    from trendscope.analyzer.insights import _detect_emerging_vs_established

    items = [
        {
            "source": f"s{i % 3}",
            "title": f"trend topic {i} quantum computing research",
            "trend_score": 70 + (i % 20),
        }
        for i in range(200)
    ]
    start = time.perf_counter()
    out = _detect_emerging_vs_established(items)
    elapsed = time.perf_counter() - start
    assert "emerging" in out
    assert elapsed < 1.0, f"emerging took {elapsed:.3f}s"
