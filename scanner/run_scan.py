from __future__ import annotations

import argparse
import os
from datetime import UTC, date, datetime
from pathlib import Path

from scanner.calendars import is_trading_day, market_close_for
from scanner.config import ConfigurationError, load_local_env, validate_configuration
from scanner.daily_command import calculate_command
from scanner.daily_prep import nightly_prep_message
from scanner.data_quality import DataQualityError, require_completed_candles
from scanner.entry_plan import build_entry_plan
from scanner.grading import grade_candidate
from scanner.indicators import ema
from scanner.market_regime import classify_market_regime
from scanner.models import Candidate, Grade, RejectedRecord, ScanResult, ScanType
from scanner.momentum import calculate_momentum, strict_daily_filter
from scanner.notifications import (
    TELEGRAM_TEST_MESSAGE,
    TelegramNotifier,
    completion_message,
    log_delivery,
)
from scanner.option_liquidity import classify_option_liquidity
from scanner.providers.alpaca import AlpacaDataProvider, NullCatalystProvider
from scanner.providers.base import CatalystProvider, MarketDataProvider, OptionDataProvider
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.reports import write_reports
from scanner.universe import configured_symbols
from scanner.watchlist import watch_details


def _providers(
    fixture: bool,
    scenario: str,
) -> tuple[MarketDataProvider, OptionDataProvider, CatalystProvider]:
    if fixture:
        provider = FixtureDataProvider(scenario=scenario)
        return provider, provider, provider
    alpaca = AlpacaDataProvider()
    return alpaca, alpaca, NullCatalystProvider()


def _scan_symbol(
    symbol: str,
    market: MarketDataProvider,
    options: OptionDataProvider,
    catalysts: CatalystProvider,
    market_regime: str,
) -> Candidate:
    daily = market.daily(symbol)
    four_hour = market.four_hour(symbol)
    weekly = market.weekly(symbol)
    benchmark = "QQQ"
    benchmark_daily = market.daily(benchmark)
    require_completed_candles(daily, minimum=220, label=f"{symbol} daily")
    require_completed_candles(four_hour, minimum=60, label=f"{symbol} four_hour")
    require_completed_candles(weekly, minimum=30, label=f"{symbol} weekly")
    command = calculate_command(symbol, daily, benchmark_daily, weekly)
    daily_htf = weekly[-1].close > ema([c.close for c in weekly], 21)
    daily_momentum = calculate_momentum(symbol, daily, "1D", daily_htf)
    daily_filter = strict_daily_filter(daily_momentum)
    four_hour_momentum = calculate_momentum(symbol, four_hour, "4H", daily_filter)
    option_quotes = options.option_quotes(symbol)
    option_liquidity = classify_option_liquidity(option_quotes)
    if option_quotes and getattr(options, "option_feed", "") == "indicative":
        option_liquidity = "Indicative"
    catalyst = catalysts.catalyst(symbol)
    entry = build_entry_plan(command, four_hour_momentum)
    return grade_candidate(
        symbol=symbol,
        company=market.company_name(symbol),
        sector=market.sector(symbol),
        benchmark=benchmark,
        command=command,
        daily_momentum=daily_momentum,
        four_hour=four_hour_momentum,
        option_liquidity=option_liquidity,
        catalyst=catalyst,
        market_regime=market_regime,
        entry_plan=entry,
        allow_technical_watch=os.environ.get("ALLOW_TECHNICAL_WATCH", "true").lower() == "true",
    )


def run_scan(scan_type: ScanType, *, fixture: bool = False, scenario: str = "default") -> ScanResult:
    validate_configuration(fixture=fixture)
    market, options, catalysts = _providers(fixture, scenario)
    weekly = market.weekly("SPY")
    market_regime = classify_market_regime(market.daily("SPY"), market.daily("QQQ"), weekly)
    if fixture and scenario == "zero":
        symbols = ["ZERO"]
    elif fixture and scenario == "s_tier":
        symbols = ["SSTR"]
    elif fixture and scenario == "a_plus":
        symbols = ["APLUS"]
    elif fixture and scenario == "technical_watch":
        symbols = ["SSTR"]
    else:
        symbols = configured_symbols(fixture=fixture)
    candidates: list[Candidate] = []
    rejected: list[RejectedRecord] = []
    for symbol in symbols:
        try:
            candidate = _scan_symbol(symbol, market, options, catalysts, market_regime)
        except (DataQualityError, ValueError, RuntimeError) as exc:
            rejected.append(RejectedRecord(symbol, "data_quality", ["scan_error"], {"error": str(exc)}))
            continue
        if candidate.grade == Grade.S_TIER:
            candidates.append(candidate)
        elif candidate.grade == Grade.A_PLUS:
            candidates.append(candidate)
        elif candidate.grade == Grade.TECHNICAL_WATCH:
            candidates.append(candidate)
        else:
            rejected.append(
                RejectedRecord(
                    symbol,
                    "grading",
                    candidate.rejection_reasons or ["did_not_meet_primary_report_standard"],
                    watch_details(candidate),
                )
            )
    s_tier = [c for c in candidates if c.grade == Grade.S_TIER][:5]
    remaining_slots = max(0, 5 - len(s_tier))
    a_plus = [c for c in candidates if c.grade == Grade.A_PLUS][:remaining_slots]
    remaining_slots = max(0, remaining_slots - len(a_plus))
    technical_watch = [
        c for c in candidates if c.grade == Grade.TECHNICAL_WATCH
    ][:remaining_slots]
    timestamp = FIXTURE_TIMESTAMP if fixture else datetime.now(UTC)
    return ScanResult(
        scan_type=scan_type,
        generated_at=datetime.now(UTC),
        market_data_timestamp=timestamp,
        market_regime=market_regime,
        universe_count=len(symbols),
        deterministic_pass_count=len(candidates),
        research_count=len(candidates),
        s_tier=s_tier,
        a_plus=a_plus,
        technical_watch=technical_watch,
        rejected=rejected,
        fixture=fixture,
    )


