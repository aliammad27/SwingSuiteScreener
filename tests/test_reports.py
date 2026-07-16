import json

from scanner.models import ScanType
from scanner.reports import FIXTURE_LABEL, result_to_json, write_reports
from scanner.run_scan import run_scan


def test_report_publishes_v5_timing_trust_and_actual_contract(
    tmp_path, monkeypatch
) -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    import scanner.reports as reports

    monkeypatch.setattr(reports, "ROOT", tmp_path)
    markdown_path, json_path = write_reports(result)
    text = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    dashboard = markdown_path.with_name("latest.html").read_text(encoding="utf-8")
    assert FIXTURE_LABEL in text
    assert "Hourly timing:" in text
    assert "Tactical warning / failure:" in text
    assert "Theta / ask:" in text
    assert "Data trust:" in text
    assert "Primary call:" in text
    assert payload["schema_version"] == 5
    assert payload["validation_state"] == "research_default"
    assert payload["ready_verify"][0]["state"] == "ready_verify"
    assert "Bullish Weekly Participation v5" in dashboard
    assert "SIMULATED FIXTURE - NOT CURRENT MARKET DATA" in dashboard
    assert 'id="compare-panel"' in dashboard
    assert 'id="dte"' in dashboard
    assert "Contract Alternatives" in dashboard
    assert "A long call can lose" in dashboard


def test_json_schema_exposes_only_v5_review_state_groups() -> None:
    payload = result_to_json(run_scan(ScanType.INTRADAY, fixture=True))
    candidate_groups = {
        key
        for key, value in payload.items()
        if isinstance(value, list) and key != "rejected"
    }
    assert candidate_groups == {
        "ready",
        "ready_verify",
        "developing",
        "verify_contract",
    }
