from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import mean, median


@dataclass(frozen=True)
class ContractBar:
    """Minute-sequenced underlying evidence paired with the latest option quote."""

    timestamp: datetime
    underlying_high: float
    underlying_low: float
    underlying_close: float
    bid: float
    ask: float
    dte: int
    underlying_open: float | None = None
    quote_age_minutes: float = 0.0
    event_blocked: bool = False

    @property
    def spread(self) -> float:
        return max(self.ask - self.bid, 0.0)


@dataclass(frozen=True)
class LongCallExperiment:
    experiment_id: str
    lane: str
    pattern_type: str
    market_regime: str
    signal_timestamp: datetime
    trigger: float
    invalidation: float
    objective: float
    confirmed_at_signal: bool
    bars: tuple[ContractBar, ...]
    trigger_timestamp: datetime | None = None
    symbol: str = ""


@dataclass(frozen=True)
class FillPolicy:
    name: str
    maximum_hold_sessions: int
    no_progress_sessions: int
    requalify_dte: int
    exit_at_objective: bool = True
    entry_spread_fraction: float = 1.0
    exit_spread_fraction: float = 0.0
    commission_per_contract: float = 0.65
    maximum_quote_age_minutes: float = 2.0


@dataclass(frozen=True)
class LongCallOutcome:
    experiment_id: str
    policy_name: str
    entered: bool
    entry_timestamp: datetime | None
    exit_timestamp: datetime | None
    entry_price: float | None
    exit_price: float | None
    return_percent: float | None
    maximum_favorable_excursion: float | None
    maximum_adverse_excursion: float | None
    maximum_loss_per_contract: float | None
    exit_reason: str


@dataclass(frozen=True)
class ExperimentMetrics:
    policy_name: str
    observation_count: int
    entered_count: int
    median_return_percent: float | None
    mean_return_percent: float | None
    positive_return_percent: float | None
    worst_return_percent: float | None
    maximum_drawdown_percent: float | None
    overlap_adjusted_count: int = 0
    maximum_concurrent_positions: int = 0
    largest_pattern_concentration_percent: float | None = None


@dataclass(frozen=True)
class WalkForwardFold:
    fold_number: int
    training_observations: int
    test_observations: int
    selected_policy: str
    training_metrics: ExperimentMetrics
    test_metrics: ExperimentMetrics
    purged_training_observations: int = 0
    embargoed_test_observations: int = 0
    test_lane_counts: tuple[tuple[str, int], ...] = ()
    test_pattern_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    reason: str
    observation_count: int
    positive_fold_percent: float
    historical_gates_passed: bool = False
    shadow_gates_passed: bool = False
    failed_gates: tuple[str, ...] = ()


def _fill_price(bar: ContractBar, spread_fraction: float) -> float:
    fraction = min(max(spread_fraction, 0.0), 1.0)
    return bar.bid + bar.spread * fraction


def _net_return_percent(
    entry_price: float,
    exit_price: float,
    commission_per_contract: float,
) -> float:
    entry_cash = entry_price * 100 + commission_per_contract
    exit_cash = max(exit_price * 100 - commission_per_contract, 0.0)
    return ((exit_cash / entry_cash) - 1) * 100


def _valid_quote(bar: ContractBar, policy: FillPolicy) -> bool:
    return (
        bar.bid >= 0
        and bar.ask >= bar.bid
        and bar.ask > 0
        and bar.quote_age_minutes <= policy.maximum_quote_age_minutes
    )


def _no_entry(
    experiment: LongCallExperiment,
    policy: FillPolicy,
    reason: str,
    *,
    exit_timestamp: datetime | None = None,
) -> LongCallOutcome:
    return LongCallOutcome(
        experiment_id=experiment.experiment_id,
        policy_name=policy.name,
        entered=False,
        entry_timestamp=None,
        exit_timestamp=exit_timestamp,
        entry_price=None,
        exit_price=None,
        return_percent=None,
        maximum_favorable_excursion=None,
        maximum_adverse_excursion=None,
        maximum_loss_per_contract=None,
        exit_reason=reason,
    )


