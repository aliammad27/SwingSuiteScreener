from scanner.config import ROOT, load_config, validate_configuration
from scanner.strategy_profile import PROFILE
from scanner.universe import configured_symbols


def test_root_agents_present() -> None:
    assert (ROOT / "CLAUDE.md").exists()


def test_configuration_valid_fixture() -> None:
    assert validate_configuration(fixture=True) == []
    assert load_config("universe")["options_required"] is True


def test_bullish_participation_profile_is_authoritative() -> None:
    assert PROFILE.direction == "bullish_only"
    assert PROFILE.enable_put_scans is False
    assert (PROFILE.preferred_dte_minimum, PROFILE.preferred_dte_maximum) == (30, 60)
    assert (PROFILE.preferred_delta_minimum, PROFILE.preferred_delta_maximum) == (0.45, 0.65)
    assert (PROFILE.intended_hold_days_minimum, PROFILE.intended_hold_days_maximum) == (5, 15)


def test_live_universe_is_broad_and_unique() -> None:
    symbols = configured_symbols(fixture=False)

    assert len(symbols) >= 150
    assert len(symbols) == len(set(symbols))
    assert {"AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM"}.issubset(symbols)


def test_fixture_universe_stays_deterministic() -> None:
    assert configured_symbols(fixture=True) == ["SSTR", "APLUS", "ZERO"]
