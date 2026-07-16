# Ali Swing Suite

## Bullish Participation v4 Training Manual

**Purpose:** A complete operating guide for the read-only Bullish Participation v4
stock and long-call research system.

**Scope:** U.S. listed stocks and index ETFs, daily setup selection, four-hour timing,
and long-call contract research.

**Important:** This system is educational research software. It does not place
orders, access brokerage accounts, or guarantee an outcome. A long call can lose the
entire premium paid.

---

## 1. The Operating Idea

Bullish Participation v4 looks for a specific combination:

1. a supportive or at least non-hostile market
2. a stock or index in a healthy long-term uptrend
3. leadership or index strength appropriate to its lane
4. recognizable bullish geometry with a clear trigger and invalidation
5. four-hour momentum that agrees with the daily thesis
6. no unresolved earnings-event conflict
7. a liquid call contract that fits the lane

The system does not reward activity. No setup is a valid result. Cash is a valid
state.

### 1.1 Why The Underlying Comes First

A call option is a derivative of the underlying security. The thesis is therefore
defined on the stock or ETF chart:

- the setup is selected on the daily chart
- the entry trigger is an underlying price
- the invalidation is an underlying price
- the objective is an underlying planning level
- the option contract is the participation vehicle

Premium movement can be distorted by spread, implied volatility, time decay, and
quote quality. The underlying chart remains the primary thesis surface.

### 1.2 What A Score Means

A score is a structured evidence rank. It answers questions such as:

- Does the trend meet the configured conditions?
- Is the stock leading its peer?
- Is the pattern geometry clean?
- Is momentum aligned?
- Is the market supportive?
- Is the contract liquid and fresh?
- Is the risk geometry acceptable?

A score does **not** mean:

- probability of profit
- expected return
- certainty
- permission to place an order

---

## 2. System Architecture

### 2.1 Daily Chart Ownership

The daily chart owns:

- trend
- structure
- leadership
- pattern selection
- trigger
- support
- invalidation
- resistance
- planning objective

Only a completed daily candle can change daily qualification.

### 2.2 Four-Hour Chart Ownership

The four-hour chart owns:

- RSI and MACD timing
- momentum confirmation
- reaction trigger
- short-term support
- momentum warning level
- divergence warnings

The four-hour chart cannot rescue a weak daily chart. It only times a daily thesis
that already has sufficient evidence.

### 2.3 Contract Ownership

The option chain owns:

- expiration
- strike
- delta
- bid and ask
- spread
- volume
- open interest
- implied volatility
- Greeks
- quote timestamp

The Pine scripts cannot validate a live contract. The Python screener can rank the
chain it receives, but the live broker chain remains authoritative.

---

## 3. Strategy Lanes

### 3.1 Index Core

| Field | Rule |
|---|---|
| Symbols | SPY and QQQ |
| Preferred DTE | 45-90 |
| Hard DTE | 30-120 |
| Preferred delta | 0.60-0.75 |
| Hard delta | 0.50-0.85 |
| Intended thesis window | 10-30 sessions |
| Requalification boundary | 30 DTE |
| Maximum spread | 5% |
| Minimum open interest | 1,000 |
| Minimum daily volume | 500 |

Index Core uses more time and higher delta because the intended move is typically
slower and the underlying is diversified. A higher-delta contract usually tracks the
underlying more directly, but it also costs more premium.

Index Core does not receive a synthetic leadership score. The index itself is the
market vehicle.

### 3.2 Leader Swing

| Field | Rule |
|---|---|
| Symbols | Curated liquid sector leaders |
| Preferred DTE | 30-60 |
| Hard DTE | 21-75 |
| Preferred delta | 0.45-0.65 |
| Hard delta | 0.35-0.75 |
| Intended thesis window | 5-15 sessions |
| Requalification boundary | 21 DTE |
| Maximum spread | 8% |
| Minimum open interest | 500 |
| Minimum daily volume | 100 |

Leader Swing requires stock-versus-sector and sector-versus-market evidence. The
contract has less time than Index Core because the setup is expected to resolve more
quickly, but it still avoids very short-dated exposure.

---

## 4. Review States

### Ready

All required chart, market, event, risk, and trustworthy live contract evidence
passes.

Manual review is still required. Ready is not an order signal.

### Ready - Verify

