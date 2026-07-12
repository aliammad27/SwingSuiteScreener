import json

from scanner.models import ScanType
from scanner.reports import FIXTURE_LABEL, write_reports
from scanner.run_scan import run_scan


def test_fixture_report_label_and_json_shape() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="default")
    md, js = write_reports(result)
    assert FIXTURE_LABEL in md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["scan_type"] == "post_close"
    assert "rejected" in data


def test_zero_report_wording() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="zero")
    md, _ = write_reports(result)
    text = md.read_text(encoding="utf-8")
    assert "No setups are ready for review today." in text
    assert "do not force an entry" in text


def test_technical_watch_report_section_and_json() -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="technical_watch")
    md, js = write_reports(result)
    text = md.read_text(encoding="utf-8")
    data = json.loads(js.read_text(encoding="utf-8"))
    assert "VERIFY CONTRACT" in text
    assert "Verify the contract" in text
    assert "Target stock price:" in text
    assert "Research call strike:" in text
    assert "Preferred DTE range: 30-60" in text
    assert "Intended hold window: 5-15 days" in text
    assert data["technical_watch"]
    entry = data["technical_watch"][0]["entry_plan"]
    assert entry["target_price"] > 0
    assert entry["research_call_strike"] > 0
    assert entry["preferred_dte_minimum"] == 30
    assert entry["preferred_dte_maximum"] == 60


def test_s_tier_report_has_management_footer_and_strike_note() -> None:
    from scanner.reports import MANAGEMENT_FOOTER, STRIKE_VALIDATION_NOTE

    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="s_tier")
    md, _ = write_reports(result)
    text = md.read_text(encoding="utf-8")
    assert result.s_tier
    assert MANAGEMENT_FOOTER in text
    assert STRIKE_VALIDATION_NOTE in text
    assert "underlying invalidation" in text
    assert "0.45-0.65 delta" in text
