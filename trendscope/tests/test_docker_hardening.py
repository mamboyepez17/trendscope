"""Static checks for Docker hardening (no docker daemon required)."""

from pathlib import Path


def test_dockerfile_is_multi_stage():
    text = Path("Dockerfile").read_text(encoding="utf-8").lower()
    assert "as build" in text
    assert text.count("from python") >= 2
    assert "user trendscope" in text or "useradd" in text


def test_dockerfile_has_no_dev_extras():
    text = Path("Dockerfile").read_text(encoding="utf-8")
    assert "[dev]" not in text
    assert "-e ." not in text.replace("-e \"", "")


def test_dockerfile_has_healthcheck():
    text = Path("Dockerfile").read_text(encoding="utf-8").upper()
    assert "HEALTHCHECK" in text


def test_compose_hardening():
    text = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "read_only: true" in text
    assert "cap_drop" in text
    assert "no-new-privileges" in text
    assert "healthcheck" in text
    assert "mem_limit" in text
