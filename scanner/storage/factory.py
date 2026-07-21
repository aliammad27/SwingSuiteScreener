from __future__ import annotations

import os
from pathlib import Path

from scanner.config import ROOT, ConfigurationError, load_config
from scanner.storage.base import Storage
from scanner.storage.local_json import LocalJsonStorage


def configured_storage() -> Storage:
    config = load_config("storage")
    backend = os.environ.get("STORAGE_BACKEND", str(config.get("backend", "local_json")))
    if backend == "local_json":
        configured_path = Path(str(config.get("local_state_path", "data/state")))
        base_path = configured_path if configured_path.is_absolute() else ROOT / configured_path
        return LocalJsonStorage(base_path)
    if backend == "postgres":
        from scanner.storage.postgres import PostgresStorage

        dsn_env = str(config.get("postgres_dsn_env", "DATABASE_URL"))
        return PostgresStorage(os.environ.get(dsn_env))
    raise ConfigurationError(
        f"Unsupported storage backend {backend!r}; expected 'local_json' or 'postgres'."
    )
