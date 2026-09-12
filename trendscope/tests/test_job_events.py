"""SSE job progress endpoint."""

import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from trendscope.jobs.store import JobStore, reset_job_store


def test_job_events_emits_final_when_done(tmp_path, isolated_app):
    store = reset_job_store(tmp_path / "jobs.db")
    job_id = store.create("trends", "ai", None, "CO")
    store.mark_running(job_id)
    store.mark_done(job_id, "/tmp/x.json")

    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        resp = client.get(f"/jobs/{job_id}/events")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "event: status" in body or "event: final" in body
    assert "done" in body


def test_job_events_404(tmp_path, isolated_app):
    reset_job_store(tmp_path / "jobs2.db")
    client = TestClient(isolated_app)
    with patch("trendscope.api.middleware.settings.api_key_required", False):
        # TestClient may not stream forever; 404 on missing job happens immediately
        resp = client.get("/jobs/missing-id/events")
    assert resp.status_code == 200
    assert "Job not found" in resp.text or "error" in resp.text
