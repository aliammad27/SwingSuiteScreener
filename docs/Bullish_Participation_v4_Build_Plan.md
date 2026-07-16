# Bullish Participation v4 Build Plan

## Objective

Build a deterministic, read-only platform that finds high-quality bullish stock
setups, evaluates long-call contract quality, explains every decision, and improves
only through point-in-time, after-cost, held-out evidence.

The objective is not the highest backtest return or the highest hit rate. The
objective is a robust edge that survives spread costs, regime changes, neighboring
parameter choices, stale data, event risk, and forward shadow use.

## Non-Negotiable Boundaries

1. No brokerage account access or trade execution.
2. No score is described as a probability.
3. Only completed candles qualify a setup.
4. Unknown event data prevents a fully ready state.
5. Indicative option data prevents a fully ready contract state.
6. Underlying returns are never substituted for option returns.
7. Research never rewrites production configuration automatically.
8. Same-bar trigger and invalidation is resolved pessimistically.
9. Every promoted feature must improve held-out, after-cost evidence.
10. The active repository, reports, Pine scripts, and manual describe one v4 system.

## Product Surfaces

### Python Screener

The Python application is the authoritative multi-symbol scanner. It owns:

- universe traversal
- completed-bar data validation
- market regime and breadth
- daily trend and leadership
- bullish pattern geometry and lifecycle
- daily and four-hour momentum
- event-risk gating
- actual call-chain filtering and ranking
- review-state classification
- research ledger and replay

### HTML Dashboard

Each scan generates a portable `latest.html` with:

- regime, score, breadth, and freshness summary
- state, lane, and text filters
- dense candidate comparison
- contract quality and liquidity
- trigger, support, invalidation, resistance, and objective
- evidence component bars
- event status and pending checks
- rejected diagnostics
- mobile and print layouts

The first release uses static HTML because it has no server, authentication,
deployment, or database attack surface. A hosted application is only justified when
multi-user history, saved views, or collaborative review becomes a real requirement.

### Telegram

Telegram remains the concise delivery surface:

- scan completion
- state counts
- market context
- top candidate summaries
- contract verification posture
- full-premium-loss reminder
- notification deduplication

### Pine V6

The Pine suite contains two focused overlays:

1. `AS_Command_1D_v4.pine`
2. `AS_Momentum_4H_v4.pine`

The daily script contains the complete bullish pattern library. The four-hour script
contains timing and warning logic. This division keeps each script inside platform
limits and matches daily selection versus four-hour timing ownership.

### Training Manual

The canonical text is versioned in
`docs/Bullish_Participation_v4_Training_Manual.md`. The visually verified import
artifact is versioned in
`docs/Ali_Swing_Suite_Bullish_Participation_v4_Training_Manual.docx`. Native Google
Docs publication uses that DOCX and includes title sanitization, page rendering,
connector import, readback, and exported-PDF review.

## Architecture

```text
Configuration
    |
    v
Provider adapters -> Data quality -> Market context
    |                                  |
    +-> Daily/weekly evidence ----------+
    +-> Four-hour momentum -------------+-> Candidate classification
    +-> Event calendar -----------------+
    +-> Call chain ---------------------+
                                           |
                  +------------------------+-----------------------+
                  |                        |                       |
                  v                        v                       v
             MD / JSON                HTML dashboard          Telegram
                  |
                  v
           Research ledger -> Replay -> Long-call simulation -> Walk-forward review
```

## Strategy Design

### Index Core Lane

- symbols: SPY and QQQ
- preferred DTE: 45-90
- hard DTE: 30-120
- preferred delta: 0.60-0.75
- hard delta: 0.50-0.85
- intended hold: 10-30 sessions
- requalify: 30 DTE
- maximum spread: 5%
- minimum open interest: 1,000
- minimum daily contract volume: 500

The purpose is slower participation with higher delta and more time. The lane is not
graded on single-stock leadership.

### Leader Swing Lane

- curated liquid sector leaders
- preferred DTE: 30-60
- hard DTE: 21-75
- preferred delta: 0.45-0.65
- hard delta: 0.35-0.75
- intended hold: 5-15 sessions
- requalify: 21 DTE
- maximum spread: 8%
- minimum open interest: 500
- minimum daily contract volume: 100

The purpose is directional participation in a leading stock while maintaining
enough time and liquidity for the thesis to work.

## Evidence Pipeline

### Market Context

Initial components:

- SPY daily trend
- QQQ daily trend
- SPY and QQQ weekly alignment
- percentage of leaders above SMA50
- percentage of leaders above EMA21

Candidate features such as volatility indexes, advance/decline data, sector breadth,
and credit proxies remain research-only until they improve held-out results without
making the model fragile.

### Trend

Initial evidence:

- close above EMA21
- EMA21 above SMA50
- close above SMA50
- SMA50 above SMA200
- close above SMA200
- rising SMA200
- weekly close above weekly EMA21
- confirmed structure and pivots
- rolling anchored-volume-weighted support
- extension control

Price below SMA200 and excessive extension are hard failures.

### Leadership

Leader Swing uses:

- stock versus sector benchmark
- sector benchmark versus SPY
- relative line versus EMA21
- five-session relative direction
- approximately three-month stock versus peer return

Leadership is omitted for Index Core rather than filled with a synthetic perfect
score.

### Pattern Library

Production geometry:

1. controlled pullback
2. confirmed breakout
3. bull flag
4. flat base
5. ascending triangle
6. volatility contraction / tight base
7. cup with handle
8. breakout retest
9. double bottom
10. inverse head and shoulders
11. falling wedge
12. rounding base

Every pattern produces:

- quality score
- trigger
- underlying invalidation
- planning objective
- geometry notes
- age
- lifecycle state

Pattern count is not a goal. A pattern remains enabled only if its deterministic
tests and research evidence justify the complexity.

### Momentum

Daily momentum establishes the higher-timeframe filter. Four-hour momentum owns
timing:

- RSI level and direction
- MACD versus signal
- MACD versus zero
- histogram direction
- confirmed daily alignment
- positive divergence support
- negative divergence warning
- reaction trigger, support, and warning levels

### Event Risk

The runtime fails closed:

- confirmed earnings inside the blackout window: rejected
- unknown earnings date: at most Ready - Verify
- stale event check: requires verification

A production event adapter must record source, checked timestamp, earnings date, and
status. A manually maintained file is acceptable as a fallback but not as the
long-term production source for a large universe.

### Contract Selection

Hard filters:

- expiration inside lane hard range
- delta inside lane hard range
- positive, uncrossed bid/ask
- spread inside lane maximum
- open interest minimum
- volume minimum
- quote freshness

Ranking factors:

- distance from preferred delta center
- spread quality
- distance from preferred DTE center
- open interest
- volume
- freshness

IV, skew, term structure, and IV percentile remain descriptive until point-in-time
research proves they improve selection. They must not become hidden hard gates.

## Data Plan

### Live Runtime

- Alpaca stock and option market data
- OPRA subscription for trustworthy live option decisions
- configured event provider with fail-closed behavior
- maintained NYSE exchange calendar

### Historical Research

Recommended option evidence:

- historical U.S. option quotes from Massive
- trades or minute aggregates for execution-path diagnostics
- reference contract data and corporate actions
- Alpaca as a secondary comparison from its available history

Required fields:

- contract symbol
- expiration and strike
- point-in-time bid, ask, sizes, and timestamp
- underlying OHLC
- DTE
- open interest and volume when available
- Greeks and implied volatility only when available at that timestamp
- earnings status known at that timestamp

### Point-In-Time Universe

A serious historical study cannot use only today's symbol list. The research dataset
must preserve:

- symbol membership by date
- delistings and ticker changes
- split and dividend adjustments
- sector benchmark mapping by date
- data-source revisions

If point-in-time membership is unavailable, results are labeled with survivorship
risk and cannot clear the strongest validation gate.

## Long-Call Simulation

### Entry

- select only contracts available at the signal timestamp
- apply the lane's hard filters
- use a predeclared contract-ranking policy
- fill at the ask by default
- include commission
- reject stale or crossed quotes

### Exit

Research policies may compare:

- underlying invalidation
- planning objective
- maximum hold
- five-session no-progress review
- event-risk discovery
- lane DTE requalification

Exit fills default to the bid and include commission. A quote below zero, crossed
market, or stale quote is invalid data rather than an opportunity to interpolate a
favorable price.

### Intrabar Ambiguity

When a daily bar reaches both trigger and invalidation and intraday sequencing is not
available, the experiment records invalidation first. Higher-resolution evidence may
resolve the order only when it is complete and point in time.

### Metrics

Primary:

- median net contract return
- mean net contract return
- maximum drawdown
- worst observation
- maximum adverse excursion
- maximum favorable excursion
- entered-contract count
- opportunity count

