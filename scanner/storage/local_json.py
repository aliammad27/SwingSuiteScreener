from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scanner.config import ROOT
from scanner.storage.base import Storage


class LocalJsonStorage(Storage):
    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or ROOT / "data" / "state"
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = key.replace("/", "_")
        return self.base_path / f"{safe}.json"

    def load_json(self, key: str) -> dict[str, Any]:
        path = self._path(key)
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {}
        return data

    def save_json(self, key: str, value: dict[str, Any]) -> None:
        self._path(key).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
