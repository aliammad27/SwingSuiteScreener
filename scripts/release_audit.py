from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

REQUIRED_V5_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/intraday.yml",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "config/events.yaml",
    "config/notifications.yaml",
    "config/pine_parity.json",
    "config/providers.yaml",
    "config/schedule.yaml",
    "config/strategy.yaml",
    "config/universe.yaml",
    "pyproject.toml",
    "render.yaml",
    "AS_Weekly_Command_1D_v5.pine",
    "AS_Weekly_Timing_1H_v5.pine",
    "AS_Bullish_Pattern_Atlas_1D_v5.pine",
    "AS_Weekly_Screener_v5.pine",
    "AS_Weekly_Underlying_Research_v5.pine",
    "docs/Bullish_Weekly_Participation_v5_Build_Plan.md",
    "docs/Bullish_Weekly_Participation_v5_Training_Manual.md",
    "docs/Ali_Swing_Suite_Bullish_Weekly_Participation_v5_Training_Manual.docx",
    "docs/assets/v5_dashboard_desktop.png",
    "docs/assets/v5_pattern_atlas.png",
    "docs/assets/v5_pine_suite.png",
    "docs/assets/v5_workflow.png",
    "reports/intraday/.gitkeep",
    "scanner/data_trust.py",
    "scanner/intraday_schedule_gate.py",
    "scanner/providers/events.py",
    "scanner/timing.py",
    "scripts/run_intraday_refresh.sh",
)

ACTIVE_TEXT_FILES = (
    ".github/workflows/ci.yml",
    ".github/workflows/intraday.yml",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
    "config/notifications.yaml",
    "config/pine_parity.json",
    "config/providers.yaml",
    "config/schedule.yaml",
    "config/strategy.yaml",
    "config/universe.yaml",
    "pyproject.toml",
    "render.yaml",
    "docs/Bullish_Weekly_Participation_v5_Build_Plan.md",
    "docs/Bullish_Weekly_Participation_v5_Training_Manual.md",
    "scripts/run_intraday_refresh.sh",
)

PINE_FILES = (
    "AS_Weekly_Command_1D_v5.pine",
    "AS_Weekly_Timing_1H_v5.pine",
    "AS_Bullish_Pattern_Atlas_1D_v5.pine",
    "AS_Weekly_Screener_v5.pine",
    "AS_Weekly_Underlying_Research_v5.pine",
)

LEGACY_ACTIVE_PATTERNS = (
    re.compile(r"\bbullish(?: weekly)? participation v[1-4]\b", re.IGNORECASE),
    re.compile(r"\bAS_Command_1D_v4\.pine\b"),
    re.compile(r"\bAS_Momentum_4H_v4\.pine\b"),
    re.compile(r"\bScanType\.FOUR_HOUR\b"),
    re.compile(r"\bscanner\.run_scan four_hour\b"),
    re.compile(r"\breports/four_hour\b"),
    re.compile(r"\brun_four_hour_refresh\.sh\b"),
)

PRE_V5_ARTIFACT = re.compile(r"(?:^|[_-])v[1-4](?:[_\-.]|$)", re.IGNORECASE)
LEGACY_FOUR_HOUR_PATH = re.compile(
    r"(?:^|[/_-])four[_-]hour(?:[/_.-]|$)",
    re.IGNORECASE,
)

IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "tmp",
}

FORBIDDEN_EXECUTION_TOKENS = (
    "/v2/orders",
    "/v2/account",
    "/v2/positions",
    "submit_order",
    "place_order",
    "replace_order",
    "cancel_order",
    "get_account",
    "get_all_positions",
    "close_position",
    "exercise_options_position",
    "paper_trading",
    "live_trading",
)

EXPECTED_PRODUCTION_PATTERNS = {
    "ascending_triangle",
    "breakout_retest",
    "bull_flag",
    "confirmed_breakout",
    "controlled_pullback",
    "flat_base",
    "vcp_tight_base",
}

EXPECTED_CONTEXT_PATTERNS = {
    "cup_with_handle",
    "double_bottom",
    "falling_wedge",
    "inverse_head_and_shoulders",
    "rounding_base",
}


