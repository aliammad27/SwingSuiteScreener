# Ali Swing Suite v2 — Aggressive Contract Profile

**The complete training manual for the high-risk, high-reward version of the Final Swing System**

**Purpose:** This manual replaces the v1 Expert Training Guide as the operating doctrine for the aggressive contract profile. The stock-selection engine is unchanged — the same Command Center, the same Momentum Confirmation, the same S tier and A Plus gates enforced by the SwingSuiteScreener. What changed is everything that happens *after* a setup qualifies: the expiration window, the strike placement, the sizing, and the management rules. v1 was built to survive being wrong slowly. v2 is built to get paid fast for being right — and to get out fast when it isn't.

Educational use only. This is not financial advice and not a recommendation to buy or sell any security or option contract. Long options can and regularly do lose 100% of the premium paid. The aggressive profile loses more often than it wins by design. Read Section 2 before anything else — if the math in that section is not acceptable, do not trade this profile.

---

# 1. What Changed From v1 And Why

## The One-Paragraph Version

v1 bought 45–60 DTE, 0.45–0.65 delta contracts — near-the-money, long-dated, forgiving. A v1 trade could stall for a week and survive. v2 buys 14–21 DTE, 0.25–0.35 delta contracts — out-of-the-money, short-dated, unforgiving. A v2 trade that stalls for three days is dead and must be cut. In exchange, a v2 winner routinely returns +150% to +300% on premium where the equivalent v1 winner returned +40% to +80%. The trade quality bar went *up*, not down: only S tier and A Plus setups are tradeable. Everything else — B tier, Technical Watch, and every "interesting" chart — is watch-only.

## The Full Change Table

| Dimension | v1 (Conservative) | v2 (Aggressive) | Why it changed |
| :---- | :---- | :---- | :---- |
| Setups traded | S, A+ preferred | S and A+ **only**, mechanically | Low win-rate contracts cannot afford B-grade charts |
| DTE window | 45–60 (puts 45–70) | **14–21** (hard min 10, max 25) | Pay for the move, not for insurance you'll exit before using |
| Delta band | 0.45–0.65 | **0.25–0.35** (hard floor 0.20) | OTM convexity: small premium, multiplied payoff |
| Strike | ~ATM at trigger | **Halfway between trigger and target** | Strike the stock can actually reach inside the window |
| Hold window | 5–14 days | **3–7 days** | Theta curve makes longer holds structurally losing |
| Stop | Chart invalidation | **−50% premium, hard** | Chart stops trigger too late on short-dated contracts |
| Time stop | Loose | **2–3 days of no progress** | A stalled short-dated OTM option is a melting ice cube |
| Profit taking | Discretionary at target | **Sell half at +100%, mandatory** | Converts the win-rate math from fatal to survivable |
| Forced exit | Expiration-aware | **Exit or roll by 5 DTE, no exceptions** | Theta and gamma go vertical inside 5 DTE |
| Sizing | Small fixed fraction | **Max 5% of account premium per trade** | The ceiling, not the target — see Section 2 |
| Concurrency | Not formalized | **Max 4 positions; correlated sector = 1** | Three semis calls are one trade wearing three hats |
| New filter | — | **Movement filter** (screener-enforced) | A perfect chart on a slow stock cannot pay an OTM strike |
| Earnings | 7-day blackout | 7-day blackout, **unchanged** | Short-dated OTM through earnings is a different strategy |
| Direction | Calls only | **Calls and puts** | The screener's bearish side is live; both directions trade |

## What Did NOT Change — Read This Twice

The selection layer is untouched and this is deliberate. Command Score math, momentum scoring, RSI/MACD logic, higher-timeframe filters, relative strength, anchored VWAP, weekly alignment, structure classification, market regime, and every S/A+ threshold are byte-for-byte identical to v1. **You are not taking worse trades. You are taking the same elite trades with a more violent instrument.** The moment you catch yourself relaxing a selection gate because the contract is "only" costing 2% of the account, you have broken the system at its foundation. Aggression lives in the contract layer and nowhere else.

---

# 2. The Honest Math — The Section That Keeps You Alive

Every rule in this manual is downstream of the arithmetic in this section. Do not skim it.

## The Expectancy Model

A 0.25–0.35 delta, 14–21 DTE contract on an S/A+ setup has a realistic profile of roughly:

```text
Win rate:        30–40% (assume 35% for planning)
Average winner:  +150% of premium (half sold at +100%, half runs)
Average loser:   −55% of premium (−50% hard stop plus slippage/spread)
```

