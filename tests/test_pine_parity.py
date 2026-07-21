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
        "AS_Weekly_Command_1D_v5.pine",
        "AS_Weekly_Timing_1H_v5.pine",
        "AS_Bullish_Pattern_Atlas_1D_v5.pine",
    ):
        source = ROOT / relative_path
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source.read_text())
    command_path = tmp_path / "AS_Weekly_Command_1D_v5.pine"
    command_path.write_text(
        command_path.read_text().replace(
            "const int PARITY_TREND_MINIMUM = 80",
            "const int PARITY_TREND_MINIMUM = 79",
        )
    )
    assert any("PARITY_TREND_MINIMUM" in error for error in check_parity(tmp_path))


def test_pine_indicator_suite_is_bullish_v5_and_non_repainting() -> None:
    paths = (
        "AS_Weekly_Command_1D_v5.pine",
        "AS_Weekly_Timing_1H_v5.pine",
        "AS_Bullish_Pattern_Atlas_1D_v5.pine",
    )
    files = {path: (ROOT / path).read_text(encoding="utf-8") for path in paths}
    suite = "\n".join(files.values())
    assert all(payload.startswith("//@version=6") for payload in files.values())
    assert all("\nindicator(" in payload for payload in files.values())
    assert "strategy(" not in suite
    assert not re.search(r"\bput\b", suite, re.IGNORECASE)
    assert not re.search(r"\bv[1-4]\b", suite, re.IGNORECASE)
    assert "lookahead = barmerge.lookahead_on" in suite
    assert "[1]" in suite
    assert "barstate.isconfirmed" in suite
    assert "Ready - Verify" in files["AS_Weekly_Command_1D_v5.pine"]
    assert "Research default" in files["AS_Weekly_Command_1D_v5.pine"]
    assert 'timeframe.period == "1D"' in files["AS_Weekly_Command_1D_v5.pine"]
    assert 'timeframe.period == "60"' in files["AS_Weekly_Timing_1H_v5.pine"]
    assert 'timeframe.period == "1D"' in files["AS_Bullish_Pattern_Atlas_1D_v5.pine"]
    assert 'timeframe.period == "D"' not in suite
    assert "[close, ta.sma(close, 50), ta.sma(close, 200)]" in files[
        "AS_Weekly_Command_1D_v5.pine"
    ]
    assert "[close, ta.ema(close, 9), ta.ema(close, 21)]" in files[
        "AS_Weekly_Timing_1H_v5.pine"
    ]
    assert "and intradayMarketAligned and timingScore" in files[
        "AS_Weekly_Timing_1H_v5.pine"
    ]
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
        assert pattern in files["AS_Bullish_Pattern_Atlas_1D_v5.pine"]
    assert not (ROOT / "AS_Weekly_Screener_v5.pine").exists()
    assert not (ROOT / "AS_Weekly_Underlying_Research_v5.pine").exists()


def test_pine_indicator_suite_has_compact_tables_without_chart_markers_or_warnings() -> None:
    paths = (
        "AS_Weekly_Command_1D_v5.pine",
        "AS_Weekly_Timing_1H_v5.pine",
        "AS_Bullish_Pattern_Atlas_1D_v5.pine",
    )
    insight_contract = {
        "AS_Weekly_Command_1D_v5.pine": ("position.top_right", 18),
        "AS_Weekly_Timing_1H_v5.pine": ("position.top_right", 18),
        "AS_Bullish_Pattern_Atlas_1D_v5.pine": ("position.bottom_right", 16),
    }
    forbidden = ("plotshape(", "plotchar(", "label.")
    for relative_path in paths:
        payload = (ROOT / relative_path).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in payload, f"{relative_path} contains visual clutter: {token}"
        expected_position, expected_cells = insight_contract[relative_path]
        assert payload.count("table.new(") == 1
        assert payload.count("table.cell(") == expected_cells
        assert expected_position in payload
        assert 'showInsights = input.bool(true, "Show quick insights"' in payload
        assert "if barstate.islast and showInsights" in payload
        for line in payload.splitlines():
            if line.strip().startswith("plot("):
                assert "display =" in line, (
                    f"{relative_path} has a plot that can leak into the status line "
                    "or price scale"
                )

    command = (ROOT / "AS_Weekly_Command_1D_v5.pine").read_text(encoding="utf-8")
    timing = (ROOT / "AS_Weekly_Timing_1H_v5.pine").read_text(encoding="utf-8")
    atlas = (ROOT / "AS_Bullish_Pattern_Atlas_1D_v5.pine").read_text(
        encoding="utf-8"
    )
    assert "showPlanningLevels = input.bool(false" in command
    assert "Show current tactical levels" in timing
    assert "float priorLowestLowRaw = ta.lowest(low[1], 4)" in timing
    assert "float tacticalFailure = priorLowestLow" in timing
    assert 'includeContextPatterns = input.bool(false' in atlas
    for relative_path in paths:
        payload = (ROOT / relative_path).read_text(encoding="utf-8")
        for line in payload.splitlines():
            if "ta." in line:
                assert "?" not in line, (
                    f"{relative_path} history functions must be calculated before "
                    "completed-bar selection"
                )
                assert not line.lstrip().startswith(("if ", "else if ", "bool ")), (
                    f"{relative_path} history functions must run unconditionally"
                )


def test_production_command_excludes_context_only_patterns() -> None:
    command = (ROOT / "AS_Weekly_Command_1D_v5.pine").read_text(encoding="utf-8")
    for pattern in (
        "controlled_pullback",
        "confirmed_breakout",
        "bull_flag",
        "breakout_retest",
        "flat_base",
        "vcp_tight_base",
        "ascending_triangle",
    ):
        assert pattern in command
    for pattern in (
        "cup_with_handle",
        "double_bottom",
        "inverse_head_and_shoulders",
        "falling_wedge",
        "rounding_base",
    ):
        assert pattern not in command
