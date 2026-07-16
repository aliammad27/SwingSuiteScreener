from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

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


def load_simple_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ConfigurationError(f"Configuration root must be a mapping: {path}")
    return {str(key): value for key, value in loaded.items()}


def load_config(name: str) -> dict[str, Any]:
    path = ROOT / "config" / f"{name}.yaml"
    if not path.exists():
        raise ConfigurationError(f"Missing configuration file: {path}")
    return load_simple_yaml(path)


def get_env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


def validate_configuration(fixture: bool = False) -> list[str]:
    load_local_env()
    required = ["strategy", "universe", "events", "schedule", "notifications", "providers", "storage"]
    warnings: list[str] = []
    for name in required:
        load_config(name)
    strategy = load_config("strategy")
    if strategy.get("schema_version") != 4:
        raise ConfigurationError("Strategy schema_version must be 4.")
    if strategy.get("direction") != "bullish_only":
        raise ConfigurationError("Bullish Participation v4 requires direction: bullish_only.")
    lanes = strategy.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != {"index_core", "leader_swing"}:
        raise ConfigurationError("Strategy must define index_core and leader_swing lanes.")
    for lane_name, raw_lane in lanes.items():
        if not isinstance(raw_lane, dict):
            raise ConfigurationError(f"Lane {lane_name} must be a mapping.")
        preferred_dte = raw_lane.get("preferred_dte")
        hard_dte = raw_lane.get("hard_dte")
        preferred_delta = raw_lane.get("preferred_delta")
        hard_delta = raw_lane.get("hard_delta")
        if not all(isinstance(value, list) and len(value) == 2 for value in (preferred_dte, hard_dte, preferred_delta, hard_delta)):
            raise ConfigurationError(f"Lane {lane_name} ranges must contain two values.")
        assert isinstance(preferred_dte, list)
        assert isinstance(hard_dte, list)
        assert isinstance(preferred_delta, list)
        assert isinstance(hard_delta, list)
        if int(preferred_dte[0]) < int(hard_dte[0]) or int(preferred_dte[1]) > int(hard_dte[1]):
            raise ConfigurationError(f"Lane {lane_name} preferred DTE must fit inside hard DTE.")
        if float(preferred_delta[0]) < float(hard_delta[0]) or float(preferred_delta[1]) > float(hard_delta[1]):
            raise ConfigurationError(f"Lane {lane_name} preferred delta must fit inside hard delta.")
    patterns = strategy.get("patterns")
    if not isinstance(patterns, dict) or not isinstance(patterns.get("enabled"), list):
        raise ConfigurationError("Strategy patterns.enabled must be a list.")
    enabled_patterns = [str(value) for value in patterns["enabled"]]
    if len(enabled_patterns) != len(set(enabled_patterns)):
        raise ConfigurationError("Strategy patterns.enabled must not contain duplicates.")
    if len(enabled_patterns) < 12:
        raise ConfigurationError("Bullish Participation v4 requires the full pattern library.")
    if not (ROOT / "CLAUDE.md").exists():
        raise ConfigurationError("Root CLAUDE.md is required.")
    if fixture:
        return warnings
    if not os.environ.get("ALPACA_API_KEY_ID") or not os.environ.get("ALPACA_API_SECRET_KEY"):
        warnings.append(
            "Live Alpaca credentials are not configured; live market scans are disabled."
        )
    if not os.environ.get("TELEGRAM_BOT_TOKEN") or not os.environ.get("TELEGRAM_CHAT_ID"):
        warnings.append(
            "Telegram token or chat id is not configured; live notifications are disabled."
        )
    if os.environ.get("ALPACA_OPTION_FEED", "indicative").lower() != "opra":
        warnings.append(
            "The configured option feed is not OPRA; candidates will require contract verification."
        )
    if not os.environ.get("MASSIVE_API_KEY"):
        warnings.append(
            "Historical option data is not configured; long-call optimization remains unvalidated."
        )
    return warnings
