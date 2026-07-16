import json
from datetime import timedelta

from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.replay import _CutoffMarketProvider, sequential_replay, write_replay_report


def test_cutoff_provider_never_exposes_future_bars() -> None:
    cutoff = FIXTURE_TIMESTAMP - timedelta(days=3)
    provider = _CutoffMarketProvider(FixtureDataProvider(), cutoff)
    for candles in (
        provider.daily("SPY"),
        provider.one_hour("SPY"),
        provider.weekly("SPY"),
    ):
        assert candles
        assert max(candle.timestamp for candle in candles) <= cutoff


def test_sequential_replay_smoke_and_report_never_fabricate_option_returns(tmp_path) -> None:
    hits = sequential_replay(
        FixtureDataProvider(),
        "SPY",
        ["SSTR", "APLUS", "BTIER"],
        horizon_sessions=3,
        maximum_signal_dates=5,
    )
    assert isinstance(hits, tuple)
    assert all(hit.source_bar_count >= 220 for hit in hits)
    markdown_path, json_path = write_replay_report(hits, tmp_path)
    assert "not option performance" in markdown_path.read_text()
    payload = json.loads(json_path.read_text())
    assert all(not any("contract" in key for key in row) for row in payload)
