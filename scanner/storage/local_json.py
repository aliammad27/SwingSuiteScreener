from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scanner.config import ROOT
from scanner.storage.base import Storage


class LocalJsonStorage(Storage):
    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or ROOT / "data" / "state"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        if not key or any(
            character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
            for character in key
        ):
            raise ValueError(
                "Storage keys may contain only letters, numbers, dots, dashes, and underscores."
            )
        return self.base_path / f"{key}.json"

    def load_json(self, key: str) -> dict[str, Any]:
        path = self._path(key)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to load local state for key {key!r}.") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"Local state for key {key!r} must contain a JSON object.")
        return data

    def save_json(self, key: str, value: dict[str, Any]) -> None:
        path = self._path(key)
        payload = json.dumps(value, indent=2, sort_keys=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.base_path,
                prefix=f".{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Unable to save local state for key {key!r}.") from exc
