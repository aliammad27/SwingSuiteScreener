import json

from scanner.models import ScanType
from scanner.reports import FIXTURE_LABEL, result_to_json, write_reports
from scanner.run_scan import run_scan


def test_report_publishes_v4_evidence_and_actual_contract(tmp_path, monkeypatch) -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="ready")
    import scanner.reports as reports

    monkeypatch.setattr(reports, "ROOT", tmp_path)
    markdown_path, json_path = write_reports(result)
    text = markdown_path.read_text(encoding="utf-8")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    dashboard = markdown_path.with_name("latest.html").read_text(encoding="utf-8")
    assert FIXTURE_LABEL in text
    assert "Evidence: Trend" in text
    assert "Primary call:" in text
    assert "research strike" not in text.lower()
    assert "long call can lose the full premium" in text.lower()
    assert payload["schema_version"] == 4
    assert payload["ready"][0]["state"] == "ready"
    assert "Bullish Participation v4" in dashboard
    assert "SIMULATED FIXTURE - NOT CURRENT MARKET DATA" in dashboard
    assert 'data-filter-state="ready"' in dashboard
    assert "SSTR" in dashboard
    assert "A long call can" in dashboard


def test_json_schema_exposes_only_v4_review_state_groups() -> None:
    payload = result_to_json(run_scan(ScanType.POST_CLOSE, fixture=True))
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
