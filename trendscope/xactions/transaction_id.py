"""
XActions-PY — x-client-transaction-id generation.

X's web client signs GraphQL calls with a transaction id. We cannot fully
replicate the browser's RSA/animation pipeline without shipping their JS
bundle, but we do bind the id to method+path+time with a random key so it
is not a bare uuid4.

Format: 26-char URL-safe-ish token (A-Za-z0-9), similar length to the
browser header.

Env: XACTIONS_TXID_MODE=uuid (legacy) | bound (default)
"""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
import time
import uuid


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def generate_transaction_id(
    method: str = "GET",
    path: str = "/",
    *,
    now: float | None = None,
    mode: str | None = None,
) -> str:
    """
    Create an x-client-transaction-id value.
    mode: 'bound' (default) or 'uuid' (v1.5 behaviour).
    """
    mode = (mode or os.getenv("XACTIONS_TXID_MODE", "bound")).lower()
    if mode == "uuid":
        return str(uuid.uuid4())

    now = now if now is not None else time.time()
    key = secrets.token_bytes(16)
    # 4-byte time bucket (reduces identical ids in the same second)
    ts = int(now).to_bytes(4, "big")
    msg = f"{method.upper()}|{path}|".encode() + ts
    digest = hashlib.sha256(key + msg).digest()
    # Mix key material so two clients rarely collide
    mixed = bytes(a ^ b for a, b in zip(key, digest[:16], strict=True))
    token = _b64(mixed + digest[16:20])
    # Browser ids are typically ~26-28 chars; trim/pad softly
    return token[:28]
