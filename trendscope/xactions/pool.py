"""
XActions-PY — ClientPool
Pool de clientes con rotación de cookies (multi-cuenta).

Cuando una cuenta pega rate limit (429) o sus cookies mueren (401/403),
el pool rota automáticamente a la siguiente cuenta disponible.

Uso:
    pool = ClientPool([cookies1, cookies2, cookies3])
    profile = await scrape_profile(pool, "elonmusk")   # compatible con scrapers
    await pool.aclose()
"""

from __future__ import annotations

import logging
from typing import Any

from .client import AuthError, ForbiddenError, RateLimitError, TwitterClient, TwitterError

_log = logging.getLogger(__name__)


class ClientPool:
    """
    Pool round-robin de TwitterClient.

    Expone la misma interfaz que TwitterClient (`graphql`, `rest_get`,
    `rest_post`, `is_authenticated`, `validate_cookies`, `aclose`), por lo
    que puede pasarse a cualquier scraper/acción en lugar de un cliente.
    """

    def __init__(
        self,
        cookies_list: list[str] | None = None,
        proxy: str | None = None,
        max_retries: int = 3,
        clients: list[TwitterClient] | None = None,
    ):
        if clients is not None:
            self._clients = list(clients)
        else:
            if not cookies_list:
                raise ValueError("ClientPool requiere al menos un string de cookies")
            self._clients = [
                TwitterClient(cookies=c, proxy=proxy, max_retries=max_retries)
                for c in cookies_list
                if c and c.strip()
            ]
        if not self._clients:
            raise ValueError("ClientPool quedó sin clientes válidos")
        self._idx = 0
        self._dead: set[int] = set()

    # ─── Gestión del pool ─────────────────────────────────────────────────────

    @property
    def current(self) -> TwitterClient:
        return self._clients[self._idx]

    @property
    def size(self) -> int:
        return len(self._clients)

    @property
    def alive(self) -> int:
        return self.size - len(self._dead)

    def _rotate(self) -> None:
        """Avanza a la siguiente cuenta viva. Lanza TwitterError si no hay ninguna."""
        if self.alive <= 0:
            raise TwitterError("Todas las cuentas del pool están agotadas (rate limit o cookies inválidas)")
        for _ in range(self.size):
            self._idx = (self._idx + 1) % self.size
            if self._idx not in self._dead:
                return

    def mark_dead(self) -> None:
        """Marca la cuenta actual como inválida y rota."""
        _log.warning("ClientPool: marcando cuenta #%d como muerta", self._idx)
        self._dead.add(self._idx)
        self._rotate()

    # ─── Interfaz compatible con TwitterClient ────────────────────────────────

    def is_authenticated(self) -> bool:
        return self.current.is_authenticated()

    async def _execute(self, method_name: str, *args, **kwargs) -> Any:
        """
        Ejecuta un método del cliente actual con rotación automática
        ante rate limits y errores de autenticación.
        """
        last_exc: Exception | None = None
        attempts = self.size

        for _ in range(attempts):
            method = getattr(self.current, method_name)
            try:
                return await method(*args, **kwargs)
            except RateLimitError as e:
                last_exc = e
                _log.warning("ClientPool: rate limit en cuenta #%d, rotando", self._idx)
                self._rotate()
            except (AuthError, ForbiddenError) as e:
                last_exc = e
                self.mark_dead()

        raise last_exc or TwitterError("ClientPool: todas las cuentas fallaron")

    async def graphql(self, *args, **kwargs) -> dict[str, Any]:
        return await self._execute("graphql", *args, **kwargs)

    async def rest_get(self, *args, **kwargs) -> dict[str, Any]:
        return await self._execute("rest_get", *args, **kwargs)

    async def rest_post(self, *args, **kwargs) -> dict[str, Any]:
        return await self._execute("rest_post", *args, **kwargs)

    async def rest_upload(self, *args, **kwargs) -> dict[str, Any]:
        return await self._execute("rest_upload", *args, **kwargs)

    async def validate_cookies(self) -> dict[str, Any]:
        """Valida todas las cuentas del pool y devuelve el resumen."""
        results = []
        for i, client in enumerate(self._clients):
            if i in self._dead:
                results.append({"account": i, "valid": False, "error": "marked dead"})
                continue
            try:
                res = await client.validate_cookies()
                results.append({"account": i, **res})
                if not res.get("valid"):
                    self._dead.add(i)
            except Exception as e:  # noqa: BLE001 — validación best-effort
                results.append({"account": i, "valid": False, "error": str(e)})
                self._dead.add(i)
        # Dejar el índice apuntando a una cuenta viva
        if self._idx in self._dead and self.alive > 0:
            self._rotate()
        return {
            "total": self.size,
            "alive": self.alive,
            "accounts": results,
        }

    # ─── Ciclo de vida ────────────────────────────────────────────────────────

    async def aclose(self) -> None:
        for client in self._clients:
            await client.aclose()

    async def __aenter__(self) -> ClientPool:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()
