from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONSTANT_PATTERN = r"^\s*const\s+(?:int|float)\s+{name}\s*=\s*(-?\d+(?:\.\d+)?)\s*$"


def _nested_value(payload: dict[str, Any], path: str) -> int | float:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"Missing strategy config path: {path}")
        value = value[part]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"Parity path must resolve to a number: {path}")
    return value


def check_parity(root: Path = ROOT) -> list[str]:
    manifest = json.loads((root / "config" / "pine_parity.json").read_text())
    strategy = yaml.safe_load((root / manifest["strategy_config"]).read_text())
    errors: list[str] = []
    for check in manifest["checks"]:
        expected = Decimal(str(_nested_value(strategy, check["config_path"])))
        pattern = re.compile(
            CONSTANT_PATTERN.format(name=re.escape(check["constant"])),
            re.MULTILINE,
        )
        for relative_path in check["pine_files"]:
            pine_path = root / relative_path
            if not pine_path.exists():
                errors.append(f"{relative_path}: file is missing")
                continue
            match = pattern.search(pine_path.read_text())
            if match is None:
                errors.append(f"{relative_path}: missing {check['constant']}")
                continue
            actual = Decimal(match.group(1))
            if actual != expected:
                errors.append(
                    f"{relative_path}: {check['constant']}={actual} but "
                    f"{check['config_path']}={expected}"
                )
    return errors


def main() -> int:
    errors = check_parity()
    if errors:
        print("Pine parity check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Pine defaults match config/strategy.yaml.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
