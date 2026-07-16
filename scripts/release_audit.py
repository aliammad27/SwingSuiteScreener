from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ACTIVE_TEXT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "config/strategy.yaml",
    "config/notifications.yaml",
    "AS_Command_1D_v4.pine",
    "AS_Momentum_4H_v4.pine",
)

LEGACY_PATTERNS = (
    re.compile(r"bullish participation v[123]\b", re.IGNORECASE),
    re.compile(r"\bversion (?:one|two|three)\b", re.IGNORECASE),
)

FORBIDDEN_EXECUTION_TOKENS = (
    "/v2/orders",
    "/v2/account",
    "/v2/positions",
    "submit_order",
    "place_order",
    "cancel_order",
    "paper_trading",
    "live_trading",
)


def run_release_audit(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative in ACTIVE_TEXT_FILES:
        path = root / relative
        if not path.exists():
            errors.append(f"Missing active v4 file: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in LEGACY_PATTERNS:
            if pattern.search(text):
                errors.append(f"Legacy strategy reference in {relative}: {pattern.pattern}")
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if re.search(r"(?:^|[_-])v[123](?:[_\-.]|$)", path.name, re.IGNORECASE):
            errors.append(f"Pre-v4 artifact remains: {path.relative_to(root)}")
    scanner_root = root / "scanner"
    for path in scanner_root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_EXECUTION_TOKENS:
            if token in text:
                errors.append(f"Execution token {token!r} found in {path.relative_to(root)}")
    return errors


def main() -> int:
    errors = run_release_audit()
    if errors:
        print("Release audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Bullish Participation v4 release audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