def _trigger_time(
    experiment: LongCallExperiment,
    bars: tuple[ContractBar, ...],
) -> tuple[datetime | None, ContractBar | None, str | None, datetime | None]:
    not_before = experiment.signal_timestamp
    if (
        experiment.trigger_timestamp is not None
        and experiment.trigger_timestamp > not_before
    ):
        not_before = experiment.trigger_timestamp
    eligible = tuple(bar for bar in bars if bar.timestamp >= not_before)
    if experiment.confirmed_at_signal or experiment.trigger_timestamp is not None:
        return not_before, next((bar for bar in eligible), None), None, None
    for bar in eligible:
        trigger_touched = bar.underlying_high >= experiment.trigger
        invalidation_touched = bar.underlying_low <= experiment.invalidation
        if invalidation_touched and not trigger_touched:
            return None, None, "invalidated_before_entry", bar.timestamp
        if trigger_touched:
            return bar.timestamp, bar, None, None
    return None, None, None, None


def simulate_long_call(
    experiment: LongCallExperiment,
    policy: FillPolicy,
) -> LongCallOutcome:
    bars = tuple(
        sorted(
            (
                bar
                for bar in experiment.bars
                if bar.timestamp >= experiment.signal_timestamp
            ),
            key=lambda bar: bar.timestamp,
        )
    )
    if not bars:
        return _no_entry(experiment, policy, "no_post_signal_data")

    trigger_time, trigger_bar, trigger_failure, failure_timestamp = _trigger_time(
        experiment,
        bars,
    )
    if trigger_failure is not None:
        return _no_entry(
            experiment,
            policy,
            trigger_failure,
            exit_timestamp=failure_timestamp,
        )
    if trigger_time is None:
        return _no_entry(experiment, policy, "trigger_not_reached")

    entry_index: int | None = None
    for index, bar in enumerate(bars):
        if bar.timestamp < trigger_time:
            continue
        if bar.underlying_low <= experiment.invalidation and not _valid_quote(bar, policy):
            return _no_entry(
                experiment,
                policy,
                "invalidated_before_fresh_quote",
                exit_timestamp=bar.timestamp,
            )
        if _valid_quote(bar, policy):
            entry_index = index
            break
    if entry_index is None:
        return _no_entry(experiment, policy, "no_fresh_quote")

    entry_bar = bars[entry_index]
    entry_price = _fill_price(entry_bar, policy.entry_spread_fraction)
    entry_underlying = entry_bar.underlying_close
    same_bar_ambiguous = (
        trigger_bar is not None
        and trigger_bar.timestamp == entry_bar.timestamp
        and not experiment.confirmed_at_signal
        and trigger_bar.underlying_high >= experiment.trigger
        and trigger_bar.underlying_low <= experiment.invalidation
    )

    liquidation_returns: list[float] = []
    session_closes: dict[object, float] = {}
    exit_bar = entry_bar
    exit_reason = "end_of_data"
    pending_exit_reason: str | None = "same_bar_ambiguous" if same_bar_ambiguous else None
    last_fresh_bar = entry_bar

    for bar in bars[entry_index:]:
        if _valid_quote(bar, policy):
            last_fresh_bar = bar
            liquidation_returns.append(
                _net_return_percent(
                    entry_price,
                    _fill_price(bar, policy.exit_spread_fraction),
                    policy.commission_per_contract,
                )
            )
        session_closes[bar.timestamp.date()] = bar.underlying_close
        session_count = len(session_closes)

        if pending_exit_reason is None:
            if bar.event_blocked:
                pending_exit_reason = "event_risk"
            elif bar.underlying_low <= experiment.invalidation:
                pending_exit_reason = "underlying_invalidation"
            elif policy.exit_at_objective and bar.underlying_high >= experiment.objective:
                pending_exit_reason = "planning_objective"
            elif bar.dte <= policy.requalify_dte:
                pending_exit_reason = "dte_requalification"
            elif (
                session_count >= policy.no_progress_sessions
                and max(session_closes.values()) <= entry_underlying
            ):
                pending_exit_reason = "no_progress_review"
            elif session_count >= policy.maximum_hold_sessions:
                pending_exit_reason = "maximum_hold"

        if pending_exit_reason is not None and _valid_quote(bar, policy):
            exit_bar = bar
            exit_reason = pending_exit_reason
            break
    else:
        exit_bar = last_fresh_bar
        if pending_exit_reason is not None:
            exit_reason = f"{pending_exit_reason}_next_quote_unavailable"

    final_exit = _fill_price(exit_bar, policy.exit_spread_fraction)
    final_return = _net_return_percent(
        entry_price,
        final_exit,
        policy.commission_per_contract,
    )
    if not liquidation_returns:
        liquidation_returns.append(final_return)
    return LongCallOutcome(
        experiment_id=experiment.experiment_id,
        policy_name=policy.name,
        entered=True,
        entry_timestamp=entry_bar.timestamp,
        exit_timestamp=exit_bar.timestamp,
        entry_price=entry_price,
        exit_price=final_exit,
        return_percent=final_return,
        maximum_favorable_excursion=max(liquidation_returns),
        maximum_adverse_excursion=min(liquidation_returns),
        maximum_loss_per_contract=entry_price * 100 + policy.commission_per_contract,
        exit_reason=exit_reason,
    )


