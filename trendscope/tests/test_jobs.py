"""Async jobs API tests."""

import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_async_trends_returns_202(tmp_path):
    import trendscope.jobs.store as jobs_mod
    from trendscope.server_api import app

    jobs_mod.reset_job_store(tmp_path / "jobs.db")
    client = TestClient(app)

    payload = {
        "meta": {"query": {"topic": "ai", "geo": "CO"}, "total_analyzed": 1},
        "top_trends": [{"title": "t", "trend_score": 80, "source": "mock"}],
    }

    with patch("trendscope.server_api.settings.api_key_required", False):
        with patch(
            "trendscope.jobs.store.submit_analysis_job",
            return_value="abc123",
        ):
            resp = client.get("/trends", params={"topic": "ai", "async": "true"})

    assert resp.status_code == 202
    data = resp.json()
    assert data["job_id"] == "abc123"
    assert "poll" in data


def test_job_poll_not_found():
    from trendscope.server_api import app

    client = TestClient(app)
    with patch("trendscope.server_api.settings.api_key_required", False):
        resp = client.get("/jobs/does-not-exist")
    assert resp.status_code == 404


def test_job_lifecycle_with_mocked_pipeline(tmp_path):
    import trendscope.jobs.store as jobs_mod

    store = jobs_mod.reset_job_store(tmp_path / "jobs.db")
    job_id = store.create("trends", "ai", None, "CO")
    assert store.get(job_id)["status"] == "pending"

    store.mark_running(job_id)
    assert store.get(job_id)["status"] == "running"

    store.mark_done(job_id, "/tmp/x.json")
    job = store.get(job_id)
    assert job["status"] == "done"
    assert job["result_path"] == "/tmp/x.json"

    job_id2 = store.create("trends", "x", None, "CO")
    store.mark_error(job_id2, "boom")
    assert store.get(job_id2)["status"] == "error"


def test_submit_job_runs_pipeline(tmp_path):
    import trendscope.jobs.store as jobs_mod

    jobs_mod.reset_job_store(tmp_path / "jobs.db")

    payload = {
        "meta": {
            "query": {"topic": "ai", "geo": "CO"},
            "total_analyzed": 2,
            "sentiment_summary": {},
        },
        "top_trends": [],
    }

    with patch("trendscope.core.pipeline.run", return_value=(payload, "r")):
        with patch(
            "trendscope.output.exporter.export_json",
            return_value=tmp_path / "out.json",
        ):
            job_id = jobs_mod.submit_analysis_job("trends", "ai", None)
            # esperar a que termine
            for _ in range(50):
                job = jobs_mod.get_job_store().get(job_id)
                if job["status"] in {"done", "error"}:
                    break
                time.sleep(0.05)
            job = jobs_mod.get_job_store().get(job_id)

    assert job["status"] == "done", job
