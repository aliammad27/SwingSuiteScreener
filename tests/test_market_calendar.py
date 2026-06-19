from datetime import date

from scanner.calendars import is_half_day, is_trading_day, market_close_for


def test_holiday_and_half_day_rules() -> None:
    assert is_trading_day(date(2026, 6, 19)) is False
    assert is_trading_day(date(2026, 6, 22)) is True
    assert is_half_day(date(2026, 11, 27)) is True
    assert market_close_for(date(2026, 11, 27)).hour == 13
