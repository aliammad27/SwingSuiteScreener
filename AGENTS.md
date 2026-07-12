# SwingSuiteScreener Engineering Contract

## Mission

Maintain a deterministic, read-only research screener for the Bullish Participation
v3 strategy. The application identifies bullish stock and call-option candidates;
it never places orders, connects to an account, or presents a score as a probability.

## Active Strategy

The source of truth is `config/strategy.yaml` and its typed adapter in
`scanner/strategy_profile.py`.

- bullish only
- controlled pullbacks preferred over breakouts
- 30-60 DTE preferred, 21-75 hard bounds
- 0.45-0.65 call delta preferred, 0.35 hard floor
- 5-15 trading-day planning window
- no earnings-event trades
- no minimum ATR or OTM movement-capability gate
- live option quality required before a setup is called ready

Put modules are retained only for compatibility. Do not expose put commands while
`direction: bullish_only` and `enable_put_scans: false` are active.

## Setup States

Internal enum codes remain stable for stored-state compatibility. User-facing
labels are provided by `Grade.label`:

- S -> Ready
- A+ -> Ready - Verify
- B -> Developing
- Technical Watch -> Verify Contract
- Rejected -> Rejected

Do not add performance claims to a state. Scores rank evidence; they do not estimate
win probability, expected return, or certainty.

## Selection Ownership

The daily chart owns trend and setup selection. The four-hour chart owns timing.
Only completed candles count.

Hard protections include:

- price above SMA 200
- non-hostile market regime
- no unresolved major event risk
- no extension
- daily/four-hour trend agreement
- acceptable option liquidity or an explicit Verify Contract state

Pullback setups receive a ranking advantage because their invalidation is usually
clearer and their option volatility is less likely to be inflated by a breakout.

## Contract Research

The screener proposes a near-the-money research strike. Live chain data remains
authoritative. Verify DTE, delta, spread, volume, open interest, IV, and earnings
before any decision.

Never label a synthetic objective as resistance. Always show the nearest confirmed
daily pivot. Use it as the target when it offers sufficient room; otherwise label the
target as a 2R planning objective and require review of the path through that pivot.

## Management Language

Reports may describe the following educational process rules:

- use the underlying invalidation
- reassess after five sessions without meaningful progress
- do not hold through earnings
- exit or fully re-qualify by 21 DTE
- size for the possibility of full premium loss

Do not prescribe universal premium-return stops, profit targets, account allocations,
or expected win/loss distributions.

## Data And Safety

- Alpaca access is read-only market data.
- Never add brokerage execution or account endpoints.
- Never print secrets.
- Fixture output must be labeled as simulated and not current market data.
- Indicative option data can only produce Verify Contract.
- Preserve stale-data, completed-candle, schedule, and notification-deduplication gates.

## Repository Standards

- Python 3.12
- deterministic pure calculations where practical
- typed dataclasses for domain records
- configuration values must flow through `StrategyProfile`
- tests scale with behavior changes
- generated reports, charts, logs, secrets, and state remain untracked

Required checks:

```bash
python -m pytest
python -m ruff check scanner tests
python -m mypy scanner
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan post_close --fixture
```

## Change Discipline

When strategy behavior changes, update together:

1. `config/strategy.yaml` and `StrategyProfile`
2. calculations and grading
3. reports and Telegram text
4. fixtures and tests
5. README, changelog, and training manual

The code, report, and manual must describe the same system.
