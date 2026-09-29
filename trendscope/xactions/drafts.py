"""
XActions-PY — Write drafts + human approval gate.

When enabled (env XACTIONS_REQUIRE_APPROVAL=1 or explicit flag), write
actions are saved as drafts instead of hitting X. A human lists and
approves them; only then the action runs.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)

DEFAULT_DRAFTS_DIR = Path(os.getenv("XACTIONS_HOME", str(Path.home() / ".xactions"))) / "drafts"

APPROVAL_ENV = "XACTIONS_REQUIRE_APPROVAL"


def approval_required() -> bool:
    return os.getenv(APPROVAL_ENV, "").strip().lower() in {"1", "true", "yes"}


def _drafts_dir(path: Path | str | None = None) -> Path:
    return Path(path) if path else DEFAULT_DRAFTS_DIR


def create_draft(
    action: str,
    params: dict[str, Any],
    account: str = "default",
    path: Path | str | None = None,
) -> dict[str, Any]:
    """Persist a pending write. Returns the draft dict."""
    d = _drafts_dir(path)
    d.mkdir(parents=True, exist_ok=True)
    draft_id = uuid.uuid4().hex[:12]
    draft = {
        "id": draft_id,
        "action": action,
        "params": params,
        "account": account,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    (d / f"{draft_id}.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _log.info("Draft saved: %s %s", action, draft_id)
    return draft


def load_draft(draft_id: str, path: Path | str | None = None) -> dict[str, Any] | None:
    p = _drafts_dir(path) / f"{draft_id}.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_draft(draft: dict[str, Any], path: Path | str | None = None) -> None:
    draft["updated_at"] = time.time()
    d = _drafts_dir(path)
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{draft['id']}.json").write_text(
        json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_drafts(
    status: str | None = "pending",
    path: Path | str | None = None,
) -> list[dict[str, Any]]:
    d = _drafts_dir(path)
    if not d.exists():
        return []
    out: list[dict[str, Any]] = []
    for p in sorted(d.glob("*.json")):
        try:
            draft = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if status is None or draft.get("status") == status:
            out.append(draft)
    out.sort(key=lambda x: x.get("created_at") or 0)
    return out


def mark_status(draft_id: str, status: str, path: Path | str | None = None) -> dict[str, Any] | None:
    draft = load_draft(draft_id, path)
    if not draft:
        return None
    draft["status"] = status
    save_draft(draft, path)
    return draft


def approve(draft_id: str, path: Path | str | None = None) -> dict[str, Any] | None:
    return mark_status(draft_id, "approved", path)


def discard(draft_id: str, path: Path | str | None = None) -> dict[str, Any] | None:
    return mark_status(draft_id, "discarded", path)


def get_approved_to_run(draft_id: str, path: Path | str | None = None) -> dict[str, Any] | None:
    """Return draft if approved and not yet executed."""
    draft = load_draft(draft_id, path)
    if draft and draft.get("status") == "approved":
        return draft
    return None


def mark_executed(draft_id: str, result: dict[str, Any] | None = None, path: Path | str | None = None) -> None:
    draft = load_draft(draft_id, path)
    if not draft:
        return
    draft["status"] = "executed"
    if result is not None:
        draft["result"] = result
    save_draft(draft, path)


async def maybe_draft_or_run(
    action_name: str,
    params: dict[str, Any],
    runner,
    account: str = "default",
    drafts_path: Path | str | None = None,
) -> dict[str, Any]:
    """
    If approval is required, save a draft and return {drafted: True, draft}.
    Else await runner(**params) and return its result with drafted=False.
    """
    if approval_required():
        draft = create_draft(action_name, params, account=account, path=drafts_path)
        return {"drafted": True, "draft": draft, "success": True}
    result = await runner(**params)
    if isinstance(result, dict):
        return {**result, "drafted": False}
    return {"success": True, "drafted": False, "result": result}