def _ignored(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    return any(part in IGNORED_DIRECTORY_NAMES for part in relative.parts)


def _check_required_files(root: Path, errors: list[str]) -> None:
    for relative in REQUIRED_V5_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required v5 file: {relative}")


def _check_active_text(root: Path, errors: list[str]) -> None:
    for relative in ACTIVE_TEXT_FILES:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in LEGACY_ACTIVE_PATTERNS:
            if pattern.search(text):
                errors.append(
                    f"Legacy active-strategy reference in {relative}: {pattern.pattern}"
                )


def _check_artifact_names(root: Path, errors: list[str]) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or _ignored(path, root):
            continue
        relative = path.relative_to(root)
        relative_text = relative.as_posix()
        if PRE_V5_ARTIFACT.search(path.name):
            errors.append(f"Pre-v5 artifact remains: {relative_text}")
        if LEGACY_FOUR_HOUR_PATH.search(relative_text):
            errors.append(f"Legacy four-hour artifact remains: {relative_text}")


def _check_strategy_config(root: Path, errors: list[str]) -> None:
    path = root / "config/strategy.yaml"
    if not path.is_file():
        return
    values = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(values, dict):
        errors.append("config/strategy.yaml must contain a mapping")
        return

    required_values = {
        "schema_version": 5,
        "profile_name": "Bullish Weekly Participation v5",
        "direction": "bullish_only",
        "validation_state": "research_default",
    }
    for key, expected in required_values.items():
        if values.get(key) != expected:
            errors.append(
                f"config/strategy.yaml {key} must be {expected!r}, "
                f"found {values.get(key)!r}"
            )

    patterns = values.get("patterns")
    if not isinstance(patterns, dict):
        errors.append("config/strategy.yaml patterns must contain a mapping")
    else:
        if set(patterns.get("production", ())) != EXPECTED_PRODUCTION_PATTERNS:
            errors.append("config/strategy.yaml production pattern registry is not v5")
        if set(patterns.get("context_only", ())) != EXPECTED_CONTEXT_PATTERNS:
            errors.append("config/strategy.yaml context-only pattern registry is not v5")
        if patterns.get("ready_distance_atr") != 0.30:
            errors.append("config/strategy.yaml ready_distance_atr must be 0.30")
        if patterns.get("maximum_confirmed_extension_atr") != 0.75:
            errors.append(
                "config/strategy.yaml maximum_confirmed_extension_atr must be 0.75"
            )
        if patterns.get("maximum_confirmed_age_bars") != 1:
            errors.append("config/strategy.yaml maximum_confirmed_age_bars must be 1")

    lanes = values.get("lanes")
    if not isinstance(lanes, dict) or set(lanes) != {
        "index_weekly",
        "leader_weekly",
    }:
        errors.append("config/strategy.yaml must define only the two v5 weekly lanes")


def _check_package_version(root: Path, errors: list[str]) -> None:
    path = root / "pyproject.toml"
    if path.is_file():
        values = tomllib.loads(path.read_text(encoding="utf-8"))
        version = values.get("project", {}).get("version")
        if version != "5.0.0":
            errors.append(f"pyproject.toml project.version must be '5.0.0', found {version!r}")

    package_init = root / "scanner/__init__.py"
    if package_init.is_file():
        text = package_init.read_text(encoding="utf-8")
        if '__version__ = "5.0.0"' not in text:
            errors.append('scanner/__init__.py must expose __version__ = "5.0.0"')


def _check_pine_contract(root: Path, errors: list[str]) -> None:
    forbidden_visual_tokens = ("plotshape(", "plotchar(", "label.", "table.")
    for relative in PINE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if not text.startswith("//@version=6\n"):
            errors.append(f"{relative} must use Pine v6")
        if "PARITY_SCHEMA_VERSION = 5" not in text:
            errors.append(f"{relative} must expose PARITY_SCHEMA_VERSION = 5")
        for token in forbidden_visual_tokens:
            if token in text:
                errors.append(
                    f"{relative} must remain label-free; found visual token {token!r}"
                )
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.strip().startswith("plot(") and "display =" not in line:
                errors.append(
                    f"{relative}:{line_number} must set an explicit plot display mode"
                )

    screener = root / "AS_Weekly_Screener_v5.pine"
    if screener.is_file():
        text = screener.read_text(encoding="utf-8")
        request_count = len(re.findall(r"\brequest\.[A-Za-z_]+\s*\(", text))
        plot_count = len(re.findall(r"(?m)^\s*plot\s*\(", text))
        if request_count > 5:
            errors.append(
                f"AS_Weekly_Screener_v5.pine uses {request_count} request calls; maximum is 5"
            )
        if plot_count < 10:
            errors.append(
                f"AS_Weekly_Screener_v5.pine exposes {plot_count} plots; at least 10 required"
            )
        if text.count("display.pine_screener") != 10:
            errors.append(
                "AS_Weekly_Screener_v5.pine must expose exactly ten data-only "
                "Pine Screener plots"
            )
        if "input.symbol(" in text:
            errors.append(
                "AS_Weekly_Screener_v5.pine cannot use input.symbol because "
                "Pine Screener ignores symbol inputs"
            )

    tester = root / "AS_Weekly_Underlying_Research_v5.pine"
    if tester.is_file():
        text = tester.read_text(encoding="utf-8")
        if "NOT OPTION PERFORMANCE" not in text:
            errors.append(
                "AS_Weekly_Underlying_Research_v5.pine must retain its proxy warning"
            )

    atlas = root / "AS_Bullish_Pattern_Atlas_1D_v5.pine"
    if atlas.is_file():
        for line_number, line in enumerate(
            atlas.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if "ta." not in line:
                continue
            if "?" in line or line.lstrip().startswith(("if ", "else if ", "bool ")):
                errors.append(
                    "AS_Bullish_Pattern_Atlas_1D_v5.pine:"
                    f"{line_number} must calculate history functions unconditionally"
                )


def _check_no_execution(root: Path, errors: list[str]) -> None:
    scanner_root = root / "scanner"
    if not scanner_root.is_dir():
        return
    for path in scanner_root.rglob("*.py"):
        if _ignored(path, root):
            continue
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_EXECUTION_TOKENS:
            if token in text:
                errors.append(f"Execution token {token!r} found in {path.relative_to(root)}")


def run_release_audit(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    _check_required_files(root, errors)
    _check_active_text(root, errors)
    _check_artifact_names(root, errors)
    _check_strategy_config(root, errors)
    _check_package_version(root, errors)
    _check_pine_contract(root, errors)
    _check_no_execution(root, errors)
    return errors


def main() -> int:
    errors = run_release_audit()
    if errors:
        print("Release audit failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Bullish Weekly Participation v5 release audit passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
