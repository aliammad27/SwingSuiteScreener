from scanner.config import ROOT, load_config, validate_configuration
from scanner.universe import configured_symbols


def test_root_agents_present() -> None:
    assert (ROOT / "CLAUDE.md").exists()


def test_configuration_valid_fixture() -> None:
    assert validate_configuration(fixture=True) == []
    assert load_config("universe")["options_required"] is True


def test_live_universe_is_broad_and_unique() -> None:
    symbols = configured_symbols(fixture=False)

    assert len(symbols) >= 150
    assert len(symbols) == len(set(symbols))
    assert {"AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM"}.issubset(symbols)


def test_fixture_universe_stays_deterministic() -> None:
    assert configured_symbols(fixture=True) == ["SSTR", "APLUS", "ZERO"]
