from __future__ import annotations

import argparse
import logging
import os
from datetime import UTC, date, datetime
from pathlib import Path

from scanner.calendars import is_trading_day, market_close_for
from scanner.charts import render_watchlist_chart
from scanner.clocks import NY
from scanner.config import ConfigurationError, load_config, load_local_env, validate_configuration
from scanner.daily_command import calculate_command
from scanner.daily_prep import nightly_prep_message, ranked_nightly_items, weekly_radar_message
from scanner.data_quality import DataQualityError, require_completed_candles
from scanner.entry_plan import build_entry_plan
from scanner.grading import grade_candidate
from scanner.indicators import ema
from scanner.market_regime import classify_market_regime
from scanner.models import (
    Candidate,
    Grade,
    PutCandidate,
    PutScanResult,
    RejectedRecord,
    ScanResult,
    ScanType,
)
from scanner.momentum import calculate_momentum, strict_daily_filter
from scanner.notifications import (
    TELEGRAM_TEST_MESSAGE,
    TelegramNotifier,
    completion_message,
    log_delivery,
)
from scanner.option_liquidity import classify_option_liquidity, classify_put_option_liquidity
from scanner.providers.alpaca import AlpacaDataProvider, NullCatalystProvider
from scanner.providers.base import CatalystProvider, MarketDataProvider, OptionDataProvider
from scanner.providers.cache import CachedMarketDataProvider, CachedOptionDataProvider
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.put_command import calculate_put_command
from scanner.put_entry_plan import build_put_entry_plan
from scanner.put_grading import grade_put_candidate
from scanner.put_momentum import calculate_put_momentum, strict_bearish_daily_filter
from scanner.put_reports import write_put_reports
from scanner.reports import write_reports
from scanner.state import NotificationState, completion_snapshot, should_send_completion
from scanner.storage.local_json import LocalJsonStorage
from scanner.universe import configured_symbols
from scanner.watchlist import SETUP_BUCKETS, watch_details, watchlist_level_summary

log = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )


def _providers(
    fixture: bool,
    scenario: str,
) -> tuple[MarketDataProvider, OptionDataProvider, CatalystProvider]:
    if fixture:
        provider = FixtureDataProvider(scenario=scenario)
        return CachedMarketDataProvider(provider), CachedOptionDataProvider(provider), provider
    alpaca = AlpacaDataProvider()
    return (
        CachedMarketDataProvider(alpaca),
        CachedOptionDataProvider(alpaca),
        NullCatalystProvider(),
    )


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


def run_scan(
    scan_type: ScanType, *, fixture: bool = False, scenario: str = "default"
) -> ScanResult:
    from collections import Counter

    validate_configuration(fixture=fixture)
    market, options, catalysts = _providers(fixture, scenario)
    weekly = market.weekly("SPY")
    market_regime = classify_market_regime(market.daily("SPY"), market.daily("QQQ"), weekly)
    print(f"[scan] Market regime: {market_regime}")
    if fixture and scenario == "zero":
        symbols = ["ZERO"]
    elif fixture and scenario == "s_tier":
        symbols = ["SSTR"]
    elif fixture and scenario == "a_plus":
        symbols = ["APLUS"]
    elif fixture and scenario == "b_tier":
        symbols = ["BTIER"]
    elif fixture and scenario == "technical_watch":
        symbols = ["SSTR"]
    else:
        symbols = configured_symbols(fixture=fixture)
    print(f"[scan] Processing {len(symbols)} symbols...")
    candidates: list[Candidate] = []
    rejected: list[RejectedRecord] = []
    for symbol in symbols:
        try:
            candidate = _scan_symbol(symbol, market, options, catalysts, market_regime)
        except (DataQualityError, ValueError, RuntimeError) as exc:
            rejected.append(
                RejectedRecord(symbol, "data_quality", ["scan_error"], {"error": str(exc)})
            )
            continue
        if candidate.grade == Grade.S_TIER:
            candidates.append(candidate)
        elif candidate.grade == Grade.A_PLUS:
            candidates.append(candidate)
        elif candidate.grade == Grade.B_TIER:
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
    reason_counts: Counter[str] = Counter()
    for record in rejected:
        for reason in record.reason_codes:
            reason_counts[reason] += 1
    print(
        f"[scan] Done: {len(candidates)} qualified, {len(rejected)} rejected"
        f" out of {len(symbols)}"
    )
    for reason, count in reason_counts.most_common(5):
        print(f"[scan] Rejection reason: {reason} ({count}x)")
    s_tier = [c for c in candidates if c.grade == Grade.S_TIER][:5]
    remaining_slots = max(0, 5 - len(s_tier))
    a_plus = [c for c in candidates if c.grade == Grade.A_PLUS][:remaining_slots]
    remaining_slots = max(0, remaining_slots - len(a_plus))
    b_tier = [c for c in candidates if c.grade == Grade.B_TIER][:remaining_slots]
    remaining_slots = max(0, remaining_slots - len(b_tier))
    technical_watch = [c for c in candidates if c.grade == Grade.TECHNICAL_WATCH][:remaining_slots]
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
        b_tier=b_tier,
        technical_watch=technical_watch,
        rejected=rejected,
        fixture=fixture,
    )


