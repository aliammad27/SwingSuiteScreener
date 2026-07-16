from scanner.config import ROOT, load_config, validate_configuration
from scanner.models import StrategyLane
from scanner.strategy_profile import PROFILE
from scanner.universe import configured_symbols, leader_metadata


def test_root_engineering_contract_present() -> None:
    assert (ROOT / "AGENTS.md").exists()
    assert (ROOT / "CLAUDE.md").exists()


def test_configuration_valid_fixture() -> None:
    assert validate_configuration(fixture=True) == []
    assert load_config("universe")["options_required"] is True


def test_bullish_weekly_v5_lanes_are_authoritative() -> None:
    assert PROFILE.schema_version == 5
    assert PROFILE.name == "Bullish Weekly Participation v5"
    assert PROFILE.direction == "bullish_only"
    assert PROFILE.validation_state == "research_default"
    index = PROFILE.lane(StrategyLane.INDEX_WEEKLY)
    leader = PROFILE.lane(StrategyLane.LEADER_WEEKLY)
    assert index.preferred_dte == (10, 16)
    assert index.hard_dte == (7, 21)
    assert index.preferred_delta == (0.60, 0.75)
    assert index.intended_hold_sessions == (1, 4)
    assert index.requalify_dte == 5
    assert leader.preferred_dte == (14, 21)
    assert leader.hard_dte == (10, 24)
    assert leader.preferred_delta == (0.55, 0.70)
    assert leader.intended_hold_sessions == (1, 5)
    assert leader.requalify_dte == 7
    assert PROFILE.maximum_quote_age_minutes == 2
    assert len(PROFILE.production_patterns) == 7
    assert len(PROFILE.context_patterns) == 5


def test_live_universe_is_broad_unique_and_sector_mapped() -> None:
    symbols = configured_symbols(fixture=False)
    leaders = leader_metadata()
    assert len(symbols) >= 150
    assert len(symbols) == len(set(symbols))
    assert {"AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM", "SPY", "QQQ"}.issubset(
        symbols
    )
    assert leaders["NVDA"].peer_etf == "SMH"
    assert leaders["JPM"].peer_etf == "XLF"


def test_fixture_universe_stays_deterministic() -> None:
    assert configured_symbols(fixture=True) == [
        "SPY",
        "QQQ",
        "SSTR",
        "APLUS",
        "BTIER",
        "ZERO",
    ]
