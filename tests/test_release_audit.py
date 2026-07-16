from scripts.release_audit import run_release_audit


def test_v5_release_audit_passes() -> None:
    assert run_release_audit() == []