Chart evidence passes, but at least one item requires confirmation, usually:

- contract score below the full-ready threshold but above the verification threshold
- event calendar unknown
- another evidence item that remains acceptable only after review

### Verify Contract

The chart setup passes, but the option feed is indicative or otherwise not
authoritative enough for a contract decision.

### Developing

Bullish geometry exists, but one or more chart requirements are incomplete:

- trend score below ready threshold
- setup still forming
- momentum not confirmed
- market below ready threshold
- leadership incomplete

### Rejected

A hard protection failed or the structure does not qualify. Common reasons:

- price below SMA200
- excessive extension
- hostile market
- earnings inside blackout
- failed or stale pattern
- no eligible call contract

---

## 5. Market Context

The market score combines:

- SPY daily trend
- QQQ daily trend
- SPY and QQQ weekly alignment
- percentage of leaders above SMA50
- percentage of leaders above EMA21

### Supportive

The broad environment is aligned with bullish participation. This does not remove
single-stock risk.

### Mixed

Some evidence is constructive and some is weak. Developing setups may remain useful,
but the system does not treat the environment as fully supportive.

### Hostile

Broad trend and participation are too weak. New bullish candidates are rejected.

### Practical Reading

Breadth matters because an index can remain elevated while fewer stocks participate.
Strong breadth supports follow-through. Weak breadth increases the chance that a
single-stock breakout fails even when the headline index looks acceptable.

---

## 6. Trend Evidence

The trend score uses:

- close above EMA21
- EMA21 above SMA50
- close above SMA50
- SMA50 above SMA200
- close above SMA200
- rising SMA200
- weekly close above weekly EMA21

### Hard Trend Protections

**Below SMA200:** The candidate is rejected. The system is built for bullish
participation in established long-term trends.

**Excessively extended:** The candidate is rejected when price is too far above the
EMA21 in ATR terms. Extension creates poor invalidation geometry and can coincide
with expensive implied volatility.

### Structure

Confirmed pivots classify structure as:

- bullish
- improving
- mixed
- weak

Pivots require bars on both sides. This confirmation delay is intentional because it
prevents future-looking structure.

### Anchored Volume-Weighted Support

The system uses a recent rolling volume-weighted price reference alongside EMA21,
SMA50, and confirmed pivots. It is a support input, not an infallible line.

---

## 7. Leadership

Leader Swing compares:

1. the stock against its sector or industry benchmark
2. the peer benchmark against SPY
3. the stock's medium-term return against the peer

A stock can rise while still lagging its sector. Leadership evidence asks whether
capital is favoring the stock rather than merely lifting the entire group.

### Strong Leadership

- stock/peer ratio above its EMA21
- stock/peer ratio rising over five sessions
- peer/SPY ratio constructive
- stock outperforming peer over the medium-term window

### Weak Leadership

- stock/peer ratio below trend
- relative line falling
- sector lagging the market
- stock return behind peer return

Leadership is evidence, not a guarantee. It improves prioritization.

---

## 8. Pattern Lifecycle

Every enabled pattern uses the same lifecycle.

### Forming

Geometry exists but price is not near enough to the trigger.

### Ready

Price is within the configured ATR distance of the trigger and remains above
invalidation.

### Confirmed

Price has closed through the trigger recently and is not excessively extended.

### Failed

Price closed below the underlying invalidation.

### Stale

The trigger was confirmed too long ago or price moved too far beyond it. The system
does not chase.

---

## 9. Bullish Pattern Library

### 9.1 Controlled Pullback

**Idea:** An established uptrend pulls back toward EMA21, volume-weighted support, or
a confirmed pivot and then holds.

**Valid geometry:**

- healthy trend
- pullback reaches support without breaking it
- closing recovery or constructive candle
- manageable distance from trigger to invalidation
- room to resistance or a planning objective

**Trigger:** High of the recent recovery candles.

**Invalidation:** Below the support zone with an ATR buffer.

**Failure:** Close below invalidation.

**Option implication:** Often preferred because the move has not already expanded and
implied volatility may be less inflated than after a breakout.

### 9.2 Confirmed Breakout

**Idea:** Price closes above established resistance with supportive volume.

**Valid geometry:**

- trend aligned
- resistance defined from completed bars
- closing break, not an intraday wick alone
- volume expansion
- not excessively extended

