"""Repository interfaces — SQLite today, Postgres-ready tomorrow."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from trendscope.watchlist.models import AnalysisRecord, WatchItem
from trendscope.watchlist.store import WatchlistStore


class WatchlistRepository(ABC):
    """Puerto de acceso a watchlist/history. Implementación actual: SQLite."""

    @abstractmethod
    def add(self, item: WatchItem) -> WatchItem: ...

    @abstractmethod
    def list_all(self, org_id: str | None = None) -> list[WatchItem]: ...

    @abstractmethod
    def list_active(self, org_id: str | None = None) -> list[WatchItem]: ...

    @abstractmethod
    def get(self, item_id: int, org_id: str | None = None) -> Optional[WatchItem]: ...

    @abstractmethod
    def update(self, item: WatchItem) -> WatchItem: ...

    @abstractmethod
    def delete(self, item_id: int, org_id: str | None = None) -> bool: ...

    @abstractmethod
    def save_history(self, payload: dict, org_id: str = "default") -> AnalysisRecord: ...

    @abstractmethod
    def get_history(
        self,
        topic: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
        org_id: str | None = None,
    ) -> list[AnalysisRecord]: ...

    @abstractmethod
    def get_stats(self) -> dict: ...

    @abstractmethod
    def prune_history(self, keep_days: int = 90, keep_payload_days: int = 14) -> dict: ...


class SqliteWatchlistRepository(WatchlistRepository):
    """Adaptador sobre el WatchlistStore SQLite existente."""

    def __init__(self, store: WatchlistStore):
        self._store = store

    def add(self, item: WatchItem) -> WatchItem:
        return self._store.add(item)

    def list_all(self, org_id: str | None = None) -> list[WatchItem]:
        return self._store.list_all(org_id=org_id)

    def list_active(self, org_id: str | None = None) -> list[WatchItem]:
        return self._store.list_active(org_id=org_id)

    def get(self, item_id: int, org_id: str | None = None) -> Optional[WatchItem]:
        return self._store.get(item_id, org_id=org_id)

    def update(self, item: WatchItem) -> WatchItem:
        return self._store.update(item)

    def delete(self, item_id: int, org_id: str | None = None) -> bool:
        return self._store.delete(item_id, org_id=org_id)

    def save_history(self, payload: dict, org_id: str = "default") -> AnalysisRecord:
        return self._store.save_history(payload, org_id=org_id)

    def get_history(
        self,
        topic: Optional[str] = None,
        days: int = 7,
        limit: int = 100,
        org_id: str | None = None,
    ) -> list[AnalysisRecord]:
        return self._store.get_history(topic=topic, days=days, limit=limit, org_id=org_id)

    def get_stats(self) -> dict:
        return self._store.get_stats()

    def prune_history(self, keep_days: int = 90, keep_payload_days: int = 14) -> dict:
        return self._store.prune_history(keep_days=keep_days, keep_payload_days=keep_payload_days)