Secondary and descriptive:

- positive-return frequency
- outcome by lane
- outcome by pattern
- outcome by regime
- outcome by spread bucket
- outcome by DTE and delta bucket

Positive-return frequency is never presented as a probability of success.

## Optimization Protocol

### Frozen Baselines

Every experiment compares against:

1. current v4 settings
2. a fixed near-the-money call policy
3. the underlying security over the same window
4. cash / no signal

The baseline configuration hash is frozen before searching.

### Search Space

Search only parameters with a causal rationale:

- trend and evidence thresholds
- pattern distances and age
- lane DTE and delta bands
- liquidity constraints
- maximum hold
- no-progress review timing
- objective-exit behavior

Avoid searching arbitrary indicator combinations. Every extra degree of freedom
increases multiple-testing risk.

### Walk-Forward Design

- chronological folds
- training data strictly before test data
- purge overlapping holding periods at fold boundaries
- embargo after training to prevent path overlap
- separate Index Core and Leader Swing analysis
- retain regime and pattern subgroup reports
- choose parameters on training data only
- report every held-out fold, including weak folds

### Promotion Gates

A change cannot enter shadow validation unless:

- at least 100 entered held-out contracts exist for the lane
- any promoted pattern/regime subgroup has at least 30 entered contracts
- held-out median and mean net returns exceed the frozen baseline
- held-out median is positive in at least 60% of chronological folds
- maximum drawdown is no worse than the baseline
- no single ticker contributes more than 20% of net outcome
- neighboring parameter values produce similar conclusions
- missing-data and pessimistic-fill sensitivity do not reverse the conclusion
- the change has a written causal explanation

Passing these gates means **eligible for shadow**, not production-ready.

### Forward Shadow Gate

Before production:

- run the selected policy unchanged for at least 30 calendar days
- capture at least 30 new eligible opportunities when market activity permits
- compare predicted contract selection with real timestamped quotes
- record event, data, and operational failures
- require manual approval and a versioned configuration change

If the sample is not available, the period extends. The evidence bar is not reduced.

## Testing Plan

### Unit Tests

- every threshold boundary
- every pattern positive and negative geometry
- incomplete-candle exclusion
- trigger, invalidation, and objective ordering
- DTE and delta hard bounds
- spread, volume, open interest, and quote-age bounds
- event blackout boundaries
- review-state transitions

### Data-Quality Tests

- missing bars
- zero volume
- stale quotes
- crossed quotes
- duplicate contracts
- pagination
- splits and ticker changes
- half days and holidays
- daylight-saving transitions
- provider timeouts and rate limits

### Research Tests

- no future bars in signal generation
- no future contract selection
- same-bar pessimism
- bid/ask fills and commission
- chronological folds
- no automatic production promotion
- config-hash reproducibility
- idempotent ledger writes

### UI Tests

- desktop and mobile screenshots
- no clipped or overlapping text
- all states
- zero-result state
- long symbol and pattern labels
- search and filters
- rejected diagnostics
- print layout

### Pine Tests

- Pine v6 declaration
- no inactive strategy code
- configuration parity
- confirmed higher-timeframe requests
- request count inside platform limits
- all enabled pattern names
- completed-bar alert conditions
- TradingView Pine Editor compilation
- chart checks on daily and four-hour timeframes

## Release Process

1. Freeze intended scope and inspect the complete diff.
2. Remove generated reports, local databases, document staging, and secrets.
3. Run all repository quality gates.
4. Generate fixture reports and inspect the HTML dashboard at desktop and mobile
   widths.
5. Compile both Pine scripts in TradingView and verify plots and alerts.
6. Render and inspect every page of the manual DOCX.
7. Import the manual as a native Google Doc and verify readback and exported PDF.
8. Run the v4 release audit.
9. Commit the complete release.
10. Push the tested commit directly to `origin/main` without force.
11. Monitor the main-branch CI run.
12. Tag `v4.0.0` only after CI passes.

## Definition Of Done

Bullish Participation v4 is complete when:

- active repository artifacts are v4 only
- all enabled patterns are implemented, tested, documented, and represented in Pine
- Python, Markdown, JSON, HTML, Telegram, and Pine agree on states and thresholds
- the dashboard passes visual review
- the manual passes DOCX and Google Docs review
- fixture and quality gates pass
- main-branch CI passes
- any performance language is supported by point-in-time option evidence
- unvalidated parameters are explicitly labeled research defaults
