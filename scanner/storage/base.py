from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Storage(ABC):
    @abstractmethod
    def load_json(self, key: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def save_json(self, key: str, value: dict[str, Any]) -> None:
        raise NotImplementedError
