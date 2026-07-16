from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean, median


@dataclass(frozen=True)
class ContractBar:
    timestamp: datetime
    underlying_high: float
    underlying_low: float
    underlying_close: float
    bid: float
    ask: float
    dte: int
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
    maximum_quote_age_minutes: float = 30.0


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


@dataclass(frozen=True)
class WalkForwardFold:
    fold_number: int
    training_observations: int
    test_observations: int
    selected_policy: str
    training_metrics: ExperimentMetrics
    test_metrics: ExperimentMetrics


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    reason: str
    observation_count: int
    positive_fold_percent: float


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


def simulate_long_call(
    experiment: LongCallExperiment,
    policy: FillPolicy,
) -> LongCallOutcome:
    entry_index: int | None = None
    entry_price: float | None = None
    entry_underlying: float | None = None
    valid_bars = [
        (index, bar)
        for index, bar in enumerate(experiment.bars)
        if _valid_quote(bar, policy)
    ]
    if not valid_bars:
        return LongCallOutcome(
            experiment_id=experiment.experiment_id,
            policy_name=policy.name,
            entered=False,
            entry_timestamp=None,
            exit_timestamp=None,
            entry_price=None,
            exit_price=None,
            return_percent=None,
            maximum_favorable_excursion=None,
            maximum_adverse_excursion=None,
            maximum_loss_per_contract=None,
            exit_reason="no_fresh_quote",
        )

    for index, bar in valid_bars:
        trigger_touched = experiment.confirmed_at_signal or (
            bar.underlying_high >= experiment.trigger
        )
        invalidation_touched = bar.underlying_low <= experiment.invalidation
        if not trigger_touched:
            if invalidation_touched:
                return LongCallOutcome(
                    experiment_id=experiment.experiment_id,
                    policy_name=policy.name,
                    entered=False,
                    entry_timestamp=None,
                    exit_timestamp=bar.timestamp,
                    entry_price=None,
                    exit_price=None,
                    return_percent=None,
                    maximum_favorable_excursion=None,
                    maximum_adverse_excursion=None,
                    maximum_loss_per_contract=None,
                    exit_reason="invalidated_before_entry",
                )
            continue
        entry_index = index
        entry_price = _fill_price(bar, policy.entry_spread_fraction)
        entry_underlying = bar.underlying_close
        break

    if entry_index is None or entry_price is None or entry_underlying is None:
        return LongCallOutcome(
            experiment_id=experiment.experiment_id,
            policy_name=policy.name,
            entered=False,
            entry_timestamp=None,
            exit_timestamp=None,
            entry_price=None,
            exit_price=None,
            return_percent=None,
            maximum_favorable_excursion=None,
            maximum_adverse_excursion=None,
            maximum_loss_per_contract=None,
            exit_reason="trigger_not_reached",
        )

    eligible_after_entry = [
        (index, bar) for index, bar in valid_bars if index >= entry_index
    ]
    liquidation_returns: list[float] = []
    closes: list[float] = []
    entry_bar = eligible_after_entry[0][1]
    exit_bar = eligible_after_entry[-1][1]
    exit_reason = "end_of_data"

    for session, (_, bar) in enumerate(eligible_after_entry, start=1):
        exit_price = _fill_price(bar, policy.exit_spread_fraction)
        liquidation_returns.append(
            _net_return_percent(entry_price, exit_price, policy.commission_per_contract)
        )
        closes.append(bar.underlying_close)
        same_bar_ambiguous = (
            session == 1
            and not experiment.confirmed_at_signal
            and bar.underlying_high >= experiment.trigger
            and bar.underlying_low <= experiment.invalidation
        )
        if same_bar_ambiguous:
            exit_bar = bar
            exit_reason = "same_bar_ambiguous"
            break
        if bar.event_blocked:
            exit_bar = bar
            exit_reason = "event_risk"
            break
        if bar.underlying_low <= experiment.invalidation:
            exit_bar = bar
            exit_reason = "underlying_invalidation"
            break
        if policy.exit_at_objective and bar.underlying_high >= experiment.objective:
            exit_bar = bar
            exit_reason = "planning_objective"
            break
        if bar.dte <= policy.requalify_dte:
            exit_bar = bar
            exit_reason = "dte_requalification"
            break
        if (
            session >= policy.no_progress_sessions
            and max(closes) <= entry_underlying
        ):
            exit_bar = bar
            exit_reason = "no_progress_review"
            break
        if session >= policy.maximum_hold_sessions:
            exit_bar = bar
            exit_reason = "maximum_hold"
            break

    final_exit = _fill_price(exit_bar, policy.exit_spread_fraction)
    return LongCallOutcome(
        experiment_id=experiment.experiment_id,
        policy_name=policy.name,
        entered=True,
        entry_timestamp=entry_bar.timestamp,
        exit_timestamp=exit_bar.timestamp,
        entry_price=entry_price,
        exit_price=final_exit,
        return_percent=_net_return_percent(
            entry_price,
            final_exit,
            policy.commission_per_contract,
        ),
        maximum_favorable_excursion=max(liquidation_returns),
        maximum_adverse_excursion=min(liquidation_returns),
        maximum_loss_per_contract=entry_price * 100 + policy.commission_per_contract,
        exit_reason=exit_reason,
    )


