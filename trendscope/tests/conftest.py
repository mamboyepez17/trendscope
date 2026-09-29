"""Shared pytest fixtures for TrendScope tests."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _no_live_comment_collection(monkeypatch):
    """Los tests no deben salir a internet a buscar comentarios desde /trends."""
    from trendscope.settings import settings

    monkeypatch.setattr(settings, "pipeline_collect_comments", False)


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch):
    """Point settings.data_dir at a temp folder."""
    from trendscope.settings import settings

    monkeypatch.setattr(settings, "data_dir", str(tmp_path))
    return tmp_path


@pytest.fixture
def isolated_app(tmp_path: Path):
    """FastAPI app with SQLite stores under tmp_path and scheduler disabled."""
    from trendscope.api.factory import create_app
    from trendscope.watchlist.scheduler import WatchlistScheduler
    from trendscope.watchlist.store import WatchlistStore

    store = WatchlistStore(db_path=tmp_path / "watchlist.db")
    scheduler = WatchlistScheduler(store)
    return create_app(
        store=store,
        scheduler=scheduler,
        enable_scheduler=False,
        configure_logging=False,
    )
