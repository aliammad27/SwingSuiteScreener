from __future__ import annotations

import argparse
import logging
import os
from datetime import UTC, date, datetime, timedelta

from scanner.config import ConfigurationError, load_local_env, validate_configuration
from scanner.contract_selection import select_contracts
from scanner.data_quality import DataQualityError, require_completed_candles
from scanner.entry_plan import build_entry_plan
from scanner.evidence import (
    analyze_trend,
    annualized_realized_volatility,
    calculate_leadership,
)
from scanner.grading import calculate_risk_score, classify_candidate
from scanner.indicators import ema
from scanner.market_context import calculate_market_context
from scanner.models import (
    Candidate,
    EvidenceScores,
    RejectedRecord,
    ReviewState,
    ScanResult,
    ScanType,
    StrategyLane,
)
from scanner.momentum import calculate_momentum, strict_daily_filter
from scanner.patterns import detect_best_pattern
from scanner.providers.alpaca import AlpacaDataProvider, ConfiguredEventRiskProvider
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider
from scanner.providers.cache import CachedMarketDataProvider, CachedOptionDataProvider
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.strategy_profile import PROFILE
from scanner.universe import configured_leader_symbols, configured_symbols, metadata_for

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
) -> tuple[MarketDataProvider, OptionDataProvider, EventRiskProvider]:
    if fixture:
        provider = FixtureDataProvider(scenario=scenario)
        return CachedMarketDataProvider(provider), CachedOptionDataProvider(provider), provider
    alpaca = AlpacaDataProvider()
    return (
        CachedMarketDataProvider(alpaca),
        CachedOptionDataProvider(alpaca),
        ConfiguredEventRiskProvider(),
    )


def _scan_symbol(
    symbol: str,
    market: MarketDataProvider,
    options: OptionDataProvider,
    events: EventRiskProvider,
    market_context: object,
    as_of: datetime,
) -> Candidate:
    from scanner.models import MarketContext

    if not isinstance(market_context, MarketContext):
        raise TypeError("market_context must be MarketContext")
    metadata = metadata_for(symbol)
    daily = market.daily(symbol)
    four_hour = market.four_hour(symbol)
    weekly = market.weekly(symbol)
    require_completed_candles(daily, minimum=220, label=f"{symbol} daily")
    require_completed_candles(four_hour, minimum=60, label=f"{symbol} four_hour")
    require_completed_candles(weekly, minimum=30, label=f"{symbol} weekly")

    trend = analyze_trend(daily, weekly)
    leadership: int | None = None
    if metadata.lane == StrategyLane.LEADER_SWING:
        leadership = calculate_leadership(
            daily,
            market.daily(metadata.peer_etf),
            market.daily("SPY"),
        )
    daily_htf = weekly[-1].close > ema([candle.close for candle in weekly], 21)
    daily_momentum = calculate_momentum(symbol, daily, "1D", daily_htf)
    four_hour_momentum = calculate_momentum(
        symbol,
        four_hour,
        "4H",
        strict_daily_filter(daily_momentum),
    )
    pattern = detect_best_pattern(daily, trend, PROFILE)
    lane_profile = PROFILE.lane(metadata.lane)
    entry = build_entry_plan(trend, pattern, lane_profile)
    expiry_start = as_of.date() + timedelta(days=lane_profile.hard_dte[0])
    expiry_end = as_of.date() + timedelta(days=lane_profile.hard_dte[1])
    chain = options.call_chain(symbol, expiry_start, expiry_end)
    contracts = select_contracts(
        chain,
        lane_profile,
        as_of,
        annualized_realized_volatility(daily),
        feed_when_empty=getattr(options, "option_feed", "unknown"),
    )
    event = events.event_risk(symbol)
    risk_score = calculate_risk_score(trend, pattern, entry, event)
    scores = EvidenceScores(
        trend=trend.score,
        leadership=leadership,
        setup=pattern.quality,
        momentum=round((daily_momentum.score + four_hour_momentum.score) / 2),
        market=market_context.score,
        contract=contracts.score,
        risk=risk_score,
    )
    state, reasons = classify_candidate(
        lane=metadata.lane,
        scores=scores,
        trend=trend,
        pattern=pattern,
        four_hour=four_hour_momentum,
        market=market_context,
        event=event,
        contracts=contracts,
        profile=PROFILE,
        as_of=as_of,
    )
    return Candidate(
        symbol=symbol,
        company=metadata.company,
        sector=metadata.sector,
        peer_etf=metadata.peer_etf,
        lane=metadata.lane,
        trend=trend,
        leadership_score=leadership,
        pattern=pattern,
        daily_momentum=daily_momentum,
        four_hour_momentum=four_hour_momentum,
        market=market_context,
        event_risk=event,
        contracts=contracts,
        entry_plan=entry,
        scores=scores,
        state=state,
        reasons=reasons,
    )