Expectancy per trade, per dollar of premium:

```text
EV = (0.35 × 1.50) − (0.65 × 0.55)
   = 0.525 − 0.3575
   = +0.1675  →  roughly +17% of premium per trade
```

At 5% of account per trade, that is roughly **+0.8% of account expected value per trade**. Over 100 disciplined trades a year, that compounds meaningfully. That is the entire pitch — and every word of it depends on three things holding: the win rate (which depends on taking *only* S/A+), the average winner (which depends on the mandatory half-off at +100% and letting the rest run), and the average loser (which depends on the −50% stop being a hard rule, not a suggestion).

## The Losing Streak Table — Memorize It

At a 35% win rate, losing streaks are not a possibility. They are a schedule.

| Streak length | Probability of any given run | Over 100 trades | Account damage at 5%/trade |
| :---- | :---- | :---- | :---- |
| 4 straight losses | 17.9% | Near-certain, multiple times | ~11% drawdown |
| 6 straight losses | 7.5% | Expect it more than once | ~16% drawdown |
| 8 straight losses | 3.2% | Expect it at least once | ~20% drawdown |
| 10 straight losses | 1.3% | Plausible in a bad year | ~25% drawdown |

(Damage assumes average loser of −55% of a 5% premium position ≈ −2.75% of account each.)

**The conclusions you must internalize:**

1. An 8-trade losing streak is a *normal operating condition* of this profile, not evidence the system is broken. The system is broken only if selection discipline broke.
2. This is why 5% is the ceiling. At 10% per trade the same schedule of streaks produces 40%+ drawdowns, which require +67% just to recover, which produces desperation sizing, which ends accounts. The math compounds against the impatient.
3. This is why you must take **every** qualifying S/A+ signal. At a 35% win rate, the entire year's profit typically lives in 5–8 outlier winners. Skip two of them because you were demoralized by a streak, and the year is negative. Mechanical execution is not a virtue here; it is the arithmetic.

## Why The Winners Must Run

Sell half at +100% and the banked half pays for roughly two average losers. The runner half is where the year is made: a runner that reaches +300% turns one trade into the equivalent of four winners. If you habitually take the whole position off at +50% because "profit is profit," your average winner collapses toward +50%, and the expectancy goes negative:

```text
EV = (0.35 × 0.50) − (0.65 × 0.55) = 0.175 − 0.3575 = −0.18   ← losing system
```

Same setups. Same stop. Same win rate. **Negative expectancy purely from impatient profit-taking.** The half-at-+100% rule is not style. It is the load-bearing wall.

---

# 3. System Architecture

## The Five Layers

```text
Layer 1 — Screener (SwingSuiteScreener):  produces S, A+, TW, B, Watch lists nightly
Layer 2 — Daily chart (Command Center):    confirms the selection with your own eyes
Layer 3 — 4H chart (Momentum Confirmation): times the entry
Layer 4 — Contract (broker option chain):  DTE, delta, strike, IV, spread, liquidity
Layer 5 — Management (this manual):        stops, time stops, scaling, forced exits
```

The chain of command is absolute: a lower layer can never overrule a higher one. A beautiful 4H trigger on a B tier name is not a trade. A perfect S tier chart with a 15%-wide option spread is not a trade. In v2 this discipline matters *more* than in v1 because each individual trade is more fragile — the edge is the stack, and the stack is only as strong as the layer you skipped.

## Screener Tiers → Actions

| Screener output | v2 action |
| :---- | :---- |
| **S tier** | Trade candidate. Verify layers 2–4 by hand, then execute the playbook. |
| **A Plus** | Trade candidate. Same process; note the missing confirmation and whether it's about to resolve. |
| **Technical Watch** | Watch only. Chart qualified, option liquidity unverifiable on free data. Verify the chain in the broker yourself — if the contract passes every Section 7 gate, it may be treated as A+; if anything is unverifiable, it stays watch. |
| **B tier** | Watch only. No exceptions, no "it's almost A+." Set alerts, wait for promotion. |
| **Watch list** | Radar only. These feed tomorrow's candidates, not today's orders. |
| **Rejected** | Read the rejection codes weekly. `insufficient_movement_capability` on a great chart teaches you what this profile can and cannot trade. |

## The Movement Filter — v2's New Gate

The screener now enforces two conditions before any name reaches S or A+:

```text
1. target_gain_percent ≥ 1.5 × required_move_percent
   (the move to target must be at least 1.5× the move needed to reach
    the research strike plus a 1% premium cushion)

2. Daily ATR% ≥ 2.0
```