**Trigger:** Resistance level.

**Invalidation:** EMA21 or a buffered level below resistance.

**Failure:** Close back through invalidation or immediate loss of structure.

**Option implication:** Confirmed momentum can be strong, but spread and implied
volatility require extra attention.

### 9.3 Bull Flag

**Idea:** A strong impulse is followed by a controlled, lower-volume retracement.

**Valid geometry:**

- impulse of meaningful ATR size
- retracement generally limited to half the impulse
- declining or sideways flag
- lower flag volume than pole volume
- trend remains intact

**Trigger:** Highest price in the flag.

**Invalidation:** Lowest price in the flag.

**Failure:** Deep retracement or loss of flag low.

### 9.4 Flat Base

**Idea:** Price consolidates tightly near highs while volume contracts.

**Valid geometry:**

- shallow multiweek depth
- limited volatility
- price holds above major averages
- declining volume
- price near the upper boundary

**Trigger:** Upper boundary of the base.

**Invalidation:** Base low.

**Failure:** Expansion below the base.

### 9.5 Ascending Triangle

**Idea:** Repeated resistance is met by rising confirmed lows.

**Valid geometry:**

- flat resistance band
- at least two rising pivot lows
- narrowing distance between support and resistance
- price near the top

**Trigger:** Resistance band.

**Invalidation:** Latest rising pivot low.

**Failure:** Loss of the rising-low sequence.

### 9.6 Volatility Contraction / Tight Base

**Idea:** Price ranges contract in stages while volume declines near the upper part of
the larger range.

**Valid geometry:**

- three progressively smaller ranges
- late range materially tighter than early range
- volume contraction
- price remains near highs

**Trigger:** High of the final contraction.

**Invalidation:** Low of the final contraction.

**Failure:** Range expansion below the final contraction.

### 9.7 Cup With Handle

**Idea:** A rounded base returns to the prior rim and forms a shallow handle.

**Valid geometry:**

- rim prices reasonably matched
- cup depth neither trivial nor structurally destructive
- handle remains in the upper half of the cup
- handle depth remains shallow
- handle volume contracts

**Trigger:** Right rim.

**Invalidation:** Handle low.

**Failure:** Handle breaks deeply into the cup.

### 9.8 Breakout Retest

**Idea:** Price breaks resistance on volume, returns to test it, and closes back above
the old resistance.

**Valid geometry:**

- prior closing breakout
- supportive breakout volume
- retest within a limited number of bars
- resistance converts to support
- close remains above the retest level

**Trigger:** Reclaimed former resistance.

**Invalidation:** Retest low.

**Failure:** Close below the retest low.

### 9.9 Double Bottom

**Idea:** Two confirmed lows form near the same price with a recovery through the
intervening neckline.

**Valid geometry:**

- lows separated by enough bars to be distinct
- lows within a volatility-adjusted tolerance
- meaningful depth to the neckline
- second low does not show materially worse structure
- price recovers toward the neckline

**Trigger:** Neckline.

**Invalidation:** Below the lower bottom with an ATR buffer.

**Failure:** Decisive break below the bottoms.

### 9.10 Inverse Head And Shoulders

**Idea:** A lower head forms between two higher shoulders, followed by a recovery
toward the neckline.

**Valid geometry:**

- three confirmed pivot lows
- head below both shoulders
- shoulders reasonably matched
- neckline not excessively uneven
- price returns toward the neckline

**Trigger:** Neckline.

**Invalidation:** Below the head with an ATR buffer.

**Failure:** Loss of the head low.

### 9.11 Falling Wedge

**Idea:** Price declines inside converging boundaries and recovers toward the upper
boundary.

**Valid geometry:**

- both boundaries slope down
- upper boundary falls faster than lower boundary
- range width contracts
- price returns toward the upper boundary
- larger trend remains acceptable

**Trigger:** Upper wedge boundary.

**Invalidation:** Recent wedge low.

**Failure:** New low with renewed range expansion.

### 9.12 Rounding Base

**Idea:** A gradual decline transitions into a gradual recovery with similar left and
right rim prices.

**Valid geometry:**

- multiweek curvature
- moderate depth
- left side declining
- right side rising
- rim prices reasonably matched
- price near the right rim

**Trigger:** Right rim.

**Invalidation:** Base low.

**Failure:** Recovery rolls over and loses the right-side structure.

