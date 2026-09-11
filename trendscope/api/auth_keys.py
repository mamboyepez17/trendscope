"""Multi-tenant API keys with scopes (JSON store — SQLite optional later).

Formato de API_KEYS en settings (compat):
  - Simple: "key1,key2"  → scope total, org "default"
  - Con scopes: "key1|orgA|trends:read+watchlist:write,key2|orgB|trends:read"

Si no hay scopes, se asume acceso completo (compatibilidad).
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass, field


ALL_SCOPES = frozenset(
    {
        "trends:read",
        "watchlist:write",
        "watchlist:read",
        "admin",
        "jobs:read",
    }
)


@dataclass(frozen=True)
class ApiKey:
    key: str
    org_id: str = "default"
    scopes: frozenset[str] = field(default_factory=lambda: ALL_SCOPES)

    def allows(self, scope: str) -> bool:
        if "admin" in self.scopes:
            return True
        return scope in self.scopes


def parse_api_keys(raw: str) -> list[ApiKey]:
    """Parsea API_KEYS. Soporta formato legacy 'k1,k2' y 'k|org|scope+scope'."""
    if not raw:
        return []
    keys: list[ApiKey] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "|" in part:
            bits = part.split("|")
            key = bits[0].strip()
            org = (bits[1].strip() if len(bits) > 1 and bits[1].strip() else "default")
            scopes_raw = bits[2].strip() if len(bits) > 2 else ""
            if scopes_raw:
                scopes = frozenset(s.strip() for s in scopes_raw.split("+") if s.strip())
            else:
                scopes = ALL_SCOPES
            if key:
                keys.append(ApiKey(key=key, org_id=org, scopes=scopes))
        else:
            keys.append(ApiKey(key=part))
    return keys


def match_key(raw_keys: str, provided: str | None) -> ApiKey | None:
    """Devuelve la ApiKey si el token es válido (comparación constant-time)."""
    if not provided:
        return None
    for candidate in parse_api_keys(raw_keys):
        if hmac.compare_digest(provided, candidate.key):
            return candidate
    return None
