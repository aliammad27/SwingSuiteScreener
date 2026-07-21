from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from scanner.storage.base import Storage


class PostgresStorage(Storage):
    """Durable JSON state backed by PostgreSQL or Supabase PostgreSQL."""

    def __init__(
        self,
        dsn: str | None = None,
        *,
        connect: Callable[..., Any] | None = None,
    ) -> None:
        resolved_dsn = dsn or os.environ.get("DATABASE_URL")
        if not resolved_dsn:
            raise RuntimeError("DATABASE_URL is required for PostgreSQL storage.")
        self.dsn = resolved_dsn
        if connect is None:
            import psycopg

            connect = psycopg.connect
        self._connect = connect
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scanner_state (
                        state_key TEXT PRIMARY KEY,
                        state_value JSONB NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

    def load_json(self, key: str) -> dict[str, Any]:
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT state_value FROM scanner_state WHERE state_key = %s",
                    (key,),
                )
                row = cursor.fetchone()
        if row is None:
            return {}
        raw = row[0]
        value = json.loads(raw) if isinstance(raw, str) else raw
        if not isinstance(value, dict):
            raise RuntimeError(f"PostgreSQL state for key {key!r} must contain a JSON object.")
        return {str(item_key): item_value for item_key, item_value in value.items()}

    def save_json(self, key: str, value: dict[str, Any]) -> None:
        payload = json.dumps(value, separators=(",", ":"), sort_keys=True)
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO scanner_state (state_key, state_value, updated_at)
                    VALUES (%s, %s::jsonb, CURRENT_TIMESTAMP)
                    ON CONFLICT (state_key) DO UPDATE
                    SET state_value = EXCLUDED.state_value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, payload),
                )
