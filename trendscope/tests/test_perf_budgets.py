"""Perf budgets (marked slow). Always-on cheap checks + optional heavy ones."""

import time

import pytest

from trendscope.analyzer.deduplicator import deduplicate
from trendscope.analyzer.insights import _detect_emerging_vs_established


def test_dedup_1k_budget():
    items = [{"source": f"s{i%4}", "title": f"unique topic number {i} about markets"} for i in range(1000)]
    t0 = time.perf_counter()
    deduplicate(items)
    assert time.perf_counter() - t0 < 2.0


def test_emerging_500_budget():
    items = [
        {
            "source": f"s{i%3}",
            "title": f"trend topic {i} quantum research",
            "trend_score": 70,
        }
        for i in range(500)
    ]
    t0 = time.perf_counter()
    _detect_emerging_vs_established(items)
    assert time.perf_counter() - t0 < 1.5


@pytest.mark.slow
def test_dedup_5k_slow_budget():
    items = [{"source": f"s{i%5}", "title": f"another unique subject {i} blockchain"} for i in range(5000)]
    t0 = time.perf_counter()
    deduplicate(items)
    assert time.perf_counter() - t0 < 3.0
