"""Typed shapes for TrendScope export payloads (TypedDict, zero runtime cost)."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class QueryMeta(TypedDict):
    mode: str
    topic: str | None
    geo: str
    keywords_used: NotRequired[list[str]]


class SentimentSummary(TypedDict):
    positive: int
    negative: int
    neutral: int
    engine: str
    overall: str


class Meta(TypedDict):
    tool: str
    version: NotRequired[str]
    generated_at: NotRequired[str]
    date: NotRequired[str]
    query: QueryMeta
    total_analyzed: int
    top_n_exported: NotRequired[int]
    sources_used: NotRequired[list[str]]
    sentiment_summary: SentimentSummary
    source_errors: NotRequired[dict[str, str]]
    source_health: NotRequired[dict[str, Any]]


class TrendItem(TypedDict, total=False):
    rank: int
    title: str
    source: str
    trend_score: float
    url: str
    category: str
    sentiment: dict[str, Any]
    signals: dict[str, Any]


class TrendPayload(TypedDict, total=False):
    meta: Meta
    top_trends: list[TrendItem]
    insights: dict[str, Any]
    agent_prompt: str


def validate_payload(payload: dict) -> list[str]:
    """Validación ligera: devuelve lista de errores (vacía si OK)."""
    errors: list[str] = []
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return ["meta missing or not a dict"]
    if "query" not in meta:
        errors.append("meta.query missing")
    if "sentiment_summary" not in meta:
        errors.append("meta.sentiment_summary missing")
    if "top_trends" not in payload:
        errors.append("top_trends missing")
    elif not isinstance(payload["top_trends"], list):
        errors.append("top_trends must be a list")
    else:
        for i, t in enumerate(payload["top_trends"][:5]):
            if not isinstance(t, dict):
                errors.append(f"top_trends[{i}] not a dict")
                continue
            if "source" not in t:
                errors.append(f"top_trends[{i}].source missing")
    return errors