def _overlap_metrics(
    outcomes: tuple[LongCallOutcome, ...],
    experiments: tuple[LongCallExperiment, ...],
) -> tuple[int, int, float | None]:
    entered = tuple(
        outcome
        for outcome in outcomes
        if outcome.entered
        and outcome.entry_timestamp is not None
        and outcome.exit_timestamp is not None
    )
    if not entered:
        return 0, 0, None

    events: list[tuple[datetime, int]] = []
    for outcome in entered:
        entry_timestamp = outcome.entry_timestamp
        exit_timestamp = outcome.exit_timestamp
        assert entry_timestamp is not None
        assert exit_timestamp is not None
        events.append((entry_timestamp, 1))
        events.append((exit_timestamp, -1))
    concurrent = 0
    maximum_concurrent = 0
    for _, change in sorted(events, key=lambda item: (item[0], item[1])):
        concurrent += change
        maximum_concurrent = max(maximum_concurrent, concurrent)

    non_overlapping = 0
    last_exit: datetime | None = None
    for outcome in sorted(entered, key=lambda item: item.entry_timestamp or datetime.min):
        assert outcome.entry_timestamp is not None
        assert outcome.exit_timestamp is not None
        if last_exit is None or outcome.entry_timestamp > last_exit:
            non_overlapping += 1
            last_exit = outcome.exit_timestamp

    experiment_by_id = {item.experiment_id: item for item in experiments}
    pattern_counts = Counter(
        experiment_by_id[outcome.experiment_id].pattern_type
        for outcome in entered
        if outcome.experiment_id in experiment_by_id
    )
    concentration = (
        max(pattern_counts.values()) / len(entered) * 100 if pattern_counts else None
    )
    return non_overlapping, maximum_concurrent, concentration


def summarize_outcomes(
    outcomes: tuple[LongCallOutcome, ...],
    policy_name: str,
    experiments: tuple[LongCallExperiment, ...] = (),
) -> ExperimentMetrics:
    returns = [
        outcome.return_percent
        for outcome in outcomes
        if outcome.entered and outcome.return_percent is not None
    ]
    overlap_count, maximum_concurrent, concentration = _overlap_metrics(
        outcomes,
        experiments,
    )
    if not returns:
        return ExperimentMetrics(
            policy_name=policy_name,
            observation_count=len(outcomes),
            entered_count=0,
            median_return_percent=None,
            mean_return_percent=None,
            positive_return_percent=None,
            worst_return_percent=None,
            maximum_drawdown_percent=None,
            overlap_adjusted_count=overlap_count,
            maximum_concurrent_positions=maximum_concurrent,
            largest_pattern_concentration_percent=concentration,
        )
    equity = 1.0
    peak = 1.0
    maximum_drawdown = 0.0
    for value in returns:
        equity *= 1 + value / 100
        peak = max(peak, equity)
        drawdown = ((equity / peak) - 1) * 100
        maximum_drawdown = min(maximum_drawdown, drawdown)
    return ExperimentMetrics(
        policy_name=policy_name,
        observation_count=len(outcomes),
        entered_count=len(returns),
        median_return_percent=median(returns),
        mean_return_percent=mean(returns),
        positive_return_percent=sum(value > 0 for value in returns) / len(returns) * 100,
        worst_return_percent=min(returns),
        maximum_drawdown_percent=maximum_drawdown,
        overlap_adjusted_count=overlap_count,
        maximum_concurrent_positions=maximum_concurrent,
        largest_pattern_concentration_percent=concentration,
    )


