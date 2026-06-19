from scanner.market_regime import classify_market_regime
from scanner.providers.fixtures import FixtureDataProvider
from scanner.run_scan import _scan_symbol
from scanner.state import NotificationState, notification_identifier
from scanner.storage.local_json import LocalJsonStorage


def test_notification_deduplication(tmp_path) -> None:
    provider = FixtureDataProvider()
    regime = classify_market_regime(provider.daily("SPY"), provider.daily("QQQ"), provider.weekly("SPY"))
    candidate = _scan_symbol("SSTR", provider, provider, provider, regime)
    identifier = notification_identifier("2026-06-18", "post_close", candidate, "new_s_tier")
    state = NotificationState(LocalJsonStorage(tmp_path))
    assert state.already_sent(identifier) is False
    state.mark_sent(identifier, {"symbol": candidate.symbol})
    assert state.already_sent(identifier) is True
