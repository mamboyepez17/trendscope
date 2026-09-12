"""Operational CLI: doctor and smoke checks (no interactive menu)."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


def run_doctor_report() -> dict[str, Any]:
    from trendscope.core.doctor import check_all

    return check_all()


def print_doctor(report: dict[str, Any]) -> None:
    table = Table(title="TrendScope Doctor", show_lines=True)
    table.add_column("Source", style="cyan", no_wrap=True)
    table.add_column("Status")
    table.add_column("Message", overflow="fold")

    for name, info in report.items():
        status = str(info.get("status", "?"))
        style = {"ok": "green", "warn": "yellow", "error": "red", "off": "dim"}.get(status, "white")
        table.add_row(name, f"[{style}]{status}[/{style}]", str(info.get("message", "")))
    console.print(table)


def run_smoke(live: bool = False) -> dict[str, Any]:
    """
    Smoke test del pipeline.
    - live=False: usa scrapers mockeados (sin red) — siempre debe pasar.
    - live=True: fuentes ligeras reales (HN, GDELT, Google RSS) con top_n mínimo.
    """
    from unittest.mock import patch

    from trendscope.core.pipeline import run as run_pipeline
    from trendscope.core.query import TrendQuery

    query = TrendQuery(mode="free", free_topic="smoke test", geo="CO", top_n=5)

    if not live:
        def fake(query_):
            return [
                {
                    "source": "smoke",
                    "title": "smoke test signal about AI",
                    "text": "smoke test signal about AI",
                    "url": "https://example.com/smoke",
                }
            ]

        payload = {
            "meta": {
                "query": {"topic": "smoke test", "geo": "CO"},
                "total_analyzed": 1,
                "sentiment_summary": {
                    "positive": 1,
                    "negative": 0,
                    "neutral": 0,
                    "engine": "local",
                    "overall": "positive",
                },
            },
            "top_trends": [
                {
                    "title": "smoke test signal about AI",
                    "source": "smoke",
                    "trend_score": 80.0,
                }
            ],
        }

        with patch("trendscope.core.pipeline.SOURCES", [("Smoke", fake)]):
            with patch("trendscope.core.pipeline._PARALLEL_SOURCES", {"Smoke"}):
                with patch("trendscope.core.pipeline._SERIAL_SOURCES", set()):
                    with patch("trendscope.core.pipeline.cache_get", return_value=None):
                        with patch("trendscope.core.pipeline.cache_set"):
                            with patch(
                                "trendscope.core.pipeline.analyze_items",
                                side_effect=lambda items, q: [
                                    {
                                        **i,
                                        "sentiment_label": "positive",
                                        "sentiment_score": 0.9,
                                        "sentiment_engine": "local",
                                        "emotions": {},
                                    }
                                    for i in items
                                ],
                            ):
                                with patch(
                                    "trendscope.core.pipeline.enrich_and_score",
                                    side_effect=lambda items, q: [
                                        {**i, "trend_score": 80.0} for i in items
                                    ],
                                ):
                                    with patch(
                                        "trendscope.core.pipeline.generate_insights",
                                        return_value={"summary": "ok"},
                                    ):
                                        with patch(
                                            "trendscope.core.pipeline.export_json",
                                            return_value=payload,
                                        ):
                                            with patch(
                                                "trendscope.core.pipeline.export_report",
                                                return_value="# smoke",
                                            ):
                                                result, _ = run_pipeline(query)
        return {
            "mode": "offline",
            "ok": True,
            "signals": result["meta"].get("total_analyzed", 0),
            "sentiment_engine": result["meta"].get("sentiment_summary", {}).get("engine"),
            "message": "Offline smoke OK (mocked scrapers, no network)",
        }

    # Live: only lightweight public sources
    import trendscope.scrapers.google_trends as gtrends
    import trendscope.scrapers.gdelt as gdelt
    import trendscope.scrapers.hackernews as hackernews

    results: dict[str, Any] = {"mode": "live", "sources": {}}
    total = 0
    for name, fn in (
        ("Hacker News", hackernews.run),
        ("GDELT", gdelt.run),
        ("Google Trends", gtrends.run),
    ):
        try:
            items = fn(query)
            results["sources"][name] = {"ok": True, "count": len(items)}
            total += len(items)
        except Exception as e:
            results["sources"][name] = {"ok": False, "error": str(e)}

    results["signals"] = total
    results["ok"] = total > 0
    results["message"] = (
        f"Live smoke: {total} signals from lightweight sources"
        if total
        else "Live smoke: no signals (check network / doctor)"
    )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trendscope-ops", description="TrendScope ops CLI")
    parser.add_argument("--doctor", action="store_true", help="Probe all data sources")
    parser.add_argument("--smoke", action="store_true", help="Run offline pipeline smoke")
    parser.add_argument(
        "--live",
        action="store_true",
        help="With --smoke: use live lightweight sources (network)",
    )
    args = parser.parse_args(argv)

    if args.doctor:
        print_doctor(run_doctor_report())
        return 0
    if args.smoke:
        result = run_smoke(live=args.live)
        console.print_json(data=result)
        return 0 if result.get("ok") else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