def evaluate_policy(
    experiments: tuple[LongCallExperiment, ...],
    policy: FillPolicy,
) -> ExperimentMetrics:
    outcomes = tuple(simulate_long_call(experiment, policy) for experiment in experiments)
    return summarize_outcomes(outcomes, policy.name, experiments)


def _robustness_score(metrics: ExperimentMetrics) -> float:
    if (
        metrics.median_return_percent is None
        or metrics.mean_return_percent is None
        or metrics.worst_return_percent is None
        or metrics.maximum_drawdown_percent is None
    ):
        return float("-inf")
    concentration_penalty = (
        max(metrics.largest_pattern_concentration_percent - 40, 0) * 0.05
        if metrics.largest_pattern_concentration_percent is not None
        else 0.0
    )
    overlap_penalty = max(
        metrics.entered_count - metrics.overlap_adjusted_count,
        0,
    ) * 0.02
    return (
        metrics.median_return_percent
        + 0.25 * metrics.mean_return_percent
        + 0.10 * metrics.worst_return_percent
        + 0.15 * metrics.maximum_drawdown_percent
        - concentration_penalty
        - overlap_penalty
    )


def _entered_counts(
    experiments: tuple[LongCallExperiment, ...],
    outcomes: tuple[LongCallOutcome, ...],
    field_name: str,
) -> tuple[tuple[str, int], ...]:
    by_id = {item.experiment_id: item for item in experiments}
    counts = Counter(
        str(getattr(by_id[outcome.experiment_id], field_name))
        for outcome in outcomes
        if outcome.entered and outcome.experiment_id in by_id
    )
    return tuple(sorted(counts.items()))


