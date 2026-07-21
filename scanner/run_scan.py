from __future__ import annotations

import argparse
import logging
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from scanner.config import ConfigurationError, load_local_env, validate_configuration
from scanner.contract_selection import select_contracts
from scanner.data_quality import DataQualityError, require_completed_candles
from scanner.data_trust import assess_data_trust, event_trust_reasons
from scanner.entry_plan import build_entry_plan
from scanner.evidence import (
    analyze_trend,
    annualized_realized_volatility,
    calculate_leadership,
)
from scanner.grading import (
    calculate_risk_score,
    chart_qualification_failures,
    classify_candidate,
    technical_qualification_failures,
)
from scanner.indicators import ema
from scanner.market_context import calculate_market_context
from scanner.models import (
    AssetMetadata,
    Candidate,
    Candle,
    ContractSelection,
    DataTrust,
    EntryPlan,
    EventRisk,
    EventRiskStatus,
    EvidenceScores,
    MarketContext,
    MomentumResult,
    PatternSignal,
    RejectedRecord,
    ReviewState,
    ScanResult,
    ScanType,
    StrategyLane,
    TimingAnalysis,
    TrendAnalysis,
)
from scanner.momentum import calculate_momentum
from scanner.patterns import detect_best_pattern
from scanner.providers.alpaca import AlpacaDataProvider
from scanner.providers.base import EventRiskProvider, MarketDataProvider, OptionDataProvider
from scanner.providers.cache import CachedMarketDataProvider, CachedOptionDataProvider
from scanner.providers.events import TrustedEventRiskProvider
from scanner.providers.fixtures import FIXTURE_TIMESTAMP, FixtureDataProvider
from scanner.strategy_profile import PROFILE
from scanner.timing import analyze_timing, market_hourly_confirmation
from scanner.universe import configured_leader_symbols, configured_symbols, metadata_for

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _TechnicalRecord:
    metadata: AssetMetadata
    trend: TrendAnalysis
    leadership: int | None
    pattern: PatternSignal
    daily_momentum: MomentumResult
    timing: TimingAnalysis
    entry: EntryPlan
    daily_realized_volatility: float | None
    provisional_scores: EvidenceScores


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
        return (
            CachedMarketDataProvider(provider),
            CachedOptionDataProvider(provider),
            provider,
        )
    alpaca = AlpacaDataProvider()
    return (
        CachedMarketDataProvider(alpaca),
        CachedOptionDataProvider(alpaca),
        TrustedEventRiskProvider(),
    )


def _fixture_symbols(scenario: str) -> list[str]:
    return {
        "ready": ["SSTR"],
        "ready_verify": ["APLUS"],
        "developing": ["BTIER"],
        "technical_watch": ["SSTR"],
        "zero": ["ZERO"],
    }.get(scenario, configured_symbols(fixture=True))


def _empty_contracts(feed: str) -> ContractSelection:
    return ContractSelection(
        score=0,
        primary=None,
        alternatives=(),
        feed=feed,
        realized_volatility=None,
        iv_to_realized_volatility=None,
        rejection_reasons=("not_fetched_until_technical_finalist",),
    )


def _unchecked_event(symbol: str, as_of: datetime) -> EventRisk:
    return EventRisk(
        symbol=symbol,
        status=EventRiskStatus.UNKNOWN,
        earnings_date=None,
        summary="Event source is checked only after chart qualification.",
        source="not_checked_until_technical_finalist",
        checked_at=as_of,
        source_timestamp=None,
    )


def _unchecked_trust(stock_feed: str, option_feed: str) -> DataTrust:
    return DataTrust(
        stock_feed=stock_feed,
        option_feed=option_feed,
        event_source="not_checked_until_technical_finalist",
        stock_trusted=stock_feed.lower() == PROFILE.required_stock_feed.lower(),
        option_trusted=False,
        event_trusted=False,
        quote_age_minutes=None,
        reasons=("not_checked_until_technical_finalist",),
    )


def _provider_rejection(
    record: _TechnicalRecord,
    *,
    stage: str,
    reason: str,
    error: Exception,
) -> RejectedRecord:
    """Create a fail-closed rejection without exposing provider response details."""
    log.warning(
        "Rejecting %s at %s because %s failed: %s",
        record.metadata.symbol,
        stage,
        reason,
        type(error).__name__,
    )
    return RejectedRecord(
        symbol=record.metadata.symbol,
        stage=stage,
        reason_codes=(reason,),
        details={
            "lane": record.metadata.lane.value,
            "pattern": record.pattern.pattern_type,
            "provider_error_type": type(error).__name__,
        },
    )