def readiness_check() -> int:
    load_local_env()
    warnings = validate_configuration(fixture=False)
    target_day = date(2026, 6, 22)
    print("Readiness check for Monday 2026-06-22")
    print(f"Trading day: {'yes' if is_trading_day(target_day) else 'no'}")
    if is_trading_day(target_day):
        print(f"Market close: {market_close_for(target_day).isoformat()}")
    print(f"Free mode: {os.environ.get('FREE_MODE', 'true')}")
    print(f"Equity feed: {os.environ.get('ALPACA_FEED', 'iex')}")
    print(f"Option feed: {os.environ.get('ALPACA_OPTION_FEED', 'indicative')}")
    print(
        "Alpaca credentials: "
        + ("configured" if os.environ.get("ALPACA_API_KEY_ID") and os.environ.get("ALPACA_API_SECRET_KEY") else "missing")
    )
    print(
        "Telegram: "
        + ("configured" if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID") else "missing")
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


def _maybe_notify(result: ScanResult, report_path: Path, fixture: bool) -> None:
    message = completion_message(result, report_path)
    notifier = TelegramNotifier()
    if fixture:
        print(message)
        return
    delivery = notifier.send(message)
    log_delivery("completion", delivery.status, event_type="completion", error=delivery.safe_error or "")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "post_close",
            "premarket",
            "four_hour",
            "test_notification",
            "daily_prep",
            "validate_configuration",
            "readiness_check",
        ],
    )
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument(
        "--scenario",
        default="default",
        choices=["default", "s_tier", "a_plus", "technical_watch", "zero"],
    )
    args = parser.parse_args()
    try:
        if args.command == "validate_configuration":
            warnings = validate_configuration(fixture=args.fixture)
            print("Configuration files are valid.")
            for warning in warnings:
                print(f"WARNING: {warning}")
            return 0
        if args.command == "readiness_check":
            return readiness_check()
        if args.command == "test_notification":
            if args.fixture:
                print(TELEGRAM_TEST_MESSAGE)
                return 0
            notifier = TelegramNotifier()
            delivery = notifier.send(TELEGRAM_TEST_MESSAGE)
            log_delivery("test_notification", delivery.status, event_type="test", error=delivery.safe_error or "")
            if not delivery.delivered:
                print(f"Telegram test notification not sent: {delivery.safe_error}")
                return 0
            print("Telegram test notification delivered.")
            return 0
        if args.command == "daily_prep":
            result = run_scan(ScanType.POST_CLOSE, fixture=args.fixture, scenario=args.scenario)
            md_path, json_path = write_reports(result)
            message = nightly_prep_message(result, md_path)
            if args.fixture:
                print(message)
                print(f"Markdown report: {md_path}")
                print(f"JSON report: {json_path}")
                return 0
            notifier = TelegramNotifier()
            delivery = notifier.send(message)
            log_delivery("daily_prep", delivery.status, event_type="daily_prep", error=delivery.safe_error or "")
            if not delivery.delivered:
                print(f"Daily prep Telegram notification not sent: {delivery.safe_error}")
                return 1
            print("Daily prep Telegram notification delivered.")
            return 0
        scan_type = ScanType(args.command)
        result = run_scan(scan_type, fixture=args.fixture, scenario=args.scenario)
        md_path, json_path = write_reports(result)
        _maybe_notify(result, md_path, args.fixture)
        print(f"Markdown report: {md_path}")
        print(f"JSON report: {json_path}")
        return 0
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Exception as exc:
        print(f"Scan failed safely: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