def walk_forward_evaluate(
    experiments: tuple[LongCallExperiment, ...],
    policies: tuple[FillPolicy, ...],
    *,
    folds: int = 4,
    purge_sessions: int = 5,
    embargo_sessions: int = 1,
) -> tuple[WalkForwardFold, ...]:
    if folds < 2:
        raise ValueError("Walk-forward evaluation requires at least two folds.")
    if not policies:
        raise ValueError("At least one fill policy is required.")
    if purge_sessions < 0 or embargo_sessions < 0:
        raise ValueError("Purge and embargo sessions cannot be negative.")
    ordered = tuple(sorted(experiments, key=lambda item: item.signal_timestamp))
    fold_size = max(len(ordered) // folds, 1)
    results: list[WalkForwardFold] = []
    for fold_number in range(1, folds):
        train_end = min(fold_number * fold_size, len(ordered))
        test_end = (
            len(ordered)
            if fold_number == folds - 1
            else min((fold_number + 1) * fold_size, len(ordered))
        )
        raw_training = ordered[:train_end]
        raw_test = ordered[train_end:test_end]
        if not raw_training or not raw_test:
            continue
        test_boundary = raw_test[0].signal_timestamp
        training_cutoff = test_boundary - timedelta(days=purge_sessions)
        test_cutoff = test_boundary + timedelta(days=embargo_sessions)
        training = tuple(
            item for item in raw_training if item.signal_timestamp < training_cutoff
        )
        test = tuple(item for item in raw_test if item.signal_timestamp >= test_cutoff)
        if not training or not test:
            continue
        training_metrics = tuple(
            evaluate_policy(training, policy) for policy in policies
        )
        best = max(training_metrics, key=_robustness_score)
        selected = next(policy for policy in policies if policy.name == best.policy_name)
        test_outcomes = tuple(
            simulate_long_call(experiment, selected) for experiment in test
        )
        results.append(
            WalkForwardFold(
                fold_number=fold_number,
                training_observations=len(training),
                test_observations=len(test),
                selected_policy=selected.name,
                training_metrics=best,
                test_metrics=summarize_outcomes(test_outcomes, selected.name, test),
                purged_training_observations=len(raw_training) - len(training),
                embargoed_test_observations=len(raw_test) - len(test),
                test_lane_counts=_entered_counts(test, test_outcomes, "lane"),
                test_pattern_counts=_entered_counts(
                    test,
                    test_outcomes,
                    "pattern_type",
                ),
            )
        )
    return tuple(results)


def promotion_decision(
    folds: tuple[WalkForwardFold, ...],
    *,
    minimum_observations_per_lane: int = 150,
    minimum_observations_per_pattern: int = 40,
    frozen_baseline_median_percent: float | None = None,
    neighboring_parameter_stable: bool = False,
    pessimistic_fill_resilient: bool = False,
    maximum_allowed_drawdown_percent: float = -35.0,
    maximum_pattern_concentration_percent: float = 40.0,
    shadow_calendar_days: int = 0,
    shadow_opportunities: int = 0,
    minimum_shadow_days: int = 45,
    minimum_shadow_opportunities: int = 50,
) -> PromotionDecision:
    observation_count = sum(fold.test_metrics.entered_count for fold in folds)
    positive_folds = sum(
        fold.test_metrics.median_return_percent is not None
        and fold.test_metrics.median_return_percent > 0
        for fold in folds
    )
    positive_fold_percent = positive_folds / len(folds) * 100 if folds else 0.0
    lane_counts: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    for fold in folds:
        lane_counts.update(dict(fold.test_lane_counts))
        pattern_counts.update(dict(fold.test_pattern_counts))

    failed: list[str] = []
    required_lanes = {"index_weekly", "leader_weekly"}
    if any(lane_counts[lane] < minimum_observations_per_lane for lane in required_lanes):
        failed.append("lane_sample")
    if not pattern_counts or any(
        count < minimum_observations_per_pattern for count in pattern_counts.values()
    ):
        failed.append("pattern_sample")
    if positive_fold_percent < 60:
        failed.append("positive_folds")

    held_out_medians = [
        fold.test_metrics.median_return_percent
        for fold in folds
        if fold.test_metrics.median_return_percent is not None
    ]
    held_out_median = median(held_out_medians) if held_out_medians else None
    if (
        frozen_baseline_median_percent is None
        or held_out_median is None
        or held_out_median <= frozen_baseline_median_percent
    ):
        failed.append("frozen_baseline_improvement")

    drawdowns = [
        fold.test_metrics.maximum_drawdown_percent
        for fold in folds
        if fold.test_metrics.maximum_drawdown_percent is not None
    ]
    if not drawdowns or min(drawdowns) < maximum_allowed_drawdown_percent:
        failed.append("drawdown")
    concentrations = [
        fold.test_metrics.largest_pattern_concentration_percent
        for fold in folds
        if fold.test_metrics.largest_pattern_concentration_percent is not None
    ]
    if (
        not concentrations
        or max(concentrations) > maximum_pattern_concentration_percent
    ):
        failed.append("concentration")
    if not neighboring_parameter_stable:
        failed.append("neighboring_parameter_stability")
    if not pessimistic_fill_resilient:
        failed.append("pessimistic_fill_resilience")

    historical_passed = not failed
    shadow_failed = []
    if shadow_calendar_days < minimum_shadow_days:
        shadow_failed.append("shadow_days")
    if shadow_opportunities < minimum_shadow_opportunities:
        shadow_failed.append("shadow_opportunities")
    shadow_passed = not shadow_failed

    if not historical_passed:
        sample_failures = {"lane_sample", "pattern_sample"}
        status = (
            "insufficient_evidence"
            if sample_failures.intersection(failed)
            else "rejected"
        )
        return PromotionDecision(
            status=status,
            reason=(
                "Historical promotion gates remain unmet; validation_state must stay "
                "research_default."
            ),
            observation_count=observation_count,
            positive_fold_percent=positive_fold_percent,
            failed_gates=tuple(failed),
        )
    if not shadow_passed:
        return PromotionDecision(
            status="eligible_for_shadow",
            reason=(
                "Historical gates passed, but the forward shadow duration and "
                "opportunity gates remain incomplete."
            ),
            observation_count=observation_count,
            positive_fold_percent=positive_fold_percent,
            historical_gates_passed=True,
            failed_gates=tuple(shadow_failed),
        )
    return PromotionDecision(
        status="eligible_for_promotion_review",
        reason=(
            "Precommitted historical and shadow gates passed. A documented manual "
            "review is still required before changing validation_state."
        ),
        observation_count=observation_count,
        positive_fold_percent=positive_fold_percent,
        historical_gates_passed=True,
        shadow_gates_passed=True,
    )