---

## 10. Four-Hour Momentum

The four-hour score uses:

- RSI zone
- RSI direction
- MACD versus signal
- MACD versus zero
- histogram direction
- daily filter
- confirmed divergence evidence

### Constructive State

- RSI at or above 50
- MACD above signal
- histogram rising
- confirmed daily filter

### Extended State

Very high RSI can remain bullish, but the system caps the score because a late entry
can have poor geometry.

### Warning State

- RSI below 50
- MACD below signal
- negative divergence
- loss of warning level

Warnings do not predict a reversal. They identify evidence that conflicts with a new
long-call entry or requires reassessment of an existing thesis.

---

## 11. Contract Selection

### 11.1 DTE

More time generally means:

- more premium
- slower theta impact
- more time for the thesis to work

Less time generally means:

- lower premium
- faster time decay
- greater sensitivity to timing error

The lane ranges prevent the screener from selecting contracts that are too short or
unnecessarily far dated for the intended thesis window.

### 11.2 Delta

Delta is the approximate option-price sensitivity to a one-dollar underlying move,
holding other factors constant.

Higher delta:

- tracks the underlying more directly
- usually costs more premium
- often has less leverage per premium dollar

Lower delta:

- costs less
- needs more directional movement
- can be more sensitive to volatility and time

The system treats delta as a range, not a single magical number.

### 11.3 Spread

Spread cost can erase a chart edge. The screener measures:

```text
(ask - bid) / midpoint
```

A narrow spread improves entry and exit flexibility. A zero bid, crossed quote, or
stale quote is not acceptable.

### 11.4 Open Interest And Volume

Open interest indicates outstanding contracts. Daily volume indicates current
trading activity. Neither alone guarantees liquidity, so they are combined with
spread and quote freshness.

### 11.5 Implied Volatility

Implied volatility affects premium. High IV can make a call expensive even when the
chart is attractive. The dashboard shows IV and realized-volatility context when
available, but IV is not a hidden universal rejection rule.

### 11.6 Greeks

- **Delta:** directional sensitivity.
- **Gamma:** rate of change in delta.
- **Theta:** modeled time-decay sensitivity.
- **Vega:** modeled implied-volatility sensitivity.

Greeks are model outputs, not guarantees. They change with price, time, and implied
volatility.

---

## 12. Event And Data Risk

### Earnings

The system does not qualify a new trade through an earnings announcement.

- earnings inside blackout: rejected
- earnings unknown: verification state
- earnings clear: event gate may pass

### Data Freshness

Check:

- market-data timestamp
- quote timestamp
- completed-candle flag
- option feed
- event checked timestamp

Stale data is not made safe by a strong chart score.

### Feed Posture

Alpaca documents two option data postures:

- **Indicative:** derived pricing and delayed derivative trades
- **OPRA:** consolidated market quotes for subscribed users

The screener therefore requires OPRA for a fully trustworthy contract state.

---

## 13. Reading The HTML Dashboard

### Top Bar

Confirms:

- strategy name
- scan type
- generated timestamp
- market-data timestamp
- fixture label when simulated

### Market Band

Shows:

- regime
- market score
- breadth above SMA50
- breadth above EMA21
- evaluated symbols
- ready and verification counts

### Candidate Table

Use it for comparison:

- symbol and lane
- review state
- selected pattern
- trend, leadership, and momentum
- selected contract
- trigger
- invalidation
- objective

Use state segments, search, and lane filtering to reduce the list.

### Candidate Detail

Review in this order:

1. state and lane
2. invalidation-to-trigger geometry
3. evidence bars
4. pattern notes
5. contract and spread
6. event status
7. pending reason codes

### Rejected Diagnostics

Rejected records are useful. They show whether the problem was data quality, hard
protection, contract quality, or incomplete evidence.

---

## 14. Using The Pine Scripts

### Daily Command

1. Open a daily chart.
2. Add `AS_Command_1D_v4.pine`.
3. Set the peer benchmark when reviewing a single stock.
4. Confirm moving averages and selected pattern.
5. Read trigger, invalidation, and objective.
6. Check trend, leadership, setup, and market-proxy rows.
7. Treat `Ready - Verify` as a chart-review state, not a contract approval.

### Four-Hour Momentum