def _leader_universe_failures(
    daily: list[Candle],
) -> tuple[str, ...]:
    if not daily:
        return ("leader_daily_data_unavailable",)
    failures: list[str] = []
    if daily[-1].close < PROFILE.minimum_price:
        failures.append("leader_price_below_minimum")
    recent = daily[-20:]
    average_dollar_volume = (
        sum(candle.close * candle.volume for candle in recent) / len(recent)
        if recent
        else 0.0
    )
    if average_dollar_volume < PROFILE.minimum_average_daily_dollar_volume_usd:
        failures.append("leader_average_dollar_volume_below_minimum")
    return tuple(failures)


def _technical_record(
    symbol: str,
    *,
    market: MarketDataProvider,
    market_context: MarketContext,
    market_confirmation: bool,
    as_of: datetime,
    scan_type: ScanType,
) -> _TechnicalRecord:
    metadata = metadata_for(symbol)
    daily = market.daily(symbol)
    hourly = market.one_hour(symbol)
    weekly = market.weekly(symbol)
    require_completed_candles(daily, minimum=220, label=f"{symbol} daily")
    require_completed_candles(
        hourly,
        minimum=PROFILE.minimum_hourly_bars,
        label=f"{symbol} one_hour",
    )
    require_completed_candles(weekly, minimum=30, label=f"{symbol} weekly")
    if metadata.lane == StrategyLane.LEADER_WEEKLY:
        failures = _leader_universe_failures(daily)
        if failures:
            raise DataQualityError(",".join(failures))

    trend = analyze_trend(daily, weekly, PROFILE)
    leadership: int | None = None
    if metadata.lane == StrategyLane.LEADER_WEEKLY:
        leadership = calculate_leadership(
            daily,
            market.daily(metadata.peer_etf),
            market.daily("SPY"),
        )
    daily_htf = weekly[-1].close > ema([candle.close for candle in weekly], 21)
    daily_momentum = calculate_momentum(symbol, daily, "1D", daily_htf)
    timing = analyze_timing(
        symbol,
        hourly,
        daily_filter_passed=(
            trend.score >= PROFILE.thresholds.trend
            and trend.weekly_aligned
            and not trend.extended
        ),
        market_confirmation=market_confirmation,
        as_of=as_of,
        scan_type=scan_type,
        profile=PROFILE,
    )
    pattern = detect_best_pattern(daily, trend, PROFILE)
    lane_profile = PROFILE.lane(metadata.lane)
    entry = build_entry_plan(trend, pattern, timing, lane_profile)
    provisional_event = EventRisk(
        symbol=symbol,
        status=EventRiskStatus.CLEAR,
        earnings_date=None,
        summary="Provisional chart-stage event state.",
        source="chart_stage",
        checked_at=as_of,
        source_timestamp=as_of,
    )
    risk_score = calculate_risk_score(
        trend, pattern, entry, provisional_event, PROFILE
    )
    scores = EvidenceScores(
        trend=trend.score,
        leadership=leadership,
        setup=pattern.quality,
        timing=timing.score,
        market=market_context.score,
        contract=0,
        risk=risk_score,
    )
    return _TechnicalRecord(
        metadata=metadata,
        trend=trend,
        leadership=leadership,
        pattern=pattern,
        daily_momentum=daily_momentum,
        timing=timing,
        entry=entry,
        daily_realized_volatility=annualized_realized_volatility(daily),
        provisional_scores=scores,
    )