def _scan_put_symbol(
    symbol: str,
    market: MarketDataProvider,
    options: OptionDataProvider,
    catalysts: CatalystProvider,
    market_regime: str,
) -> PutCandidate:
    daily = market.daily(symbol)
    four_hour = market.four_hour(symbol)
    weekly = market.weekly(symbol)
    benchmark = "QQQ"
    benchmark_daily = market.daily(benchmark)
    require_completed_candles(daily, minimum=220, label=f"{symbol} daily")
    require_completed_candles(four_hour, minimum=60, label=f"{symbol} four_hour")
    require_completed_candles(weekly, minimum=30, label=f"{symbol} weekly")
    command = calculate_put_command(symbol, daily, benchmark_daily, weekly)
    # Bearish weekly HTF: close below weekly EMA 21
    daily_htf = weekly[-1].close < ema([c.close for c in weekly], 21)
    daily_momentum = calculate_put_momentum(symbol, daily, "1D", daily_htf)
    daily_filter = strict_bearish_daily_filter(daily_momentum)
    four_hour_momentum = calculate_put_momentum(symbol, four_hour, "4H", daily_filter)
    option_quotes = options.option_quotes(symbol)
    option_liquidity = classify_put_option_liquidity(option_quotes)
    if option_quotes and getattr(options, "option_feed", "") == "indicative":
        option_liquidity = "Indicative"
    catalyst = catalysts.catalyst(symbol)
    entry = build_put_entry_plan(command, four_hour_momentum)
    return grade_put_candidate(
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


def run_put_scan(
    scan_type: ScanType, *, fixture: bool = False, scenario: str = "default"
) -> PutScanResult:
    validate_configuration(fixture=fixture)
    market, options, catalysts = _providers(fixture, scenario)
    weekly = market.weekly("SPY")
    market_regime = classify_market_regime(market.daily("SPY"), market.daily("QQQ"), weekly)
    if fixture and scenario == "put_s_tier":
        symbols = ["SPUT"]
    elif fixture and scenario == "put_a_plus":
        symbols = ["APUT"]
    elif fixture and scenario == "put_b_tier":
        symbols = ["BPUT"]
    else:
        symbols = configured_symbols(fixture=fixture)
    candidates: list[PutCandidate] = []
    rejected: list[RejectedRecord] = []
    for symbol in symbols:
        try:
            candidate = _scan_put_symbol(symbol, market, options, catalysts, market_regime)
        except (DataQualityError, ValueError, RuntimeError) as exc:
            rejected.append(
                RejectedRecord(symbol, "data_quality", ["scan_error"], {"error": str(exc)})
            )
            continue
        if candidate.grade in {Grade.S_TIER, Grade.A_PLUS, Grade.B_TIER, Grade.TECHNICAL_WATCH}:
            candidates.append(candidate)
        else:
            rejected.append(
                RejectedRecord(
                    symbol,
                    "grading",
                    candidate.rejection_reasons or ["did_not_meet_put_standard"],
                    {},
                )
            )
    s_tier = [c for c in candidates if c.grade == Grade.S_TIER][:5]
    remaining_slots = max(0, 5 - len(s_tier))
    a_plus = [c for c in candidates if c.grade == Grade.A_PLUS][:remaining_slots]
    remaining_slots = max(0, remaining_slots - len(a_plus))
    b_tier = [c for c in candidates if c.grade == Grade.B_TIER][:remaining_slots]
    remaining_slots = max(0, remaining_slots - len(b_tier))
    technical_watch = [c for c in candidates if c.grade == Grade.TECHNICAL_WATCH][:remaining_slots]
    from scanner.providers.fixtures import FIXTURE_TIMESTAMP

    timestamp = FIXTURE_TIMESTAMP if fixture else datetime.now(UTC)
    return PutScanResult(
        scan_type=scan_type,
        generated_at=datetime.now(UTC),
        market_data_timestamp=timestamp,
        market_regime=market_regime,
        universe_count=len(symbols),
        deterministic_pass_count=len(candidates),
        research_count=len(candidates),
        s_tier=s_tier,
        a_plus=a_plus,
        b_tier=b_tier,
        technical_watch=technical_watch,
        rejected=rejected,
        fixture=fixture,
    )


def readiness_check() -> int:
    load_local_env()
    warnings = validate_configuration(fixture=False)
    target_day = date.today()
    print(f"Readiness check for {target_day.strftime('%A %Y-%m-%d')}")
    print(f"Trading day: {'yes' if is_trading_day(target_day) else 'no'}")
    if is_trading_day(target_day):
        print(f"Market close: {market_close_for(target_day).isoformat()}")
    print(f"Free mode: {os.environ.get('FREE_MODE', 'true')}")
    print(f"Equity feed: {os.environ.get('ALPACA_FEED', 'iex')}")
    print(f"Option feed: {os.environ.get('ALPACA_OPTION_FEED', 'indicative')}")
    print(
        "Alpaca credentials: "
        + (
            "configured"
            if os.environ.get("ALPACA_API_KEY_ID") and os.environ.get("ALPACA_API_SECRET_KEY")
            else "missing"
        )
    )
    print(
        "Telegram: "
        + (
            "configured"
            if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")
            else "missing"
        )
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


_ONLY_ON_CHANGE_FLAGS = {
    ScanType.PREMARKET: "send_premarket_only_on_change",
    ScanType.FOUR_HOUR: "send_four_hour_only_on_change",
}


def _maybe_notify(result: ScanResult, report_path: Path, fixture: bool) -> None:
    message = completion_message(result, report_path)
    notifier = TelegramNotifier()
    if fixture:
        print(message)
        return
    flag_name = _ONLY_ON_CHANGE_FLAGS.get(result.scan_type)
    if flag_name is not None:
        only_on_change = bool(load_config("notifications").get(flag_name, True))
        state = NotificationState(LocalJsonStorage())
        snapshot = completion_snapshot(result)
        previous = state.last_completion_snapshot(result.scan_type.value)
        send = should_send_completion(previous, snapshot, only_on_change)
        state.record_completion_snapshot(result.scan_type.value, snapshot)
        if not send:
            log_delivery(
                "completion",
                "suppressed_unchanged",
                event_type="completion",
            )
            print("Completion message suppressed: nothing material changed since the last run.")
            return
    delivery = notifier.send(message)
    log_delivery(
        "completion", delivery.status, event_type="completion", error=delivery.safe_error or ""
    )


WEEKLY_RADAR_SENT_EVENT = "weekly_radar_sent_date"


def _mark_weekly_radar_sent() -> None:
    state = NotificationState(LocalJsonStorage())
    state.record_event(WEEKLY_RADAR_SENT_EVENT, datetime.now(NY).date().isoformat())


def _weekly_radar_sent_today() -> bool:
    """True when the weekly radar covers today's charts (Sunday overlap).

    The state marker catches same-process or same-state overlaps, but on GitHub
    Actions the radar job's state cache is saved only after its hold window
    closes, which is later than the nightly prep job restores state. Sundays are
    therefore skipped deterministically: the weekly radar owns Sunday charts.
    """
    now = datetime.now(NY)
    if now.weekday() == 6:
        return True
    state = NotificationState(LocalJsonStorage())
    return state.last_event(WEEKLY_RADAR_SENT_EVENT) == now.date().isoformat()


def _send_watchlist_charts(
    result: ScanResult,
    market: MarketDataProvider,
    notifier: TelegramNotifier,
    *,
    fixture: bool,
) -> None:
    if fixture:
        return
    items = ranked_nightly_items(result)
    setup_items = [item for item in items if item.bucket in SETUP_BUCKETS]
    watch_items = [item for item in items if item.bucket == "Watch"]
    for item in (setup_items + watch_items)[:5]:
        try:
            candles = market.daily(item.symbol)
            levels = watchlist_level_summary(item)
            chart_title = f"{item.symbol} daily | {item.bucket} | {item.reason}"
            if levels:
                chart_title = f"{chart_title} | {levels}"
            chart_path = render_watchlist_chart(
                item.symbol,
                candles,
                chart_title,
                item.trigger,
                item.support,
                item.target_price if item.bucket in SETUP_BUCKETS else None,
            )
            delivery = notifier.send_photo(chart_path, caption=f"{item.symbol} {item.bucket}")
            log_delivery(
                f"daily_chart_{item.symbol}",
                delivery.status,
                ticker=item.symbol,
                event_type="daily_chart",
                error=delivery.safe_error or "",
            )
        except Exception as exc:
            log_delivery(
                f"daily_chart_{item.symbol}",
                "chart_failed",
                ticker=item.symbol,
                event_type="daily_chart",
                error=str(exc),
            )


def main() -> int:
    _configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "post_close",
            "premarket",
            "four_hour",
            "test_notification",
            "daily_prep",
            "weekly_radar",
            "validate_configuration",
            "readiness_check",
            "put_post_close",
            "put_premarket",
            "put_four_hour",
        ],
    )
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument(
        "--scenario",
        default="default",
        choices=[
            "default",
            "s_tier",
            "a_plus",
            "b_tier",
            "technical_watch",
            "zero",
            "put_s_tier",
            "put_a_plus",
            "put_b_tier",
        ],
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
            log_delivery(
                "test_notification",
                delivery.status,
                event_type="test",
                error=delivery.safe_error or "",
            )
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
            log_delivery(
                "daily_prep",
                delivery.status,
                event_type="daily_prep",
                error=delivery.safe_error or "",
            )
            if not delivery.delivered:
                print(f"Daily prep Telegram notification not sent: {delivery.safe_error}")
                return 1
            if _weekly_radar_sent_today():
                print("Skipping chart attachments: weekly radar already sent them today.")
            else:
                market, _, _ = _providers(False, args.scenario)
                _send_watchlist_charts(result, market, notifier, fixture=args.fixture)
            print("Daily prep Telegram notification delivered.")
            return 0
        if args.command == "weekly_radar":
            result = run_scan(ScanType.POST_CLOSE, fixture=args.fixture, scenario=args.scenario)
            md_path, json_path = write_reports(result)
            message = weekly_radar_message(result, md_path)
            if args.fixture:
                print(message)
                print(f"Markdown report: {md_path}")
                print(f"JSON report: {json_path}")
                return 0
            notifier = TelegramNotifier()
            delivery = notifier.send(message)
            log_delivery(
                "weekly_radar",
                delivery.status,
                event_type="weekly_radar",
                error=delivery.safe_error or "",
            )
            if not delivery.delivered:
                print(f"Weekly radar Telegram notification not sent: {delivery.safe_error}")
                return 1
            market, _, _ = _providers(False, args.scenario)
            _send_watchlist_charts(result, market, notifier, fixture=args.fixture)
            _mark_weekly_radar_sent()
            print("Weekly radar Telegram notification delivered.")
            return 0
        if args.command in {"put_post_close", "put_premarket", "put_four_hour"}:
            put_scan_type = ScanType(args.command)
            put_result = run_put_scan(
                put_scan_type, fixture=args.fixture, scenario=args.scenario
            )
            md_path, json_path = write_put_reports(put_result)
            print(f"Markdown report: {md_path}")
            print(f"JSON report: {json_path}")
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
