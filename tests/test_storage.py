from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scanner.config import ConfigurationError
from scanner.storage.factory import configured_storage
from scanner.storage.local_json import LocalJsonStorage
from scanner.storage.postgres import PostgresStorage


def test_local_json_storage_round_trips_atomically(tmp_path: Path) -> None:
    storage = LocalJsonStorage(tmp_path)
    storage.save_json("notification_state", {"sent": {"abc": True}})

    assert storage.load_json("notification_state") == {"sent": {"abc": True}}
    assert list(tmp_path.glob("*.tmp")) == []


def test_local_json_storage_rejects_unsafe_keys_and_corrupt_state(
    tmp_path: Path,
) -> None:
    storage = LocalJsonStorage(tmp_path)
    with pytest.raises(ValueError, match="Storage keys"):
        storage.save_json("../outside", {})
    (tmp_path / "broken.json").write_text("not-json", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Unable to load local state"):
        storage.load_json("broken")


class FakeCursor:
    def __init__(self, database: dict[str, Any]) -> None:
        self.database = database
        self.row: tuple[Any, ...] | None = None

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        if "SELECT state_value" in query:
            assert params is not None
            value = self.database.get(str(params[0]))
            self.row = None if value is None else (value,)
        elif "INSERT INTO scanner_state" in query:
            assert params is not None
            self.database[str(params[0])] = json.loads(str(params[1]))

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.row


class FakeConnection:
    def __init__(self, database: dict[str, Any]) -> None:
        self.database = database

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self.database)


def test_postgres_storage_creates_schema_and_round_trips_json() -> None:
    database: dict[str, Any] = {}
    storage = PostgresStorage(
        "postgresql://test",
        connect=lambda dsn: FakeConnection(database),
    )
    storage.save_json("notification_state", {"sent": {"abc": True}})

    assert storage.load_json("notification_state") == {"sent": {"abc": True}}


def test_storage_factory_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "unknown")
    with pytest.raises(ConfigurationError, match="Unsupported storage backend"):
        configured_storage()
