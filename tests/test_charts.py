from scanner.charts import render_daily_chart
from scanner.models import ScanType
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import run_scan


def test_render_daily_chart_fixture(tmp_path) -> None:
    result = run_scan(ScanType.POST_CLOSE, fixture=True, scenario="s_tier")
    provider = FixtureDataProvider()

    path = render_daily_chart(result.s_tier[0], provider.daily("SSTR"), tmp_path)

    assert path.exists()
    assert path.suffix == ".png"
    assert path.stat().st_size > 1000