def _fixture_symbols(scenario: str) -> list[str]:
    return {
        "ready": ["SSTR"],
        "ready_verify": ["APLUS"],
        "developing": ["BTIER"],
        "technical_watch": ["SSTR"],
        "zero": ["ZERO"],
    }.get(scenario, configured_symbols(fixture=True))


def _candidate_rank(candidate: Candidate) -> tuple[int, int]:
    state_rank = {
        ReviewState.READY: 4,
        ReviewState.READY_VERIFY: 3,
        ReviewState.VERIFY_CONTRACT: 2,
        ReviewState.DEVELOPING: 1,
        ReviewState.REJECTED: 0,
    }[candidate.state]
    score_total = sum(
        score
        for score in (
            candidate.scores.trend,
            candidate.scores.leadership,
            candidate.scores.setup,
            candidate.scores.momentum,
            candidate.scores.market,
            candidate.scores.contract,
            candidate.scores.risk,
        )
        if score is not None
    )
    return state_rank, score_total


def run_scan(
    scan_type: ScanType,
    *,
    fixture: bool = False,
    scenario: str = "default",
) -> ScanResult:
    validate_configuration(fixture=fixture)
    market, options, events = _providers(fixture, scenario)
    as_of = FIXTURE_TIMESTAMP if fixture else datetime.now(UTC)
    breadth_symbols = configured_leader_symbols(fixture=fixture)
    market_context = calculate_market_context(market, breadth_symbols, PROFILE)
    symbols = _fixture_symbols(scenario) if fixture else configured_symbols()
    candidates: list[Candidate] = []
    rejected: list[RejectedRecord] = []
    for symbol in symbols:
        try:
            candidate = _scan_symbol(
                symbol,
                market,
                options,
                events,
                market_context,
                as_of,
            )
        except (DataQualityError, ValueError, RuntimeError) as exc:
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="data_quality",
                    reason_codes=("scan_error",),
                    details={"error": str(exc)},
                )
            )
            continue
        if candidate.state == ReviewState.REJECTED:
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="qualification",
                    reason_codes=candidate.reasons or ("not_qualified",),
                    details={
                        "lane": candidate.lane.value,
                        "pattern": candidate.pattern.pattern_type,
                    },
                )
            )
        else:
            candidates.append(candidate)
    candidates.sort(key=_candidate_rank, reverse=True)
    market_timestamp = (
        FIXTURE_TIMESTAMP
        if fixture
        else max(candle.timestamp for candle in market.daily("SPY"))
    )
    return ScanResult(
        scan_type=scan_type,
        generated_at=datetime.now(UTC),
        market_data_timestamp=market_timestamp,
        market=market_context,
        universe_count=len(symbols),
        evaluated_count=len(candidates) + len(rejected),
        ready=tuple(c for c in candidates if c.state == ReviewState.READY),
        ready_verify=tuple(
            c for c in candidates if c.state == ReviewState.READY_VERIFY
        ),
        developing=tuple(c for c in candidates if c.state == ReviewState.DEVELOPING),
        verify_contract=tuple(
            c for c in candidates if c.state == ReviewState.VERIFY_CONTRACT
        ),
        rejected=tuple(rejected),
        fixture=fixture,
    )


