from scanner.charts import render_candidate_summary, render_daily_chart
from scanner.models import ScanType
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import run_scan


def test_daily_chart_and_telegram_summary_render(tmp_path) -> None:
    result = run_scan(ScanType.INTRADAY, fixture=True, scenario="ready")
    candidate = result.ready_verify[0]
    provider = FixtureDataProvider("ready")
    daily = render_daily_chart(candidate, provider.daily("SSTR"), tmp_path)
    summary = render_candidate_summary(candidate, tmp_path)
    assert daily.exists() and daily.stat().st_size > 10_000
    assert summary.exists() and summary.stat().st_size > 10_000
    assert summary.name.endswith("_v5_summary.png")
