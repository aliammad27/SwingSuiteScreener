# SwingSuiteScreener Engineering Contract

## Mission

Maintain a deterministic, read-only research screener for Bullish Participation v4.
The application identifies bullish stock and long-call candidates. It never places
orders, reads brokerage accounts, manages positions, or presents a score as a
probability.

## Source Of Truth

Strategy behavior is owned by:

1. `config/strategy.yaml`
2. `scanner/strategy_profile.py`
3. deterministic calculations in `scanner/`
4. report, dashboard, Telegram, Pine, fixture, test, and manual parity

No strategy threshold may be hidden in a workflow, report template, or chart script.

## Strategy Doctrine

- bullish calls only
- daily chart owns trend and setup selection
- four-hour chart owns timing
- completed candles only
- controlled pullbacks receive preference when geometry is otherwise comparable
- price must remain above a rising long-term trend boundary
- market regime, leadership, event risk, data freshness, and contract quality are
  independent evidence gates
- index and single-stock candidates use separate DTE, delta, liquidity, hold, and
  requalification lanes
- live option-chain data is authoritative
- unknown earnings data prevents a fully ready state

## Review States

- `Ready`: chart, market, event, risk, and trustworthy live contract evidence pass.
- `Ready - Verify`: chart evidence passes, but a contract or event item needs manual
  confirmation.
- `Verify Contract`: chart evidence passes while the option feed is not trustworthy
  enough for a contract decision.
- `Developing`: bullish geometry exists but one or more chart gates are incomplete.
- `Rejected`: a hard protection failed or the setup does not qualify.

Scores rank evidence. They do not estimate win probability, certainty, or expected
return.

## Pattern Library

The enabled pattern registry in `config/strategy.yaml` is authoritative. Every enabled
pattern must have:

- deterministic geometry
- a trigger
- an underlying invalidation
- a planning objective
- forming, ready, confirmed, failed, and stale behavior
- positive, negative, and incomplete-candle tests
- matching Pine and manual coverage

Adding a visual pattern does not automatically make it production evidence. Research
promotion follows the held-out validation process in
`docs/Bullish_Participation_v4_Build_Plan.md`.

## Contract Research

The screener selects actual call contracts from the available chain. Hard filters
include lane DTE, delta, bid/ask validity, spread, open interest, volume, and quote
freshness.

Historical option research must:

- use contracts and quotes that existed at the signal timestamp
- enter conservatively near the ask and exit conservatively near the bid
- include commissions and explicit slippage assumptions
- treat same-bar trigger and invalidation as invalidation-first
- reject stale, missing, crossed, or zero-ask quotes
- record the possibility of full premium loss
- use chronological walk-forward folds with no future leakage

Underlying returns are not option returns. A parameter remains unvalidated until
point-in-time contract outcomes clear the documented promotion gates.

## Entry And Management Language

Reports and manuals may describe this educational process:

- use the underlying invalidation
- reassess after five sessions without meaningful progress
- do not carry event exposure through an earnings announcement
- fully requalify at the lane DTE boundary
- size for the possibility of full premium loss

Do not prescribe universal premium stops, universal profit targets, account
allocations, or expected win/loss distributions.

## Pine Contract

The active Pine suite is:

- `AS_Command_1D_v4.pine`
- `AS_Momentum_4H_v4.pine`

Both scripts must use Pine v6, completed-bar alerts, confirmed higher-timeframe
requests, and constants checked by `config/pine_parity.json`. Higher-timeframe
requests must use an offset expression with `barmerge.lookahead_on`. Pine is a chart
confirmation and alert surface; Python remains the authoritative multi-symbol
screener.

## Data And Safety

- Alpaca access is market-data only.
- Never add brokerage account, position, order, exercise, or execution endpoints.
- Never print secrets.
- Fixture output must be labeled simulated and not current market data.
- Indicative option data can only produce a contract-verification state.
- Preserve stale-data, completed-candle, event-risk, schedule, and notification
  deduplication gates.
- Exchange sessions must come from a maintained exchange calendar, not a single-year
  hardcoded list.

## Repository Standards

- Python 3.12
- typed dataclasses for domain records
- deterministic pure calculations where practical
- structured parsing for configuration and provider payloads
- configuration values flow through `StrategyProfile`
- generated reports, charts, logs, research databases, secrets, and local document
  staging stay untracked
- active repository artifacts are v4 only

Required checks:

```bash
python -m pytest
python -m ruff check scanner tests scripts
python -m mypy scanner
python scripts/check_pine_parity.py
python scripts/release_audit.py
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan post_close --fixture
```

## Change Discipline

When strategy behavior changes, update together:

1. configuration and typed profile
2. calculations, grading, and research assumptions
3. Markdown, JSON, HTML, and Telegram output
4. Pine constants and chart logic
5. fixtures and tests
6. README, changelog, build plan, and training manual

Do not push a strategy change while these surfaces disagree.
