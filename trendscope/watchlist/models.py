"""Models for the TrendScope watchlist and analysis history."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class WatchItem:
    """A topic to monitor periodically."""

    id: Optional[int]
    topic: str
    category: Optional[str]
    geo: str
    sentiment_engine: str
    interval_minutes: int
    active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class AnalysisRecord:
    """A single historical analysis snapshot."""

    id: Optional[int]
    topic: str
    geo: str
    analyzed_at: datetime
    total_signals: int
    top_score: float
    positive: int
    negative: int
    neutral: int
    payload_json: str
