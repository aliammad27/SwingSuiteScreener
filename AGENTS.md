# SwingSuiteScreener Engineering Contract

## Mission

Maintain a deterministic, read-only research screener for Bullish Weekly Participation
v5. The application identifies bullish stock and long-call research candidates. It
never places orders, reads brokerage accounts, manages positions, or presents a score
as a probability.

## Source Of Truth

Strategy behavior is owned by:

1. `config/strategy.yaml`
2. `scanner/strategy_profile.py`
3. deterministic calculations in `scanner/`
4. report, dashboard, notification, Pine, fixture, test, and manual parity

No strategy threshold may be hidden in a workflow, report template, or chart script.

## Validation State

V5 launches with `validation_state: research_default`. Even a technically complete
candidate with trusted SIP, OPRA, and event data is labeled `Ready - Verify` until the
precommitted historical and shadow gates pass. Code must never silently change this
state.

Scores rank evidence. They do not estimate win probability, expected return,
certainty, or option value.

## Strategy Lanes

### Index Weekly

- symbols: SPY and QQQ
- preferred DTE: 10-16
- hard DTE: 7-21
- preferred call delta: 0.60-0.75
- intended hold: 1-4 sessions
- exit or fully requalify at 5 DTE
- spread at or below 3%
- open interest at least 2,000
- volume at least 500
- bid and ask size at least 10
- absolute daily theta at or below 5% of ask

### Leader Weekly

- dynamically qualified liquid leaders
- price at least $20
- 20-session average dollar volume at least $100 million
- preferred DTE: 14-21
- hard DTE: 10-24
- preferred call delta: 0.55-0.70
- intended hold: 1-5 sessions
- exit or fully requalify at 7 DTE
- spread at or below 5%
- open interest at least 1,000
- volume at least 200
- bid and ask size at least 5
- absolute daily theta at or below 6% of ask

Zero through six DTE contracts are excluded. Prefer a nonstandard weekly expiration,
but allow a standard monthly expiration inside the lane window when its liquidity is
materially stronger.

## Selection Ownership

- the daily chart owns trend, leadership, pattern, and structural levels
- a completed 60-minute bar owns timing
- only completed candles count
- new entries are eligible from 10:30 AM through 2:45 PM ET
- the final scheduled hourly scan is management-only
- SPY and QQQ provide market and intraday confirmation
- price must remain above SMA200
- market regime must not be hostile
- daily and hourly evidence must agree
- no unresolved event risk
- no excessive extension
- live contract quality must pass or be explicitly labeled for verification

Controlled pullbacks receive a ranking advantage because they usually provide clearer
underlying invalidation and less volatility inflation than a late breakout.

## Pattern Registry

Production patterns:

1. controlled pullback
2. confirmed breakout
3. bull flag
4. breakout retest
5. flat base
6. VCP / tight base
7. ascending triangle

Context-only atlas patterns:

1. cup with handle
2. double bottom
3. inverse head and shoulders
4. falling wedge
5. rounding base

Every pattern must have deterministic geometry, a trigger, structural invalidation,
shared lifecycle behavior, completed-candle tests, Pine coverage, and manual coverage.
Context-only patterns cannot qualify a production candidate.

Lifecycle defaults:

- ready within 0.30 ATR of the trigger
- maximum confirmed extension of 0.75 ATR
- maximum confirmed age of one daily bar

## Timing Evidence

Completed 60-minute timing uses:

- EMA9 and EMA21
- session VWAP
- RSI
- MACD histogram
- relative volume
- higher-low or reclaim structure
- intraday SPY and QQQ confirmation

The hourly chart provides separate tactical warning and tactical failure levels. It
cannot repair a failed daily thesis.

## Event And Data Trust

- SIP stock data and OPRA option data are required for full trust
- maximum option quote age is two minutes
- event records require a source timestamp no older than 24 hours
- leaders are blocked when earnings fall inside maximum hold plus two trading sessions
- index entries are blocked around FOMC, CPI, and Employment Situation releases until
  the first completed post-event hour