def _candidate_from_record(
    record: _TechnicalRecord,
    *,
    market_context: MarketContext,
    event: EventRisk,
    contracts: ContractSelection,
    data_trust: DataTrust,
    scores: EvidenceScores,
    state: ReviewState,
    reasons: tuple[str, ...],
) -> Candidate:
    return Candidate(
        symbol=record.metadata.symbol,
        company=record.metadata.company,
        sector=record.metadata.sector,
        peer_etf=record.metadata.peer_etf,
        lane=record.metadata.lane,
        trend=record.trend,
        leadership_score=record.leadership,
        pattern=record.pattern,
        daily_momentum=record.daily_momentum,
        timing=record.timing,
        market=market_context,
        event_risk=event,
        data_trust=data_trust,
        contracts=contracts,
        entry_plan=record.entry,
        scores=scores,
        state=state,
        reasons=reasons,
    )


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
            candidate.scores.timing,
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
    market_confirmation = market_hourly_confirmation(
        market.one_hour("SPY"),
        market.one_hour("QQQ"),
    )
    symbols = _fixture_symbols(scenario) if fixture else configured_symbols()
    candidates: list[Candidate] = []
    rejected: list[RejectedRecord] = []
    leader_symbols = [
        symbol
        for symbol in symbols
        if metadata_for(symbol).lane == StrategyLane.LEADER_WEEKLY
    ]
    eligible_leaders = set(leader_symbols)
    eligibility_error: str | None = None
    if PROFILE.options_required and leader_symbols:
        leader_lane = PROFILE.lane(StrategyLane.LEADER_WEEKLY)
        try:
            eligible_leaders = options.eligible_underlyings(
                leader_symbols,
                as_of.date() + timedelta(days=leader_lane.hard_dte[0]),
                as_of.date() + timedelta(days=leader_lane.hard_dte[1]),
            )
        except (OSError, RuntimeError, ValueError) as exc:
            eligible_leaders = set()
            eligibility_error = str(exc)

    for symbol in symbols:
        metadata = metadata_for(symbol)
        if (
            metadata.lane == StrategyLane.LEADER_WEEKLY
            and symbol not in eligible_leaders
        ):
            reason = (
                "leader_options_eligibility_unavailable"
                if eligibility_error is not None
                else "leader_no_eligible_weekly_expiration"
            )
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="universe",
                    reason_codes=(reason,),
                    details={
                        "lane": metadata.lane.value,
                        "eligibility_error": eligibility_error or "",
                    },
                )
            )
            continue
        try:
            record = _technical_record(
                symbol,
                market=market,
                market_context=market_context,
                market_confirmation=market_confirmation,
                as_of=as_of,
                scan_type=scan_type,
            )
        except (DataQualityError, ValueError, RuntimeError) as exc:
            reason_codes = tuple(
                part for part in str(exc).split(",") if part
            ) or ("scan_error",)
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="universe_or_data_quality",
                    reason_codes=reason_codes,
                    details={"error": str(exc)},
                )
            )
            continue

        chart_failures = chart_qualification_failures(
            lane=record.metadata.lane,
            scores=record.provisional_scores,
            trend=record.trend,
            pattern=record.pattern,
            timing=record.timing,
            market=market_context,
            profile=PROFILE,
        )
        hard_chart_failures = {
            "below_sma200",
            "extended_beyond_configured_atr_limit",
            "hostile_market_regime",
            "pattern_failed",
            "pattern_stale",
            "pattern_not_promoted_for_production",
        }
        if chart_failures:
            if any(reason in hard_chart_failures for reason in chart_failures):
                rejected.append(
                    RejectedRecord(
                        symbol=symbol,
                        stage="technical",
                        reason_codes=chart_failures,
                        details={
                            "lane": record.metadata.lane.value,
                            "pattern": record.pattern.pattern_type,
                        },
                    )
                )
                continue
            event = _unchecked_event(symbol, as_of)
            contracts = _empty_contracts(getattr(options, "option_feed", "unknown"))
            candidates.append(
                _candidate_from_record(
                    record,
                    market_context=market_context,
                    event=event,
                    contracts=contracts,
                    data_trust=_unchecked_trust(
                        getattr(market, "stock_feed", "unknown"),
                        getattr(options, "option_feed", "unknown"),
                    ),
                    scores=record.provisional_scores,
                    state=ReviewState.DEVELOPING,
                    reasons=chart_failures,
                )
            )
            continue

        try:
            event = events.event_risk(symbol, as_of, record.metadata.lane)
        except (OSError, RuntimeError, ValueError) as exc:
            rejected.append(
                _provider_rejection(
                    record,
                    stage="event",
                    reason="event_data_unavailable",
                    error=exc,
                )
            )
            continue
        event_freshness_failures = event_trust_reasons(event, as_of, PROFILE)
        if event_freshness_failures:
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="event",
                    reason_codes=event_freshness_failures,
                    details={
                        "event_source": event.source,
                        "event_summary": event.summary,
                    },
                )
            )
            continue
        risk_score = calculate_risk_score(
            record.trend,
            record.pattern,
            record.entry,
            event,
            PROFILE,
        )
        pre_contract_scores = EvidenceScores(
            trend=record.provisional_scores.trend,
            leadership=record.provisional_scores.leadership,
            setup=record.provisional_scores.setup,
            timing=record.provisional_scores.timing,
            market=record.provisional_scores.market,
            contract=0,
            risk=risk_score,
        )
        event_failures = technical_qualification_failures(
            lane=record.metadata.lane,
            scores=pre_contract_scores,
            trend=record.trend,
            pattern=record.pattern,
            timing=record.timing,
            market=market_context,
            event=event,
            profile=PROFILE,
        )
        if event_failures:
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="event",
                    reason_codes=event_failures,
                    details={
                        "event_source": event.source,
                        "event_summary": event.summary,
                    },
                )
            )
            continue

        lane_profile = PROFILE.lane(record.metadata.lane)
        expiry_start = as_of.date() + timedelta(days=lane_profile.hard_dte[0])
        expiry_end = as_of.date() + timedelta(days=lane_profile.hard_dte[1])
        try:
            chain = options.call_chain(symbol, expiry_start, expiry_end, as_of)
        except (OSError, RuntimeError, ValueError) as exc:
            rejected.append(
                _provider_rejection(
                    record,
                    stage="contract",
                    reason="option_chain_unavailable",
                    error=exc,
                )
            )
            continue
        initial = select_contracts(
            chain,
            lane_profile,
            as_of,
            record.daily_realized_volatility,
            record.trend.close,
            maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
            feed_when_empty=getattr(options, "option_feed", "unknown"),
        )
        top = (
            [initial.primary, *initial.alternatives]
            if initial.primary is not None
            else []
        )
        top_contracts = [contract for contract in top if contract is not None]
        previous_quotes = {
            contract.contract_symbol: contract for contract in top_contracts
        }
        try:
            refreshed = options.latest_quotes(top_contracts, as_of)
        except (OSError, RuntimeError, ValueError) as exc:
            rejected.append(
                _provider_rejection(
                    record,
                    stage="contract",
                    reason="option_requote_unavailable",
                    error=exc,
                )
            )
            continue
        contracts = select_contracts(
            refreshed if top_contracts else chain,
            lane_profile,
            as_of,
            record.daily_realized_volatility,
            record.trend.close,
            maximum_quote_age_minutes=PROFILE.maximum_quote_age_minutes,
            feed_when_empty=getattr(options, "option_feed", "unknown"),
            previous_quotes=previous_quotes,
            requoted_count=len(refreshed),
        )
        data_trust = assess_data_trust(
            stock_feed=getattr(market, "stock_feed", "unknown"),
            contracts=contracts,
            event=event,
            as_of=as_of,
            profile=PROFILE,
        )
        scores = EvidenceScores(
            trend=pre_contract_scores.trend,
            leadership=pre_contract_scores.leadership,
            setup=pre_contract_scores.setup,
            timing=pre_contract_scores.timing,
            market=pre_contract_scores.market,
            contract=contracts.score,
            risk=pre_contract_scores.risk,
        )
        state, reasons = classify_candidate(
            lane=record.metadata.lane,
            scores=scores,
            trend=record.trend,
            pattern=record.pattern,
            timing=record.timing,
            market=market_context,
            event=event,
            contracts=contracts,
            data_trust=data_trust,
            profile=PROFILE,
        )
        candidate = _candidate_from_record(
            record,
            market_context=market_context,
            event=event,
            contracts=contracts,
            data_trust=data_trust,
            scores=scores,
            state=state,
            reasons=reasons,
        )
        if state == ReviewState.REJECTED:
            rejected.append(
                RejectedRecord(
                    symbol=symbol,
                    stage="contract",
                    reason_codes=reasons or ("not_qualified",),
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
        max(candle.timestamp for candle in market.one_hour("SPY"))
        + timedelta(hours=1)
        if scan_type == ScanType.INTRADAY
        else max(candle.timestamp for candle in market.daily("SPY"))
    )
    return ScanResult(
        scan_type=scan_type,
        generated_at=as_of if fixture else datetime.now(UTC),
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
        validation_state=PROFILE.validation_state,
    )


def readiness_check() -> int:
    load_local_env()
    warnings = validate_configuration(fixture=False)
    print(f"Bullish Weekly Participation v5 readiness check for {date.today().isoformat()}")
    print(f"Equity feed: {os.environ.get('ALPACA_FEED', 'sip')}")
    print(f"Option feed: {os.environ.get('ALPACA_OPTION_FEED', 'opra')}")
    print(
        "Historical option research: "
        + (
            "Massive key configured"
            if os.environ.get("MASSIVE_API_KEY")
            else "not configured"
        )
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
            "intraday",
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
            print("Bullish Weekly Participation v5 release audit passed.")
            return 0
        if args.command == "test_notification":
            from scanner.notifications import TELEGRAM_TEST_MESSAGE, TelegramNotifier

            if args.fixture:
                print(TELEGRAM_TEST_MESSAGE)
                return 0
            delivery = TelegramNotifier().send(TELEGRAM_TEST_MESSAGE)
            print(f"Telegram test: {delivery.status}")
            return (
                0
                if delivery.delivered or delivery.status == "not_configured"
                else 1
            )
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
        result = run_scan(scan_type, fixture=args.fixture, scenario=args.scenario)
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