def readiness_check() -> int:
    load_local_env()
    warnings = validate_configuration(fixture=False)
    print(f"Bullish Participation v4 readiness check for {date.today().isoformat()}")
    print(f"Equity feed: {os.environ.get('ALPACA_FEED', 'iex')}")
    print(f"Option feed: {os.environ.get('ALPACA_OPTION_FEED', 'indicative')}")
    print(
        "Historical option research: "
        + ("Massive key configured" if os.environ.get("MASSIVE_API_KEY") else "not configured")
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


def main() -> int:
    _configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=[
            "post_close",
            "premarket",
            "four_hour",
            "daily_prep",
            "weekly_radar",
            "test_notification",
            "evaluate-signals",
            "replay",
            "research-report",
            "release-audit",
            "validate_configuration",
            "readiness_check",
        ],
    )
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument(
        "--scenario",
        default="default",
        choices=[
            "default",
            "ready",
            "ready_verify",
            "developing",
            "technical_watch",
            "zero",
        ],
    )
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--horizon", type=int, default=15)
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
        if args.command == "release-audit":
            from scripts.release_audit import run_release_audit

            errors = run_release_audit()
            if errors:
                for error in errors:
                    print(f"ERROR: {error}")
                return 1
            print("Bullish Participation v4 release audit passed.")
            return 0
        if args.command == "test_notification":
            from scanner.notifications import TELEGRAM_TEST_MESSAGE, TelegramNotifier

            if args.fixture:
                print(TELEGRAM_TEST_MESSAGE)
                return 0
            delivery = TelegramNotifier().send(TELEGRAM_TEST_MESSAGE)
            print(f"Telegram test: {delivery.status}")
            return 0 if delivery.delivered or delivery.status == "not_configured" else 1
        if args.command == "evaluate-signals":
            from scanner.research import ResearchLedger

            market, _, _ = _providers(args.fixture, args.scenario)
            with ResearchLedger() as ledger:
                inserted = ledger.evaluate_pending(market)
            print(f"Recorded {inserted} signal observations.")
            return 0
        if args.command == "research-report":
            from scanner.research import ResearchLedger

            with ResearchLedger() as ledger:
                markdown_path, json_path = ledger.write_summary()
            print(f"Markdown research report: {markdown_path}")
            print(f"JSON research report: {json_path}")
            return 0
        if args.command == "replay":
            from scanner.replay import sequential_replay, write_replay_report

            market, _, _ = _providers(args.fixture, args.scenario)
            start = date.fromisoformat(args.start) if args.start else None
            end = date.fromisoformat(args.end) if args.end else None
            hits = sequential_replay(
                market,
                args.symbol,
                configured_leader_symbols(fixture=args.fixture),
                start=start,
                end=end,
                horizon_sessions=args.horizon,
            )
            markdown_path, json_path = write_replay_report(hits)
            print(f"Replay signals: {len(hits)}")
            print(f"Markdown replay report: {markdown_path}")
            print(f"JSON replay report: {json_path}")
            return 0
        scan_type = (
            ScanType.POST_CLOSE
            if args.command in {"daily_prep", "weekly_radar"}
            else ScanType(args.command)
        )
        result = run_scan(
            scan_type, fixture=args.fixture, scenario=args.scenario
        )
        from scanner.notifications import notify_scan
        from scanner.reports import write_reports

        markdown_path, json_path = write_reports(result)
        dashboard_path = markdown_path.with_name("latest.html")
        if not args.fixture:
            from scanner.research import ResearchLedger

            with ResearchLedger() as ledger:
                ledger.record_scan(result)
        notify_scan(result, markdown_path, fixture=args.fixture)
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
        print(f"HTML dashboard: {dashboard_path}")
        return 0
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        return 2
    except Exception as exc:
        print(f"Scan failed safely: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