- Massive Benzinga earnings is used when entitled
- Federal Reserve and U.S. BLS calendars are authoritative for macro windows
- unavailable, missing, stale, or unknown event evidence fails closed

## Staged Contract Research

The scanner operates in two stages:

1. Evaluate market, trend, leadership, production pattern, and hourly timing.
2. For technical finalists only, check events, fetch the option chain, rank contracts,
   and re-quote the top three before classification.

The live chain is authoritative. Contract scoring includes DTE, delta, spread, open
interest, volume, depth, theta as a percentage of ask, IV versus realized volatility,
extrinsic value, gamma, quote age, and quote stability.

## Levels And Management Language

Keep these levels separate:

- tactical warning
- tactical failure
- structural invalidation
- nearest confirmed daily pivot
- 2R planning objective

Never label a synthetic objective as resistance. Use a confirmed pivot as the target
only when it offers sufficient room. Otherwise, label the target as a 2R planning
objective and require review of the path through the pivot.

Reports and manuals may describe this educational process:

- use the underlying invalidation
- reassess after two sessions without meaningful progress
- enforce the lane maximum hold
- do not hold through earnings
- exit or fully requalify at the lane DTE boundary
- size for the possibility of full premium loss

Do not prescribe universal premium stops, profit targets, account allocations, or
expected win/loss distributions.

## Historical Research

Historical option research must:

- use point-in-time contracts and quotes
- align entry quotes strictly at or after the completed hourly trigger timestamp
- use minute-sequenced underlying evidence
- enter pessimistically near the ask and exit pessimistically near the bid
- include commissions
- reject stale, missing, crossed, or zero-ask quotes
- treat same-minute trigger and invalidation pessimistically
- use purge and embargo gaps in chronological walk-forward folds
- report overlap-aware concentration and drawdown
- compare with the frozen longer-DTE baseline
- test neighboring-parameter stability and pessimistic-fill resilience

Promotion review requires at least 150 held-out contracts per lane, 40 per promoted
pattern, positive median results in at least 60% of folds, acceptable drawdown and
concentration, baseline improvement, stable neighboring parameters, and pessimistic
fill resilience. A further 45 calendar days and 50 new eligible shadow opportunities
are required. Passing gates permits a documented review; it never auto-promotes.

Underlying proxy research is not option performance.

## Pine Contract

The active Pine v6 suite is:

- `AS_Weekly_Command_1D_v5.pine`
- `AS_Weekly_Timing_1H_v5.pine`
- `AS_Bullish_Pattern_Atlas_1D_v5.pine`
- `AS_Weekly_Screener_v5.pine`
- `AS_Weekly_Underlying_Research_v5.pine`

All scripts use completed bars and confirmed higher-timeframe requests. The screener
must stay within five `request.*` calls and expose its first ten plots as scan columns.
The underlying tester must remain explicitly labeled as a proxy.

## Data And Safety

- Alpaca access is market-data only.
- Never add brokerage account, position, order, exercise, or execution endpoints.
- Never print secrets.
- Fixture output must be labeled simulated and not current market data.
- Preserve stale-data, completed-candle, event, schedule, and notification
  deduplication gates.
- Exchange sessions must come from a maintained exchange calendar.

## Repository Standards

- Python 3.12
- typed dataclasses for domain records
- deterministic pure calculations where practical
- structured parsing for configuration and provider payloads
- configuration values flow through `StrategyProfile`
- generated reports, charts, logs, research databases, secrets, and staging files stay
  untracked
- active repository artifacts are v5 only

Required checks:

```bash
python -m pytest
python -m ruff check scanner tests scripts
python -m mypy scanner
python scripts/check_pine_parity.py
python scripts/release_audit.py
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan intraday --fixture --scenario ready
python -m scanner.run_scan post_close --fixture
```

## Change Discipline

When strategy behavior changes, update together:

1. configuration and typed profile
2. calculations, grading, events, and research assumptions
3. Markdown, JSON, HTML, and notification output
4. Pine constants and chart logic
5. fixtures and tests
6. README, changelog, build plan, and training manual

Do not release while these surfaces disagree.