**Why it exists:** v1's ATM contracts profited from modest moves, so a slow, grinding megacap with a 90 Command Score was a fine v1 trade. A v2 OTM strike needs the stock to *travel*. A stock that averages 1.2% daily range cannot reliably reach a strike 4% away inside two weeks — the chart is right and the option still dies. The movement filter removes these before you ever see them. When you see a gorgeous chart rejected for `atr_percent_below_floor`, the correct response is gratitude, not override.

---

# 4. Layer 1–2: Stock Selection (Both Directions)

## Bullish Side — Unchanged Gates, Sharper Focus

Everything from v1 stands: Command Score 75+ (85+ for S), bullish MA stack, relative strength leading, price above monthly anchored VWAP, weekly aligned, not extended, daily RSI 50+, daily MACD bullish or strengthening, no warning active. The v2 refinement is which Call Bias states are *executable*:

| Call Bias | v2 status |
| :---- | :---- |
| Breakout confirmed (with volume expansion) | **Executable** — Playbook A |
| Pullback setup (held support, green close, above AVWAP) | **Executable** — Playbook B |
| Bullish (75+, no active trigger) | **Not executable.** Watch. In v1 this was tradeable with judgment; in v2 an un-triggered entry burns 2–3 of your 3–7 day hold window waiting, which is fatal to a 14–21 DTE contract. No trigger, no trade. |
| Breakout watch | Alert set. Nothing else. |
| Extended / Watch / Mixed / Avoid | Skip, exactly as v1. |

## Bearish Side — The Mirror Image

The put side of the screener grades bearish setups with mirrored logic: price below the major moving averages, bearish stack, relative *weakness* against the benchmark, price below monthly anchored VWAP, weekly misaligned, daily RSI below 50, daily MACD bearish. The two executable bearish states:

| Put setup | Definition | Character |
| :---- | :---- | :---- |
| **Rejection** | Price rallies into a falling MA / resistance / AVWAP from below and gets rejected with a bearish close | The put-side equivalent of a pullback entry. Structurally the better entry — see the IV logic in Section 8. |
| **Breakdown** | Completed close below the breakdown level (recent structural low) with volume | The put-side breakout. Valid, but you are often paying spiked IV — extra scrutiny required. |