1. Open the same symbol on the four-hour timeframe.
2. Add `AS_Momentum_4H_v4.pine`.
3. Confirm the daily filter passes.
4. Review RSI, MACD histogram, trigger, support, and warning.
5. Note positive or negative divergence markers.
6. Require the completed four-hour candle.

### Alerts

The scripts expose alert conditions. TradingView does not create a running alert from
code alone. Create the alert in the TradingView interface and choose once-per-bar
close behavior.

### Non-Repainting Rule

Higher-timeframe requests use the prior confirmed higher-timeframe value with
`barmerge.lookahead_on`. The offset and lookahead setting work together. Removing the
offset can leak future values on historical bars.

---

## 15. Daily Operating Workflow

### Post Close

1. Confirm the market session completed.
2. Run the post-close scan.
3. Verify timestamp and feed posture.
4. Review market regime and breadth.
5. Review Ready first, then verification states, then Developing.
6. Read rejected diagnostics for data or event problems.
7. Compare daily Pine geometry with the Python report.
8. Record the candidate and reason codes in the research journal.

### Premarket

1. Recheck event status.
2. Recheck option quote freshness when available.
3. Confirm no material gap invalidates the daily geometry.
4. Do not convert an indicative contract into a fully ready state.
5. Reassess only; the daily setup still belongs to the completed daily chart.

### Four-Hour Refresh

1. Confirm the four-hour candle completed.
2. Check daily filter.
3. Check RSI and MACD state.
4. Check trigger, support, and warning.
5. Note any state change.
6. Keep the underlying invalidation authoritative.

### Weekly Radar

1. Review market and sector participation.
2. Look for forming multiweek bases.
3. Separate early research candidates from actionable states.
4. Update the next week's event calendar.

---

## 16. Entry And Management Process

### Before Any Decision

- market not hostile
- daily trend passes
- pattern ready or recently confirmed
- four-hour momentum aligned
- event status clear or explicitly verified
- contract inside lane bounds
- spread and liquidity acceptable
- live quote fresh
- underlying invalidation clear
- path to objective reviewed

### Underlying Invalidation

The invalidation defines where the chart thesis is wrong. It is not derived from a
fixed option-premium percentage.

### Five-Session Reassessment

After five sessions without meaningful progress:

- check whether structure still holds
- check whether momentum deteriorated
- check whether event risk changed
- check remaining DTE and spread
- decide whether the thesis still deserves time

This is a reassessment rule, not an automatic universal exit.

### DTE Requalification

At the lane boundary:

- Index Core: 30 DTE
- Leader Swing: 21 DTE

Fully requalify:

- trend
- pattern
- momentum
- event
- contract
- remaining thesis window

Do not carry a contract merely because it was once qualified.

### Full Premium Loss

Long-call sizing must assume the premium can be lost. This manual does not prescribe
an account allocation or a universal number of contracts.

---

## 17. Research And Optimization

### Evidence Levels

**Exploratory:** Too few observations for reliance.

**Provisional:** Enough observations to inspect, not enough for production claims.

**Validated:** The defined sample threshold is met, but causal quality, held-out
performance, concentration, and robustness still require review.

### Underlying Replay

Sequential replay proves that each signal was generated from a historical prefix.
It is useful for:

- look-ahead testing
- pattern frequency
- trigger and invalidation order
- underlying MFE and MAE

It does not prove option performance.

### Long-Call Simulation

The contract simulator requires:

- point-in-time contract
- point-in-time bid and ask
- conservative ask entry
- conservative bid exit
- commission
- stale-quote rejection
- same-bar pessimism
- event and DTE rules

### Walk-Forward Review

Parameters are selected on earlier data and tested on later data. Every held-out fold
is reported. Weak periods are not hidden.

Research can make a setting eligible for shadow validation. It cannot silently
change `config/strategy.yaml`.

---

## 18. Research Journal Template

Record:

| Field | Entry |
|---|---|
| Timestamp | |
| Symbol | |
| Lane | |
| Market regime | |
| Pattern and state | |
| Trend / leadership / setup / momentum | |
| Trigger | |
| Invalidation | |
| Resistance | |
| Objective and basis | |
| Earnings date and source | |
| Contract symbol | |
| DTE / delta | |
| Bid / ask / spread | |
| OI / volume | |
| IV and Greeks | |
| Feed and quote timestamp | |
| Pending reason codes | |
| Five-session review | |
| Final observation | |

