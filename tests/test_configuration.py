from scanner.config import ROOT, load_config, validate_configuration
from scanner.models import StrategyLane
from scanner.strategy_profile import PROFILE
from scanner.universe import configured_symbols, leader_metadata


def test_root_agents_present() -> None:
    assert (ROOT / "CLAUDE.md").exists()


def test_configuration_valid_fixture() -> None:
    assert validate_configuration(fixture=True) == []
    assert load_config("universe")["options_required"] is True


def test_bullish_participation_v4_lanes_are_authoritative() -> None:
    assert PROFILE.schema_version == 4
    assert PROFILE.direction == "bullish_only"
    index = PROFILE.lane(StrategyLane.INDEX_CORE)
    leader = PROFILE.lane(StrategyLane.LEADER_SWING)
    assert index.preferred_dte == (45, 90)
    assert index.preferred_delta == (0.60, 0.75)
    assert leader.preferred_dte == (30, 60)
    assert leader.preferred_delta == (0.45, 0.65)
    assert leader.intended_hold_sessions == (5, 15)


def test_live_universe_is_broad_unique_and_sector_mapped() -> None:
    symbols = configured_symbols(fixture=False)
    leaders = leader_metadata()
    assert len(symbols) >= 150
    assert len(symbols) == len(set(symbols))
    assert {"AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM", "SPY", "QQQ"}.issubset(symbols)
    assert leaders["NVDA"].peer_etf == "SMH"
    assert leaders["JPM"].peer_etf == "XLF"


def test_fixture_universe_stays_deterministic() -> None:
    assert configured_symbols(fixture=True) == ["SPY", "QQQ", "SSTR", "APLUS", "BTIER", "ZERO"]
