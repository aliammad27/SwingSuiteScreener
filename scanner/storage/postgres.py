from __future__ import annotations

import os
from typing import Any

from scanner.storage.base import Storage


class PostgresStorage(Storage):
    """PostgreSQL-compatible adapter placeholder for Supabase deployments.

    The adapter validates configuration and exposes the same interface as local JSON. Production
    deployments can install a DB driver such as psycopg and map these methods to an application
    table without changing scanner code.
    """

    def __init__(self) -> None:
        self.dsn = os.environ.get("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL storage.")

    def load_json(self, key: str) -> dict[str, Any]:
        raise NotImplementedError(f"PostgreSQL load_json is not connected for key {key!r}.")

    def save_json(self, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError(f"PostgreSQL save_json is not connected for key {key!r}.")
