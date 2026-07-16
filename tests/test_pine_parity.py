import re
from pathlib import Path

import pytest

from scripts.check_pine_parity import check_parity

ROOT = Path(__file__).resolve().parents[1]


def test_pine_defaults_match_strategy_profile() -> None:
    errors = check_parity(ROOT)
    assert not errors


def test_parity_check_detects_drift(tmp_path) -> None:
    pytest.importorskip("yaml")
    for relative_path in (
        "config/strategy.yaml",
        "config/pine_parity.json",
        "AS_Command_1D_v4.pine",
        "AS_Momentum_4H_v4.pine",
    ):
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text())
    command_path = tmp_path / "AS_Command_1D_v4.pine"
    command_path.write_text(
        command_path.read_text().replace(
            "const int PARITY_TREND_MINIMUM = 80",
            "const int PARITY_TREND_MINIMUM = 79",
        )
    )
    assert any("PARITY_TREND_MINIMUM" in error for error in check_parity(tmp_path))


def test_pine_suite_is_bullish_v4_and_non_repainting() -> None:
    command = (ROOT / "AS_Command_1D_v4.pine").read_text(encoding="utf-8")
    momentum = (ROOT / "AS_Momentum_4H_v4.pine").read_text(encoding="utf-8")
    suite = command + momentum
    assert command.startswith("//@version=6")
    assert momentum.startswith("//@version=6")
    assert "AS_Bullish_Patterns" not in suite
    assert not re.search(r"\bput\b", suite, re.IGNORECASE)
    assert not re.search(r"\bv[123]\b", suite, re.IGNORECASE)
    assert suite.count("request.security(") <= 5
    assert "lookahead = barmerge.lookahead_on" in suite
    assert "[1]" in suite
    assert "close > ema21 + PARITY_MAX_EXTENSION_ATR * currentAtr" in command
    assert 'syminfo.ticker == "SPY" or syminfo.ticker == "QQQ"' in command
    assert "bool leadershipPass = indexCore or" in command
    assert 'patternStale ? "Stale"' in command
    for pattern in (
        "controlled_pullback",
        "confirmed_breakout",
        "bull_flag",
        "flat_base",
        "ascending_triangle",
        "vcp_tight_base",
        "cup_with_handle",
        "breakout_retest",
        "double_bottom",
        "inverse_head_and_shoulders",
        "falling_wedge",
        "rounding_base",
    ):
        assert pattern in command
