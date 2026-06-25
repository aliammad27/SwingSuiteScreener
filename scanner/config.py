from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(RuntimeError):
    pass


def load_local_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _parse_scalar(value: str) -> Any:
    clean = value.strip().strip('"').strip("'")
    if clean.lower() in {"true", "false"}:
        return clean.lower() == "true"
    if clean == "":
        return ""
    try:
        return int(clean)
    except ValueError:
        try:
            return float(clean)
        except ValueError:
            return clean


def load_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(_parse_scalar(line[4:]))
            continue
        if line.startswith("  ") and current_key and isinstance(data.get(current_key), dict):
            key, value = line.strip().split(":", 1)
            data[current_key][key.strip()] = _parse_scalar(value)
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value == "":
            next_is_map = key in {"notify_on", "alpaca"}
            data[key] = {} if next_is_map else []
        else:
            data[key] = _parse_scalar(value)
    return data


def load_config(name: str) -> dict[str, Any]:
    path = ROOT / "config" / f"{name}.yaml"
    if not path.exists():
        raise ConfigurationError(f"Missing configuration file: {path}")
    return load_simple_yaml(path)


def get_env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def validate_configuration(fixture: bool = False) -> list[str]:
    load_local_env()
    required = [
        "strategy",
        "universe",
        "schedule",
        "notifications",
        "providers",
        "storage",
    ]
    warnings: list[str] = []
    for name in required:
        load_config(name)
    if not (ROOT / "CLAUDE.md").exists():
        raise ConfigurationError("Root CLAUDE.md is required.")
    if fixture:
        return warnings
    if not os.environ.get("ALPACA_API_KEY_ID") or not os.environ.get("ALPACA_API_SECRET_KEY"):
        warnings.append("Live Alpaca credentials are not configured; live market scans are disabled.")
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        warnings.append("Telegram token or chat id is not configured; live notifications are disabled.")
    return warnings
