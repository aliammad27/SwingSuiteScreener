from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scanner.long_call_research import (
    ContractBar,
    FillPolicy,
    LongCallExperiment,
    promotion_decision,
    simulate_long_call,
    walk_forward_evaluate,
)

START = datetime(2025, 1, 2, 21, 0, tzinfo=UTC)


def _policy(name: str = "baseline", maximum_hold: int = 5) -> FillPolicy:
    return FillPolicy(
        name=name,
        maximum_hold_sessions=maximum_hold,
        no_progress_sessions=3,
        requalify_dte=21,
    )


def _experiment(
    identifier: str,
    *,
    start: datetime = START,
    same_bar: bool = False,
    positive: bool = True,
) -> LongCallExperiment:
    bars: list[ContractBar] = []
    for index in range(6):
        high = 101.5 + index
        low = 100.0 + index * 0.4
        if same_bar and index == 0:
            low = 97.0
        bid = 2.00 + (0.35 * index if positive else -0.15 * index)
        bars.append(
            ContractBar(
                timestamp=start + timedelta(days=index),
                underlying_high=high,
                underlying_low=low,
                underlying_close=101.0 + index * (0.8 if positive else -0.2),
                bid=max(bid, 0.10),
                ask=max(bid + 0.20, 0.30),
                dte=45 - index,
            )
        )
    return LongCallExperiment(
        experiment_id=identifier,
        lane="leader_swing",
        pattern_type="controlled_pullback",
        market_regime="Supportive",
        signal_timestamp=start,
        trigger=101.0,
        invalidation=98.0,
        objective=105.0,
        confirmed_at_signal=False,
        bars=tuple(bars),
    )


def test_long_call_simulator_uses_conservative_bid_ask_fills() -> None:
    outcome = simulate_long_call(_experiment("positive"), _policy())
    assert outcome.entered is True
    assert outcome.entry_price == 2.20
    assert outcome.exit_price is not None
    assert outcome.exit_price < 3.80
    assert outcome.return_percent is not None and outcome.return_percent > 0
    assert outcome.maximum_loss_per_contract is not None
    assert outcome.exit_reason == "planning_objective"


def test_same_bar_trigger_and_invalidation_is_pessimistic() -> None:
    outcome = simulate_long_call(
        _experiment("ambiguous", same_bar=True),
        _policy(),
    )
    assert outcome.entered is True
    assert outcome.exit_reason == "same_bar_ambiguous"
    assert outcome.return_percent is not None and outcome.return_percent < 0


def test_stale_quotes_do_not_create_an_entry() -> None:
    experiment = _experiment("stale")
    stale = tuple(
        ContractBar(
            timestamp=bar.timestamp,
            underlying_high=bar.underlying_high,
            underlying_low=bar.underlying_low,
            underlying_close=bar.underlying_close,
            bid=bar.bid,
            ask=bar.ask,
            dte=bar.dte,
            quote_age_minutes=90,
        )
        for bar in experiment.bars
    )
    outcome = simulate_long_call(
        LongCallExperiment(
            experiment_id=experiment.experiment_id,
            lane=experiment.lane,
            pattern_type=experiment.pattern_type,
            market_regime=experiment.market_regime,
            signal_timestamp=experiment.signal_timestamp,
            trigger=experiment.trigger,
            invalidation=experiment.invalidation,
            objective=experiment.objective,
            confirmed_at_signal=experiment.confirmed_at_signal,
            bars=stale,
        ),
        _policy(),
    )
    assert outcome.entered is False
    assert outcome.exit_reason == "no_fresh_quote"


def test_walk_forward_is_chronological_and_never_auto_promotes() -> None:
    experiments = tuple(
        _experiment(
            f"signal-{index}",
            start=START + timedelta(days=index * 7),
            positive=index % 4 != 0,
        )
        for index in range(24)
    )
    folds = walk_forward_evaluate(
        experiments,
        (
            _policy("short", maximum_hold=3),
            _policy("standard", maximum_hold=5),
        ),
        folds=4,
    )
    assert len(folds) == 3
    assert all(fold.training_observations > 0 for fold in folds)
    decision = promotion_decision(folds)
    assert decision.status == "insufficient_evidence"
    assert decision.observation_count < 100
