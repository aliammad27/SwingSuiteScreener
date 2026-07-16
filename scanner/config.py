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
    if strategy.get("schema_version") != 5:
        raise ConfigurationError("Strategy schema_version must be 5.")
    if strategy.get("direction") != "bullish_only":
        raise ConfigurationError(
            "Bullish Weekly Participation v5 requires direction: bullish_only."
        )
    if strategy.get("validation_state") != "research_default":
        raise ConfigurationError("V5 must launch with validation_state: research_default.")
    lanes = strategy.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != {
        "index_weekly",
        "leader_weekly",
    }:
        raise ConfigurationError(
            "Strategy must define index_weekly and leader_weekly lanes."
        )
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
    if (
        not isinstance(patterns, dict)
        or not isinstance(patterns.get("production"), list)
        or not isinstance(patterns.get("context_only"), list)
    ):
        raise ConfigurationError(
            "Strategy patterns.production and patterns.context_only must be lists."
        )
    production = [str(value) for value in patterns["production"]]
    context_only = [str(value) for value in patterns["context_only"]]
    if len(production) != 7 or len(context_only) != 5:
        raise ConfigurationError("V5 requires seven production and five context patterns.")
    all_patterns = production + context_only
    if len(all_patterns) != len(set(all_patterns)):
        raise ConfigurationError("Strategy pattern lists must not contain duplicates.")
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
    if os.environ.get("ALPACA_FEED", "sip").lower() != "sip":
        warnings.append(
            "The configured stock feed is not SIP; candidates will require data verification."
        )
    if os.environ.get("ALPACA_OPTION_FEED", "opra").lower() != "opra":
        warnings.append(
            "The configured option feed is not OPRA; candidates will require contract verification."
        )
    if not os.environ.get("MASSIVE_API_KEY"):
        warnings.append(
            "Historical option data is not configured; long-call optimization remains unvalidated."
        )
    return warnings
