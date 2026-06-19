
from scanner.config import ROOT, load_config, validate_configuration


def test_root_agents_present() -> None:
    assert (ROOT / "AGENTS.md").exists()


def test_configuration_valid_fixture() -> None:
    assert validate_configuration(fixture=True) == []
    assert load_config("universe")["options_required"] is True