Do not record a fixture as live market evidence.

---

## 19. Checklists

### Candidate Checklist

- [ ] Completed daily candle
- [ ] Market not hostile
- [ ] Price above SMA200
- [ ] Not extended
- [ ] Lane identified
- [ ] Leadership passes when required
- [ ] Pattern geometry valid
- [ ] Trigger and invalidation ordered correctly
- [ ] Pattern not stale
- [ ] Four-hour candle completed
- [ ] Momentum aligned
- [ ] Event status checked
- [ ] Contract feed identified
- [ ] DTE and delta inside hard range
- [ ] Spread, OI, volume, and freshness pass
- [ ] Full premium loss considered

### Pine Checklist

- [ ] Daily Command on daily chart
- [ ] Peer benchmark correct
- [ ] Selected pattern matches report
- [ ] Trigger and invalidation match the thesis
- [ ] Four-hour Momentum on four-hour chart
- [ ] Daily filter passes
- [ ] Alerts configured once per bar close
- [ ] No alert is treated as a brokerage instruction

### Data Checklist

- [ ] Market timestamp current
- [ ] Option quote current
- [ ] Event timestamp current
- [ ] Feed is OPRA or state remains verification
- [ ] No incomplete candle
- [ ] No missing or zero-volume bar
- [ ] No crossed or zero-ask quote

---

## 20. Common Errors

### Chasing A Stale Breakout

The pattern confirmed several bars ago and price is extended. The correct state is
stale or rejected, not ready.

### Treating Indicative Quotes As Tradable

Indicative data can support research but cannot establish a fully trustworthy
contract.

### Ignoring Earnings

Unknown earnings is not clear earnings. The state remains verification.

### Using Premium As The Thesis

The option premium is noisy. The underlying invalidation defines the thesis.

### Optimizing Hit Rate

A high positive-return frequency can still produce poor outcomes if losses are large,
spreads are wide, or the sample is concentrated. Optimize robust after-cost evidence,
not a headline percentage.

### Adding Every Indicator To The Score

More indicators do not automatically mean more information. Correlated indicators
can double-count the same trend. New evidence requires a causal rationale and
held-out improvement.

---

## 21. Glossary

**ATR:** Average True Range, a volatility measure used to scale distances.

**AVWAP:** Anchored volume-weighted average price. The implementation uses a recent
rolling volume-weighted reference.

**Bid:** Highest displayed buying price.

**Ask:** Lowest displayed selling price.

**DTE:** Calendar days to expiration.

**Delta:** Modeled option-price sensitivity to underlying price.

**Gamma:** Modeled rate of change in delta.

**Theta:** Modeled sensitivity to passage of time.

**Vega:** Modeled sensitivity to implied volatility.

**Implied volatility:** Volatility embedded in option pricing.

**Open interest:** Outstanding contracts.

**MFE:** Maximum favorable excursion after entry.

**MAE:** Maximum adverse excursion after entry.

**Point in time:** Data known at the historical decision timestamp.

**Walk-forward:** Chronological train-then-test evaluation.

**Shadow validation:** Forward observation without changing production behavior.

---

## 22. Authoritative Sources

- [OCC Characteristics and Risks of Standardized Options](https://www.theocc.com/company-information/documents-and-archives/options-disclosure-document)
- [FINRA Options Investor Guide](https://www.finra.org/investors/investing/investment-products/options)
- [Alpaca Historical Option Data](https://docs.alpaca.markets/us/docs/historical-option-data)
- [Massive Options Data](https://www.massive.com/business-options)
- [TradingView Pine Repainting Guidance](https://www.tradingview.com/pine-script-docs/concepts/repainting/)
- [TradingView Pine Limitations](https://www.tradingview.com/pine-script-docs/writing/limitations/)
- [TradingView Alerts](https://www.tradingview.com/pine-script-docs/concepts/alerts/)
- [TradingView Pine Screener Requirements](https://www.tradingview.com/support/solutions/43000742436-tradingview-pine-screener-key-features-and-requirements/)
- [Exchange Calendars](https://github.com/gerrymanoim/exchange_calendars)

The OCC disclosure document should be read before buying or selling exchange-traded
options. Provider and platform documentation can change; verify the current version
before relying on a feature or data field.