**Bearish asymmetries an expert respects:** stocks fall faster than they rise but bounce violently (short-covering rallies will hit your −50% stop harder and faster than call-side pullbacks); downside measured moves overshoot less reliably (the screener's 22%-below-trigger target floor exists for this reason); and hostile market regime — which blocks call-side S tier — is often exactly when put-side setups cluster. In a hostile regime, the put book *is* the book.

## Universe Character

The movement filter does this mechanically, but know your pond: the v2 universe is high-beta by construction — semiconductors, high-growth software, crypto-adjacent names, momentum leaders. These names produce both the 6% weekly moves that pay OTM strikes and the brutal reversals that hit stops. That is the deal. A v2 trader who drifts toward "safer" slow names hasn't reduced risk — they've kept the loss profile and deleted the payoff.

---

# 5. Layer 3: 4-Hour Timing

Timing rules carry over from v1 — 4H Momentum ~70+, higher-timeframe filter passed, Overall Bullish/Strong bullish (mirrored for puts), entry on trigger close or held support with volume — with two v2 tightenings:

**1. The trigger must be *now*.** In v1, "approaching" was often good enough because a 50 DTE contract could wait. In v2, you enter on the completed 4H close through the trigger (calls: above green trigger; puts: below breakdown trigger) or on a confirmed hold of support/rejection at resistance. If it hasn't happened on a *completed* candle, you have an alert, not a position. Every day of waiting inside a position is ~5–8% of the contract's remaining life.

**2. Late is the same as wrong.** If price triggered two 4H candles ago and has already traveled 40%+ of the distance to target, the trade is gone. Chasing converts the best setups into the worst entries because the strike you'd need is now further OTM and the IV you'd pay is higher. There will be another trigger this week — the screener's whole job is making sure of it.

---

# 6. Layer 4: The Contract — Expiration

## The Window: 14–21 DTE

```text
Target window:   14–21 DTE at entry
Hard minimum:    10 DTE (never enter below this)
Hard maximum:    25 DTE
Planned hold:    3–7 days
Forced exit:     close or roll the moment the position reaches 5 DTE
```

The logic is the 2–3× rule applied honestly: a 3–7 day intended hold needs 14–21 days of runway. v1's 45–60 DTE bought insurance against stalls — but v2 doesn't hold through stalls (the time stop kills them at day 2–3), so that insurance is pure cost. You are paying only for the days you will actually use.

## Why 14–21 And Not 7

Inside ~10 DTE, theta stops being a rent payment and becomes a fire. An ATM-ish option loses value roughly in proportion to the *square root* of time remaining — meaning the last week of an option's life contains almost half its total decay. At 18 DTE, a flat day costs you roughly 3–4% of the contract; at 6 DTE, a flat day costs 10–15%. The 14–21 window gives your 3–7 day hold room to be right *slightly slowly*. Sub-10 DTE gives it none — that zone is reserved for one situation only: same-day continuation on a confirmed breakout with expanding volume, exited same-day or next-day. It is never a hold.

## The 5 DTE Forced Exit

Non-negotiable, profitable or not. Inside 5 DTE, gamma makes the position violently binary and theta consumes whatever thesis remains. If the trade still looks alive at 5 DTE, **roll**: close this contract, and re-enter a fresh 14–21 DTE contract *only if the setup would qualify as a brand-new entry today* — current trigger/support state, current IV, full checklist. A roll is a new trade that must pass every gate, not a fee to keep hoping.

## Earnings Inside The Window: Automatic Skip

If the underlying reports earnings inside your expiration window, the trade does not exist — even if the blackout's 7-day gate technically passes. Short-dated OTM options into earnings are an IV-crush machine wearing a lottery ticket costume. The screener's blackout stays on and event trades stay off.

---

# 7. Layer 4: The Contract — Strike Selection

## Delta Is Primary

```text
Target band:  0.25 – 0.35 delta (absolute value; same for puts)
Hard floor:   0.20 delta — below this, the contract is untradeable, period
Center:       ~0.30 delta
```

Delta is the market's own probability-weighted estimate of where the stock can reach — it prices in this stock's actual volatility, which is why it beats any fixed "X% OTM" rule. A 0.30 delta call on a high-ATR semi and a 0.30 delta call on anything else represent comparable risk postures; "5% OTM" on those two names would not.

**Why this band:** at 0.45–0.65 (v1), you pay heavily for intrinsic and get modest percentage payoffs. Below 0.20, three things converge to delete the edge: the bid-ask spread becomes enormous relative to premium (a $0.05 spread on a $0.35 contract is 14% lost instantly), theta consumes a huge *fraction* of the small premium daily, and the strike sits beyond what the measured move actually projects — you're no longer trading the setup, you're buying a lottery ticket that happens to share a ticker with it. The 0.25–0.35 band is where OTM convexity is real and the strike is still *inside the thesis*.

## The Research Strike Formula

The screener computes a research strike for every candidate:

```text
Calls: strike = trigger + 0.5 × (target − trigger), rounded UP to the increment
Puts:  strike = trigger − 0.5 × (trigger − target), rounded DOWN to the increment
```

Halfway between trigger and target: far enough OTM to be cheap and convex, close enough that the stock reaching your *chart target* puts the contract solidly ITM. The workflow: open the chain at 14–21 DTE, find the 0.25–0.35 delta strikes, and check that the research strike falls inside that band. **If delta and formula agree** — normal case — you have your strike. **If they disagree**, believe delta and investigate: formula-strike far below the 0.30-delta strike means IV is elevated (see IV gate); formula-strike above the 0.25-delta zone means your target likely overruns what the market prices as reachable — re-examine the target before trading, because one of you is wrong and it's usually the synthetic target. Remember the screener's target is a measured-move *estimate* (`trigger + 2× (close − support)`), not a real chart level: confirm actual resistance/support on TradingView before it anchors your strike.

## Worked Example — Call Side

```text
Setup:    S tier semiconductor. Close 100.40, ATR% 2.8
Levels:   4H trigger 101.00 | support 98.20 | target/resistance 108.00
Strike:   101 + 0.5 × (108 − 101) = 104.50 → rounds up to 105
Chain:    18 DTE, 105 strike, delta 0.31, premium $1.65, spread $0.08 (~5% of mid)
Movement: move to strike+cushion ≈ 5.6%; move to target ≈ 7.6% → 1.36×... 
          marginal — the screener flags this; a target of 109+ or entry
          nearer the trigger passes cleanly. Assume entry at 101 on trigger.
Size:     $20,000 account → 5% cap = $1,000 → 6 contracts ($990)

Outcomes from entry at $1.65:
  Stock → 105 in 3 days:  contract ≈ $3.30–3.70  →  +100–125% → sell half
  Stock → 108 in 5 days:  contract ≈ $4.50–5.50  →  +170–230% on the runner
  Stock stalls at 101–102 for 3 days: contract bleeds to ≈ $1.05 → TIME STOP
  Stock breaks 98.20:     contract ≈ $0.80 → the −50% HARD STOP already fired

Account impact: full loss of the position = −5.0%. Stopped loss ≈ −2.7%.
Half-at-+100% then runner to target ≈ +7% to +9% of account. That asymmetry
— risk 2.7 to make 7–9 — is the entire strategy in one trade.
```

## The Breakeven Trap — Mark-to-Market Thinking

The chain shows expiration breakeven (strike + premium: 106.65 above). **Ignore it.** You exit in 3–7 days, never at expiration, so your real P&L is mark-to-market: the stock reaching the *strike* with 12 days left is roughly a double, not a breakeven. This cuts both ways — it's why a stalled position loses 35% without the stock dropping a cent, and it's why the −50% stop can fire while the "stock stop" is untouched. In v2 the option's clock is as real as the stock's price.

---

# 8. Layer 4: Implied Volatility — The Invisible Opponent

Short-dated OTM contracts are maximally exposed to IV. On a 0.30 delta, 18 DTE contract, virtually the entire premium is extrinsic — an IV drop from 45 to 35 can cost 25–30% of the contract's value with the stock unchanged. You can be right on direction and lose to vega alone.

## The Gates

```text
Prefer:   IV Rank < 50, and IV not visibly spiking on the entry candle
Caution:  IV Rank 50–70 — S tier setups only, and expect thinner payoffs
Skip:     IV Rank > 70 — the contract is pre-charging you for the move
```

## The Structural Edge: Entry Type Determines Your IV Price

**Calls:** IV expands on breakout candles. Chasing a confirmed breakout means buying the moment the option market repriced. A pullback entry (Playbook B) buys when IV has cooled during the quiet dip — often 15–25% cheaper vega on the *same stock at a similar price*. When both playbooks are live, the pullback is systematically the better contract.

**Puts — this asymmetry is bigger and most traders never learn it:** fear moves IV harder than greed. A confirmed breakdown candle can spike IV 30–50% in a session, so the breakdown-chase put buyer pays peak panic premium and then faces the double hit: any bounce costs them on delta *and* on the IV crush as panic recedes. The **rejection entry** — bought as price rallies into resistance, when the market has relaxed and IV has bled off — buys cheap vega *before* the panic that will inflate it. On the put side, the rejection playbook isn't just a nicer chart entry; it is the difference between owning volatility before it's priced and renting it after.

## Liquidity Gates (Unchanged, Now Load-Bearing)

Spread ≤ 10% of mid, open interest ≥ 500, contract volume ≥ 100 — same as v1, but at $1–2 premiums the spread rule binds constantly. A $0.15 spread was noise on v1's $6.00 contract (2.5%); on v2's $1.50 contract it is 10% — a full boundary case, and you pay it twice. Always work limit orders at or near mid; walking a nickel toward the ask beats crossing an 8% spread at market. On free/indicative data (Technical Watch), *none* of this is verifiable outside the broker — verify live, or the trade doesn't exist.

---

# 9. Layer 5: Position Sizing And Portfolio Rules

```text
Per trade:     ≤ 5% of account in premium — a CEILING, not a target
Standard S:    4–5%
Standard A+:   3–4%
Concurrent:    ≤ 4 open positions
Correlation:   same-sector / same-theme names count as ONE position slot
Total at risk: ≤ 15–20% of account in open premium at any moment
```

**The ceiling logic:** Section 2's streak table is calibrated to 5%. Sizing to 7% "because this one is special" doesn't make the special trade win more often — it makes the scheduled 8-loss streak cost 28% instead of 20%. There are no special trades, only the distribution.

**The correlation rule is the one that saves you:** three calls on three semiconductor names is one trade on the semiconductor index with three commissions. When the sector reverses, all three hit −50% stops in the same session — a single hidden 15% position masquerading as diversification. One name per theme. If two S tiers appear in one sector, take the better contract (delta band fit, IV rank, spread) and let the other go.

**Drawdown circuit breakers:**

```text
−15% from equity high:  size floor — every position drops to 3% max
−25% from equity high:  full stop — no new trades for 5 sessions;
                        audit every trade in the drawdown against this manual.
                        Rule-following losses → variance → resume at 3%.
                        Rule-breaking losses → the problem isn't the system.
```

---

# 10. Layer 5: Trade Management

Entry gets you into the distribution. Management is what makes the distribution profitable. These five rules are mechanical — no judgment, no context, no exceptions:

## The Five Hard Rules

```text
1. HARD STOP:    −50% of premium → exit immediately. Not −55 "to give it room."
2. TIME STOP:    2–3 days without meaningful progress toward target → exit,
                 regardless of P&L. Flat is a loss with the clock running.
3. SCALE:        +100% on premium → sell half. Mandatory. Banked half ≈ two
                 average losers paid for.
4. RUNNER:       remaining half runs toward the chart target with a trailed
                 stop at breakeven-on-premium, tightened to the 4H structure
                 (trail under 4H higher lows for calls; above lower highs for puts).
5. FORCED EXIT:  5 DTE → close or roll (roll = new trade, full re-qualification).
```

## Why The Chart Stop Is Demoted

In v1, the chart stop (support break, warning break, bias loss) was primary. In v2 it still *matters* — a support break is an immediate exit even at −20% — but it can no longer be the *only* stop, because on a short-dated OTM contract the premium routinely hits −50% before the chart level breaks. The −50% stop protects you from the option's clock; the chart stop protects you from the stock. **Whichever fires first wins.** Both firing on the same candle means the setup failed completely — exit at market and journal it.

## What "Meaningful Progress" Means (Time Stop)

By end of day 2 in the position, price should have moved at least ~one-third of the distance from entry to target, or be pressing the trigger with volume after a clean retest. "It hasn't gone against me" is not progress — an OTM option position that goes sideways for 3 days has lost 25–35% while you waited for the stock to make up its mind. The time stop exists because *the most common way this profile loses money is not being wrong — it's being early, slowly.*

## The Runner's Exit

The runner half exits on the first of: chart target reached (take it — targets are targets), trailing structure break, +250–300% (take at least half of the runner; parabolic marks decay fast), or 5 DTE. Never let a +200% runner round-trip below +100% out of greed; the trailed breakeven-on-premium stop makes that structurally impossible if you actually place it. Place it.

---

# 11. The Four Playbooks

## Playbook A — Bullish Breakout Continuation

```text
Chart:    S/A+ | Breakout confirmed with volume expansion | not extended
Timing:   completed 4H close above green trigger, HTF passed
Contract: 14–21 DTE, 0.25–0.35Δ, strike ≈ trigger + half the run to target
IV note:  you are paying the breakout IV pop — demand IV Rank < 50 and skip
          if the entry candle itself spiked IV visibly
Kill it:  close back below the breakout level = failed breakout = exit,
          don't wait for −50%
```

## Playbook B — Bullish Pullback (The Best Contract Prices On The Call Side)

```text
Chart:    S/A+ | Pullback setup: support touched, held, green close, above AVWAP
Timing:   4H momentum turning up from support; entry on 4H higher-low
          confirmation or trigger reclaim
Contract: same band — but IV has cooled during the dip; same stock,
          cheaper vega. This is the systematically superior call entry.
Kill it:  daily close below the pullback support = setup dead at any P&L
```

## Playbook C — Bearish Rejection (The Best Contract Prices, Period)

```text
Chart:    put-side S/A+ | rally into falling MA / resistance / AVWAP from
          below, rejected with bearish close | relative weakness
Timing:   4H lower-high confirmed at resistance, HTF bearish agreement
Contract: 14–21 DTE, 0.25–0.35Δ puts, strike ≈ trigger − half the run to target
IV note:  THE structural edge — you own vega before the panic prices it.
          This entry buys fear wholesale and sells it retail.
Kill it:  close back above the rejection resistance = thesis dead
Manage:   bounces are violent; honor the −50% stop without hesitation and
          respect the 22%-floor targets — downside overshoot is less reliable
```

## Playbook D — Bearish Breakdown (Valid, But You're Buying Retail)

```text
Chart:    put-side S/A+ | completed close below breakdown level with volume
Timing:   4H close below trigger; no chasing after 40% of the move is gone
Contract: same band — but breakdown candles spike IV 30–50%. Only take it
          when IV Rank was low BEFORE the break, or on the first orderly
          retest of the breakdown level from below (IV cools on the retest —
          the put-side equivalent of Playbook B).
Kill it:  reclaim of the breakdown level = failed breakdown = short-covering
          fuel = exit immediately, this is the fastest-reversing pattern
          in the book
```

---

# 12. Scenario Training

**Scenario 1 — The system working.** S tier, Command 88, 4H closes above trigger on volume. 17 DTE 0.31Δ call at $1.80, IV Rank 38, 4.5% position. Day 2: +105% → half sold. Day 5: target hit, runner out at +240%. *Total: ~+8% of account. Note what you did between entry and exit: nothing. The rules did everything.*

**Scenario 2 — Right stock, dead contract.** A+ pullback entry; support holds beautifully… sideways. Day 3, stock down 0.3%, contract −38% on pure theta+vega. Time stop: **exit.** Stock breaks out on day 6 and you feel robbed. Run the counterfactual honestly: contract was at −55% by day 5 — the "robbery" saved you money, and re-entry on day 6's fresh trigger was always available. *The time stop will be the rule you hate most and need most.*

**Scenario 3 — The streak.** Trades 31–37: seven consecutive stopped losses, −18% from equity high, every trade rule-clean. Audit says variance. −15% breaker → 3% sizing. Trade 38 is an S tier semi you feel like skipping ("nothing works"). Section 2: the year lives in 5–8 winners and this could be one. **Take the trade at 3%.** It doubles; the streak math was never broken. *Skipping trade 38 is how profitable systems produce losing traders.*

**Scenario 4 — The IV trap.** Breakdown closes −6% on huge volume, put-side S tier fires. IV Rank 81. Playbook D says the setup is real but the contract is poisoned: at 0.30Δ the premium is double normal. **Pass, set alert for the retest.** Two days later price rallies back to the breakdown level, IV Rank 52, rejection forms — Playbook C entry at nearly half the vega cost, better strike, tighter invalidation. *The chart and the contract are separate qualifications. The market pays patience on the put side.*

**Scenario 5 — Correlation masquerading as opportunity.** Monday's scan: three S tiers — all AI-semiconductor names. The v1 brain says "three great trades." The v2 rule says one theme = one slot. Rank by contract (IV rank, spread, delta-band fit), take the best, alert the others. Wednesday: sector-wide reversal on one bad guidance report; the taken position stops at −2.5% of account. All three would have been −7.5%. *The correlation rule pays for this manual annually.*

**Scenario 6 — The 5 DTE seduction.** Runner at +160%, target 2% away, position hits 5 DTE. "Two more days and it tags it." **Close it.** +160% banked. If the thesis is truly alive, a fresh 16 DTE contract re-qualifies as a new trade tomorrow. Inside 5 DTE the trade stops being your system and starts being a coin flip with rent due hourly.

---

# 13. Failure Modes — How This Strategy Actually Dies

Ranked by body count, not by drama:

1. **Selection creep.** B tier "close enough" trades. Each one nudges the 35% win rate toward 28%, and Section 2's math goes negative quietly, over months. The screener gates exist so this is a choice, not an accident. *Defense: S/A+ only is definitional — a B tier trade isn't a worse v2 trade, it's not a v2 trade.*
2. **Impatient profit-taking.** Whole position off at +40–60% repeatedly. Feels disciplined; produces a negative-EV system (Section 2 shows the exact arithmetic). *Defense: half at +100% is mandatory, the runner has a placed stop, and the journal tracks "runner P&L given up" as its own column.*
3. **Streak psychology.** Skipping qualified signals or shrinking size mid-streak (missing the recovery winners), then revenge-oversizing after (meeting the next streak at 10%). *Defense: circuit breakers are the only sanctioned size changes. Every S/A+ gets taken.*
4. **Stop negotiation.** −50% becomes −65% "because support is right there." The stop's whole function is to fire *before* the chart proves anything — that's the design, not a flaw. *Defense: it's a standing order placed at entry, not a decision made at −48%.*
5. **Theta denial.** Holding flat positions past the time stop because "nothing bad happened." Slow bleed across many positions, invisible on any single one. *Defense: day-2 progress check is a calendar event, literally scheduled.*
6. **Regime blindness.** Running the call book hard into a deteriorating market because individual charts still look fine. Hostile regime already blocks call-side S tier — respect what that's telling you, and remember the put book exists precisely for those tapes.

---

# 14. Routines

## Nightly (after the screener's prep message)

1. Read S/A+ lists — both directions. For each: verify the chart by eye (Layer 2), locate real support/resistance (don't outsource this to the synthetic target), pre-write the plan: trigger, strike, delta, DTE, IV rank, max premium, stop, time-stop date, target.
2. Read Technical Watch and B tier for tomorrow's promotions. Set alerts at their triggers.
3. Scan rejection codes for your open names — a held position whose underlying just went `Rejected` is management information tonight, not tomorrow.
4. Check open positions against the calendar: DTE remaining, time-stop dates, earnings creep.

## At Entry (90 seconds, every time)

The one-sentence thesis, v2 form: *"I'm buying the [ticker] [strike][C/P] [exp] at [premium] because [S/A+ + playbook], delta [x], IV rank [x], stop −50% = [$], time stop [date], half off at [2× premium], runner target [level], max account risk [x]%."* Can't say it fluently → not ready to order.

## Weekly Review

Process-vs-outcome tagging, as v1 — plus the v2-specific columns: win rate by playbook (A/B/C/D), average winner (is it holding ≥ +150%?), average loser (is it holding ≤ −55%?), runner P&L given up, time-stopped trades that later worked (expect some — the rule is still right), correlation slots respected Y/N, and current drawdown vs. breakers. **If average winner sags below +120% or average loser swells past −60% for 20+ trades, the system is drifting — find which rule is being negotiated. It's always one of the five.**

---

# 15. Drills And Mastery

**Drill 1 — Streak inoculation.** Simulate 100 trades at 35%/+150%/−55% with a coin-flip script or dice. Watch real 6–8 loss streaks appear in a profitable sequence. Do this until a live streak feels like weather, not verdict.

**Drill 2 — Chain fluency.** Ten nights running: pick one S/A+ name, open the chain, find the 0.25–0.35Δ strikes at 14–21 DTE, compute the research strike by hand, note where they disagree and articulate why (IV? bad synthetic target?). Under three minutes = fluent.

**Drill 3 — Mark-to-market intuition.** For one contract, write down what it should be worth if the stock reaches the strike in 3 days vs. 8 days, and if it sits still for 3 days. Check against an options calculator. Repeat until your estimates land within 20%. This drill is what makes the time stop feel obvious instead of cruel.

**Drill 4 — Put-side IV reps.** Find five past breakdown candles on your universe. Note the IV before, at, and 3 days after the break. Price the hypothetical 0.30Δ put at each moment. Watch the retest entry beat the breakdown chase in four out of five — now Playbook D's caution is a scar you got for free.

**Drill 5 — The kill-list recital.** From memory: the five hard rules, the four playbook kill conditions, the two circuit breakers, the 5 DTE rule, the earnings rule, and the correlation rule. Every one, cold. These fire in moments when you will not want to think.

**Mastery standard:** you are ready for full size when you can (1) run 20 consecutive paper or minimum-size trades with zero rule violations — outcomes irrelevant, (2) explain to another trader *why* the half-at-+100% rule is load-bearing using the actual arithmetic, and (3) name, without looking, which failure mode in Section 13 is most likely to be *yours*. Everyone has one. Knowing yours is the difference between reading this manual and being governed by it.

---

# 16. The Cheat Sheet

## Enter Only When Every Line Is True

```text
□ Screener grade S or A Plus (this direction), verified on chart by eye
□ Playbook A, B, C, or D trigger on a COMPLETED 4H candle — happening now
□ ≤ 40% of the move to target already gone
□ 14–21 DTE, no earnings inside the window
□ Delta 0.25–0.35, research strike agrees (or you know exactly why not)
□ IV Rank < 50 (50–70 only for S tier, eyes open)
□ Spread ≤ 10% of mid, OI ≥ 500, volume ≥ 100 — verified LIVE in broker
□ ≤ 5% of account premium | ≤ 4 positions | theme slot free | ≤ 20% total at risk
□ Written: stop, time-stop date, scale point, runner plan, kill condition
□ One-sentence thesis said fluently
```

## While In The Trade

```text
−50% premium ............ OUT, immediately
Kill condition hit ....... OUT, at any P&L
Day 2–3, no progress ..... OUT (time stop)
+100% .................... HALF OFF, runner stop to breakeven, then trail 4H structure
Chart target ............. take it
5 DTE .................... OUT or re-qualified roll
```

## The Standard

v1's expert could explain why a setup passes. The v2 expert can do that *and* explain why the contract is priced fairly, what the position should be worth in three days if nothing happens, which of the five rules is currently closest to firing, and why the losing streak they are in right now changes nothing. Aggression in this system is not an emotion. It is a payoff structure, purchased with discipline, one rule at a time.

---

*Ali Swing Suite v2 — Aggressive Contract Profile. Selection engine unchanged from v1; contract layer, sizing, and management rules as implemented in SwingSuiteScreener aggressive contract profile v2 (14–21 DTE, 0.25–0.35Δ, movement filter). Educational use only — not financial advice. Long options routinely expire worthless; never trade this profile with money whose loss would change your life.*