def summarize_outcomes(
    outcomes: tuple[LongCallOutcome, ...],
    policy_name: str,
) -> ExperimentMetrics:
    returns = [
        outcome.return_percent
        for outcome in outcomes
        if outcome.entered and outcome.return_percent is not None
    ]
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
    )


def evaluate_policy(
    experiments: tuple[LongCallExperiment, ...],
    policy: FillPolicy,
) -> ExperimentMetrics:
    outcomes = tuple(simulate_long_call(experiment, policy) for experiment in experiments)
    return summarize_outcomes(outcomes, policy.name)


def _robustness_score(metrics: ExperimentMetrics) -> float:
    if (
        metrics.median_return_percent is None
        or metrics.mean_return_percent is None
        or metrics.worst_return_percent is None
        or metrics.maximum_drawdown_percent is None
    ):
        return float("-inf")
    return (
        metrics.median_return_percent
        + 0.25 * metrics.mean_return_percent
        + 0.10 * metrics.worst_return_percent
        + 0.15 * metrics.maximum_drawdown_percent
    )


def walk_forward_evaluate(
    experiments: tuple[LongCallExperiment, ...],
    policies: tuple[FillPolicy, ...],
    *,
    folds: int = 4,
) -> tuple[WalkForwardFold, ...]:
    if folds < 2:
        raise ValueError("Walk-forward evaluation requires at least two folds.")
    if not policies:
        raise ValueError("At least one fill policy is required.")
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
        training = ordered[:train_end]
        test = ordered[train_end:test_end]
        if not training or not test:
            continue
        training_metrics = tuple(
            evaluate_policy(training, policy) for policy in policies
        )
        best = max(training_metrics, key=_robustness_score)
        selected = next(policy for policy in policies if policy.name == best.policy_name)
        results.append(
            WalkForwardFold(
                fold_number=fold_number,
                training_observations=len(training),
                test_observations=len(test),
                selected_policy=selected.name,
                training_metrics=best,
                test_metrics=evaluate_policy(test, selected),
            )
        )
    return tuple(results)


def promotion_decision(
    folds: tuple[WalkForwardFold, ...],
    *,
    minimum_observations: int = 100,
) -> PromotionDecision:
    observation_count = sum(fold.test_metrics.entered_count for fold in folds)
    positive_folds = sum(
        fold.test_metrics.median_return_percent is not None
        and fold.test_metrics.median_return_percent > 0
        for fold in folds
    )
    positive_fold_percent = (
        positive_folds / len(folds) * 100 if folds else 0.0
    )
    if observation_count < minimum_observations:
        return PromotionDecision(
            status="insufficient_evidence",
            reason="The held-out option sample is below the precommitted minimum.",
            observation_count=observation_count,
            positive_fold_percent=positive_fold_percent,
        )
    if positive_fold_percent < 60:
        return PromotionDecision(
            status="rejected",
            reason="Held-out median returns were not positive in enough chronological folds.",
            observation_count=observation_count,
            positive_fold_percent=positive_fold_percent,
        )
    return PromotionDecision(
        status="eligible_for_shadow",
        reason=(
            "Evidence is strong enough for forward shadow validation, not automatic "
            "production promotion."
        ),
        observation_count=observation_count,
        positive_fold_percent=positive_fold_percent,
    )
