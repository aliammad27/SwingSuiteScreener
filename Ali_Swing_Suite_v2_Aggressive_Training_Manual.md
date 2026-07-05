# Ali Swing Suite — Aggressive Profile

**The complete training manual. Learn it until you breathe it.**

**Purpose:** This manual is the operating doctrine for the Ali Swing Suite aggressive profile — a short-dated, out-of-the-money options swing system that trades both directions. Calls on elite bullish setups. Puts on elite bearish setups. The stock is selected by the daily chart, timed by the 4-hour chart, expressed through a 14–21 DTE contract in the 0.25–0.35 delta band, and governed by five mechanical management rules. The system is enforced end-to-end: the SwingSuiteScreener grades every name nightly, the AS Command and AS Momentum TradingView indicators show the same math on the chart, and this manual is the layer that runs *you*.

Educational use only. This is not financial advice and not a recommendation to buy or sell any security or option contract. Long options can and regularly do lose 100% of the premium paid. This system loses more often than it wins **by design** — read Section 2 before anything else, and if the math there is not acceptable, do not trade this profile.

---

# 1. The System In One Breath

> Only elite setups. Both directions. Short-dated OTM contracts. Small fixed size. Five mechanical rules. The winners are large because the strikes are convex; the losers are small because the stops are absolute; the edge survives because you never negotiate with any of it.

## The Standing Orders

```text
1. Trade ONLY S tier and A Plus setups. Everything else is watch.
2. 14–21 DTE at entry. Exit or roll by 5 DTE. No exceptions.
3. 0.25–0.35 delta strikes. Hard floor 0.20. Delta is primary.
4. Max 5% of account premium per trade. Max 4 positions.
   Correlated sector names count as ONE position.
5. −50% premium hard stop. 2–3 day time stop. Half off at +100%.
6. Hold window 3–7 days. Never through earnings.
7. Losing streaks are scheduled, not exceptional. Take every signal.
```

## The Core Asymmetry

Every trade in this system risks roughly −2.7% of the account (the stop firing on a 5% position) to make +7% to +9% (half banked at +100%, runner to target). You will be wrong most of the time. The system is profitable anyway because the wins are three times the size of the losses. Protecting that ratio — not predicting the market — is your entire job. Every rule in this manual exists to protect one side of that ratio or the other.

---

# 2. The Math That Governs Everything

Do not skim this section. Every rule downstream is derived from it.

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

## Why Short-Dated OTM At All

A near-the-money, long-dated contract buys insurance against stalls — it can sit sideways for a week and survive. This system never holds through stalls: the time stop kills every stalled position at day 2–3. So that insurance is pure wasted premium. A 14–21 DTE, 0.30 delta contract pays only for the days and the move you actually intend to use, and its convexity is what makes a +150% average winner possible on an ordinary 6% stock move. The instrument is violent because the payoff structure demands it — and the five hard rules exist precisely because the instrument is violent.

---

# 3. Architecture — The Five Layers

```text
Layer 1 — Screener (SwingSuiteScreener):   grades every name nightly, both directions
Layer 2 — Daily chart (AS Command):        confirms the selection with your own eyes
Layer 3 — 4H chart (AS Momentum):          times the entry
Layer 4 — Contract (broker option chain):  DTE, delta, strike, IV, spread, liquidity
Layer 5 — Management (this manual):        stops, time stops, scaling, forced exits
```

The chain of command is absolute: **a lower layer can never overrule a higher one.** A beautiful 4H trigger on a B tier name is not a trade. A perfect S tier chart with a 15%-wide option spread is not a trade. Each individual trade in this system is fragile — the edge is the stack, and the stack is only as strong as the layer you skipped.

## Screener Tiers → Actions

| Screener output | Action |
| :---- | :---- |
| **S tier** | Trade candidate. Verify layers 2–4 by hand, then execute the playbook. |
| **A Plus** | Trade candidate. Same process; note the missing confirmation and whether it's about to resolve. |
| **Technical Watch** | Watch only. Chart qualified, option liquidity unverifiable on free data. Verify the full contract chain live in the broker yourself — if every Section 7–9 gate passes, treat as A+; if anything is unverifiable, it stays watch. |
| **B tier** | Watch only. No exceptions, no "it's almost A+." Set alerts, wait for promotion. |
| **Watch list** | Radar only. These feed tomorrow's candidates, not today's orders. |
| **Rejected** | Read the rejection codes weekly. `insufficient_movement_capability` on a beautiful chart teaches you what this profile can and cannot trade. |

## The Movement Filter

The screener enforces two conditions before any name reaches S or A+, and the AS Command table shows the second one on every chart (the ATR FLOOR row):

```text
1. target_gain_percent ≥ 1.5 × required_move_percent
   (the move to target must be at least 1.5× the move needed to reach
    the research strike plus a 1% premium cushion)

2. Daily ATR% ≥ 2.0
```

**Why it exists:** an OTM strike needs the stock to *travel*. A stock that averages 1.2% daily range cannot reliably reach a strike 4% away inside two weeks — the chart can be perfectly right and the option still dies. A 90 Command Score on a slow megacap is a beautiful chart and a dead contract. When you see a gorgeous setup rejected for `atr_percent_below_floor`, the correct response is gratitude, not override.

## The TradingView Layout

Two-pane, symbol-synced. **Left: daily chart** with AS Command v2 (Direction: Both). **Right: 4-hour chart** with AS Momentum v2 (Direction: Both). Change the ticker once, both panes follow.

The daily pane owns selection: Command and Put Command scores, Call Bias and Put Bias, breakout/breakdown triggers, pullback support / rejection resistance, targets, room, the CALL STRIKE / PUT STRIKE research rows, and the ATR FLOOR row. The 4H pane owns timing: bull and bear momentum scores, the higher-timeframe gates, trigger/support/resistance reaction lines, the SIGNAL AGE row (your time stop, on screen), and the same ATR floor check. The two panes and the screener compute the same math — when they seem to disagree, one of them is looking at a completed candle and the other is not. Completed candles are the only candles that count.

---

# 4. Layer 1–2: Selection — The Bullish Side

The daily chart answers one question: *is this stock elite enough to pay premium on?* The Command Score answers it deterministically — trend stack (price above EMA 21, EMA 21 above SMA 50, SMA 50 above SMA 200), relative strength against the right benchmark, monthly anchored VWAP, volume expansion, structure, weekly alignment. S tier demands 85+; A Plus demands 75+ with at most one minor missing confirmation. You do not negotiate with the score.

Only two Call Bias states are executable:

| Call Bias | Status |
| :---- | :---- |
| **Breakout confirmed** (completed close through the 20-bar high, volume above average) | Executable — Playbook A |
| **Pullback setup** (support touched and held, green close, above monthly AVWAP) | Executable — Playbook B |
| Bullish (75+, no active trigger) | **Not executable.** Watch. An un-triggered entry burns 2–3 days of your 3–7 day hold window waiting for confirmation — fatal to a short-dated contract. No trigger, no trade. |
| Breakout watch | Alert set at the trigger. Nothing else. |
| Extended / Watch / Mixed / Avoid | Skip. Extended means strong stock, late entry — the most seductive skip in the book. |

The daily momentum thesis check rides on top: daily RSI at least 50, daily MACD bullish or strengthening, no warning active. A gorgeous moving-average stack with stalling momentum is a stock that is about to teach you what theta feels like.

## The Universe Is High-Beta By Construction

The movement filter does this mechanically, but know your pond: semiconductors, high-growth software, crypto-adjacent names, momentum leaders. These produce both the 6% weekly moves that pay OTM strikes and the brutal reversals that hit stops. That is the deal. Drifting toward "safer" slow names doesn't reduce risk — it keeps the loss profile and deletes the payoff.

---

# 5. Layer 1–2: Selection — The Bearish Side

The Put Command engine is the full mirror, graded by the screener and displayed by AS Command: price *below* the moving averages, bearish stack (EMA 21 below SMA 50 below SMA 200), relative *weakness* against the benchmark (the stock falling faster than QQQ/SPY is "Leading" for puts), price below monthly AVWAP, bearish weekly alignment (weekly close below weekly EMA 21), bearish volume expansion. Same point values, same 75+/85+ bars. Hard gate: **no put trade on a stock above its SMA 200**, mirroring no call trade below it.

Two executable Put Bias states:

| Put setup | Definition | Character |
| :---- | :---- | :---- |
| **Rejection setup** | Price rallies into overhead resistance (falling EMA 21 / SMA 50 / AVWAP / pivot high), touches it within 0.3 ATR, and closes back down red | The premier put entry. You are selling hope at the exact level where it dies — and buying your vega cheap (Section 9). |
| **Breakdown confirmed** | Completed close below the 20-bar low with volume above average | Valid, but you are often paying spiked IV. Extra scrutiny — Playbook D. |

**Bearish asymmetries an expert respects:** stocks fall faster than they rise but bounce violently — short-covering rallies hit put-side stops harder and faster than pullbacks hit call-side stops, so the −50% stop needs *more* obedience on this side, not less. Downside measured moves overshoot less reliably, which is why put targets are floored and put room math deserves skepticism. And when the market regime turns hostile — which blocks call-side S tier entirely — put setups cluster. In a hostile tape, **the put book is the book.**

---

# 6. Layer 3: Timing — The 4-Hour Chart

The 4H chart answers exactly one question: *is the move happening now?* AS Momentum answers it with a 0–100 score per direction, a higher-timeframe gate, and reaction levels drawn from the confirmation candle.

```text
Bullish timing requires:          Bearish timing requires:
  4H bull score ~70+                4H bear score ~70+
  HTF gate: daily RSI ≥ 50          HTF gate: daily RSI < 50
            and MACD above signal             and MACD below signal
  4H RSI ≥ 50, MACD above           4H RSI < 50, MACD below
  signal, histogram rising          signal, histogram falling
  Close above trigger (signal       Close below trigger (signal
  candle high) or held support      candle low) or rejection at
  with volume                       resistance
```

The higher-timeframe gate is the discipline that makes the 4H chart safe to use: **a 4H signal against the daily is noise, always.** The indicator shows "HTF blocked" for exactly this reason — when you see it, there is no trade, no matter how clean the 4H pattern looks.

Two rules with no flex in them:

**The trigger must be *now*.** Entry happens on the completed 4H candle that closes through the trigger, or on a confirmed hold/rejection at the level. If it hasn't happened on a *completed* candle, you have an alert, not a position. Every day spent inside a position waiting for confirmation costs ~5–8% of the contract's remaining life.

**Late is the same as wrong.** If price triggered two 4H candles ago and has already traveled 40%+ of the distance to target, the trade is gone. Chasing converts the best setups into the worst entries: the strike you'd need is now further OTM and the IV you'd pay is higher. There will be another trigger this week — producing them is the screener's entire job.

---

# 7. Layer 4: The Contract — Expiration

```text
Target window:   14–21 DTE at entry
Hard minimum:    10 DTE (never enter below this)
Hard maximum:    25 DTE
Planned hold:    3–7 days
Forced exit:     close or roll the moment the position reaches 5 DTE
```

The logic is the 2–3× rule applied honestly: a 3–7 day intended hold needs 14–21 days of runway — enough time to be right *slightly slowly*, and not a day more.

## Why Not Shorter

Inside ~10 DTE, theta stops being rent and becomes fire. An option loses value roughly in proportion to the *square root* of time remaining — nearly half of a contract's total decay lives in its final week. At 18 DTE, a flat day costs roughly 3–4% of the contract; at 6 DTE, a flat day costs 10–15%. Sub-10 DTE is reserved for exactly one situation: same-day continuation on a confirmed breakout with expanding volume, exited same-day or next-day. It is never a hold.

## The 5 DTE Forced Exit

Non-negotiable, profitable or not. Inside 5 DTE, gamma makes the position violently binary and theta consumes whatever thesis remains. If the trade still looks alive at 5 DTE, **roll**: close this contract and enter a fresh 14–21 DTE contract *only if the setup would qualify as a brand-new entry today* — current trigger state, current IV, full checklist. A roll is a new trade that must pass every gate, not a fee paid to keep hoping.

## Earnings Inside The Window: Automatic Skip

If the underlying reports earnings inside your expiration window, the trade does not exist. Short-dated OTM options into earnings are an IV-crush machine wearing a lottery ticket costume. The screener's 7-day blackout enforces the perimeter; you enforce the window.

---

# 8. Layer 4: The Contract — Strike Selection

## Delta Is Primary

```text
Target band:  0.25 – 0.35 delta (absolute value; calls and puts)
Hard floor:   0.20 delta — below this, the contract is untradeable, period
Center:       ~0.30 delta
```

Delta is the market's own probability-weighted estimate of where this stock can reach — it prices in this specific name's volatility, which is why it beats any fixed "X% OTM" rule. A 0.30 delta call on a high-ATR semi and a 0.30 delta put on a breaking-down software name represent comparable risk postures; "5% OTM" on those two names would not.

**Why this band:** closer to the money you pay heavily for intrinsic and get modest percentage payoffs. Below 0.20 delta, three things converge to delete the edge: the bid-ask spread becomes enormous relative to premium (a $0.05 spread on a $0.35 contract is 14% lost instantly), theta consumes a huge *fraction* of the small premium daily, and the strike sits beyond what the measured move actually projects — you are no longer trading the setup, you are buying a lottery ticket that shares a ticker with it. The 0.25–0.35 band is where OTM convexity is real and the strike is still *inside the thesis*.

## The Research Strike

The screener computes it, and AS Command displays it on every chart (CALL STRIKE / PUT STRIKE rows):

```text
Calls: strike = trigger + 0.5 × (target − trigger), rounded UP to the increment
Puts:  strike = trigger − 0.5 × (trigger − target), rounded DOWN to the increment
```

Halfway between trigger and target: far enough OTM to be cheap and convex, close enough that the stock reaching your *chart target* puts the contract solidly ITM. The workflow: open the chain at 14–21 DTE, find the 0.25–0.35 delta strikes, and check that the research strike falls inside that band. **When delta and formula agree** — the normal case — you have your strike. **When they disagree**, believe delta and investigate: formula-strike well inside the 0.30-delta strike means IV is elevated (Section 9 gate); formula-strike beyond the 0.25-delta zone means your target overruns what the market prices as reachable — re-examine the target, because one of you is wrong and it is usually the target. The screener's target is a measured-move *estimate*, not gospel: confirm real structure on the chart before it anchors your strike.

## Worked Example — Call Side

```text
Setup:    S tier semiconductor. Close 100.40, ATR% 2.8
Levels:   4H trigger 101.00 | support 98.20 | target/resistance 108.00
Strike:   101 + 0.5 × (108 − 101) = 104.50 → rounds up to 105
Chain:    18 DTE, 105 strike, delta 0.31, premium $1.65, spread $0.08 (~5% of mid)
Size:     $20,000 account → 5% cap = $1,000 → 6 contracts ($990)

Outcomes from entry at $1.65:
  Stock → 105 in 3 days:  contract ≈ $3.30–3.70  →  +100–125% → sell half
  Stock → 108 in 5 days:  contract ≈ $4.50–5.50  →  +170–230% on the runner
  Stock stalls at 101–102 for 3 days: contract bleeds to ≈ $1.05 → TIME STOP
  Stock breaks 98.20:     contract ≈ $0.80 → the −50% HARD STOP already fired

Account impact: stopped loss ≈ −2.7%. Half-at-+100% plus runner to target
≈ +7% to +9%. Risk 2.7 to make 7–9 — that asymmetry is the entire strategy
in one trade. The put side mirrors every number in the other direction.
```

## The Breakeven Trap — Think Mark-to-Market

The chain shows expiration breakeven (strike + premium). **Ignore it.** You exit in 3–7 days, never at expiration, so your real P&L is mark-to-market: the stock reaching the *strike* with 12 days left is roughly a double, not a breakeven. This cuts both ways — it is why a stalled position loses 35% without the stock dropping a cent, and why the −50% stop routinely fires while the "stock stop" sits untouched. The option's clock is as real as the stock's price. Traders who only think in stock prices get eaten by instruments that are priced in time.

---

# 9. Layer 4: Implied Volatility — The Invisible Opponent

Short-dated OTM contracts are maximally exposed to IV. On a 0.30 delta, 18 DTE contract, virtually the entire premium is extrinsic — an IV drop from 45 to 35 can cost 25–30% of the contract's value with the stock unchanged. You can be right on direction and lose to vega alone.

## The Gates

```text
Prefer:   IV Rank < 50, and IV not visibly spiking on the entry candle
Caution:  IV Rank 50–70 — S tier setups only, and expect thinner payoffs
Skip:     IV Rank > 70 — the contract is pre-charging you for the move
```

## The Structural Edge: Entry Type Determines Your IV Price

**Calls:** IV expands on breakout candles. Chasing a confirmed breakout means buying the moment the option market repriced. A pullback entry buys during the quiet dip when IV has cooled — often 15–25% cheaper vega on the *same stock at a similar price*. When both playbooks are live, the pullback is systematically the better contract.

**Puts — this asymmetry is bigger, and most traders never learn it:** fear moves IV harder than greed. A confirmed breakdown candle can spike IV 30–50% in a single session, so the breakdown-chase put buyer pays peak panic premium and then faces the double hit — any bounce costs them on delta *and* on IV crush as panic recedes. The **rejection entry** — bought as price rallies into resistance, when the market has relaxed and IV has bled off — owns the volatility *before* the panic that will inflate it. On the put side, the rejection playbook is not just a nicer chart entry; it is the difference between buying fear wholesale and renting it retail.

## Liquidity Gates — Load-Bearing At These Premiums

Spread ≤ 10% of mid, open interest ≥ 500, contract volume ≥ 100. At $1–2 premiums, the spread rule binds constantly: a $0.15 spread on a $1.50 contract is a full 10% boundary case, and you pay it twice. Always work limit orders at or near mid; walking a nickel toward the ask beats crossing an 8% spread at market. On free/indicative data (Technical Watch names), *none* of this is verifiable outside the broker — verify live, or the trade doesn't exist.

---

# 10. Layer 5: Sizing And Portfolio Rules

```text
Per trade:     ≤ 5% of account in premium — a CEILING, not a target
Standard S:    4–5%
Standard A+:   3–4%
Concurrent:    ≤ 4 open positions
Correlation:   same-sector / same-theme names count as ONE position slot
Total at risk: ≤ 15–20% of account in open premium at any moment
```

**The ceiling logic:** Section 2's streak table is calibrated to 5%. Sizing to 7% "because this one is special" doesn't make the special trade win more often — it makes the scheduled 8-loss streak cost 28% instead of 20%. There are no special trades. There is only the distribution.

**The correlation rule is the one that saves you:** three calls on three semiconductor names is one trade on the semiconductor index paying three commissions. When the sector reverses, all three hit −50% stops in the same session — a hidden 15% position masquerading as diversification. One name per theme, longs and shorts counted separately. If two S tiers appear in one sector, take the better contract (delta-band fit, IV rank, spread) and let the other go.

**Drawdown circuit breakers:**

```text
−15% from equity high:  size floor — every position drops to 3% max
−25% from equity high:  full stop — no new trades for 5 sessions;
                        audit every trade in the drawdown against this manual.
                        Rule-following losses → variance → resume at 3%.
                        Rule-breaking losses → the problem was never the system.
```

---

# 11. Layer 5: Trade Management — The Five Hard Rules

Entry gets you into the distribution. Management is what makes the distribution profitable. These five rules are mechanical — no judgment, no context, no exceptions:

```text
1. HARD STOP:    −50% of premium → exit immediately. Not −55 "to give it room."
2. TIME STOP:    2–3 days without meaningful progress toward target → exit,
                 regardless of P&L. Flat is a loss with the clock running.
3. SCALE:        +100% on premium → sell half. Mandatory. The banked half
                 pays for roughly two average losers.
4. RUNNER:       remaining half runs toward the chart target with a trailed
                 stop at breakeven-on-premium, tightened to 4H structure
                 (under higher lows for calls; above lower highs for puts).
5. FORCED EXIT:  5 DTE → close or roll (a roll is a new trade requiring
                 full re-qualification).
```

## Two Stops, First One Wins

The chart stop still exists — a support break (calls) or resistance reclaim (puts) is an immediate exit even at −20%. But it cannot be the *only* stop, because on a short-dated OTM contract the premium routinely hits −50% before the chart level breaks. The −50% stop protects you from the option's clock; the chart stop protects you from the stock. **Whichever fires first wins.** Both firing on the same candle means the setup failed completely — exit at market and journal it. And never, under any framing, move either stop to "give it room." A stop is a decision made while you were sane.

## What "Meaningful Progress" Means

By end of day 2 in the position, price should have moved at least ~one-third of the distance from entry to target, or be pressing the trigger with volume after a clean retest. "It hasn't gone against me" is not progress — a sideways short-dated OTM position has lost 25–35% while you waited for the stock to make up its mind. The AS Momentum SIGNAL AGE row turns orange at 6 four-hour bars (~3 trading days) for exactly this reason: the time stop is on your screen so it cannot be forgotten. *The most common way this profile loses money is not being wrong — it is being early, slowly.*

## The Runner's Exit

The runner half exits on the first of: chart target reached (take it — targets are targets), trailing structure break, +250–300% (take at least half of the runner; parabolic marks decay fast), or 5 DTE. Never let a +200% runner round-trip below +100%; the trailed breakeven-on-premium stop makes that structurally impossible if you actually place it. Place it.

---

# 12. The Four Playbooks

## Playbook A — Bullish Breakout Continuation

```text
Chart:    S/A+ | Breakout confirmed with volume expansion | not extended
Timing:   completed 4H close above trigger, HTF gate passed
Contract: 14–21 DTE, 0.25–0.35Δ call, strike ≈ trigger + half the run to target
IV note:  you are paying the breakout IV pop — demand IV Rank < 50 and skip
          if the entry candle itself visibly spiked IV
Kill it:  close back below the breakout level = failed breakout = exit now,
          don't wait for −50%
```

## Playbook B — Bullish Pullback (The Best Call-Side Contract Prices)

```text
Chart:    S/A+ | Pullback setup: support touched, held, green close, above AVWAP
Timing:   4H momentum turning up from support; entry on 4H higher-low
          confirmation or trigger reclaim
Contract: same band — IV has cooled during the dip; same stock, cheaper vega.
          Systematically the superior call entry.
Kill it:  daily close below the pullback support = setup dead at any P&L
```

## Playbook C — Bearish Rejection (The Best Contract Prices, Period)

```text
Chart:    put-side S/A+ | rally into falling MA / resistance / AVWAP from
          below, rejected with a red close | relative weakness leading
Timing:   4H lower-high confirmed at resistance, bear HTF gate passed
Contract: 14–21 DTE, 0.25–0.35Δ put, strike ≈ trigger − half the run to target
IV note:  THE structural edge — you own vega before the panic prices it.
          Buying fear wholesale.
Kill it:  close back above the rejection resistance = thesis dead
Manage:   bounces are violent; obey the −50% stop without a heartbeat of
          hesitation, and respect floored targets — downside overshoot is
          less reliable than it looks
```

## Playbook D — Bearish Breakdown (Valid, But You're Buying Retail)

```text
Chart:    put-side S/A+ | completed close below the breakdown level with volume
Timing:   4H close below trigger; never after 40% of the move is gone
Contract: same band — but breakdown candles spike IV 30–50%. Take it only
          when IV Rank was low BEFORE the break, or on the first orderly
          retest of the breakdown level from below (IV cools on the retest —
          the put-side equivalent of Playbook B).
Kill it:  reclaim of the breakdown level = failed breakdown = short-covering
          fuel = exit immediately; this is the fastest-reversing pattern
          in the book
```

---

# 13. Scenario Training

**Scenario 1 — The system working.** S tier, Command 88, 4H closes above trigger on volume. 17 DTE 0.31Δ call at $1.80, IV Rank 38, 4.5% position. Day 2: +105% → half sold. Day 5: target hit, runner out at +240%. *Total: ~+8% of account. Note what you did between entry and exit: nothing. The rules did everything.*

**Scenario 2 — Right stock, dead contract.** A+ pullback entry; support holds beautifully… sideways. Day 3, stock down 0.3%, contract −38% on pure theta and vega. Time stop: **exit.** The stock breaks out on day 6 and you feel robbed. Run the counterfactual honestly: the contract was at −55% by day 5 — the "robbery" saved you money, and re-entry on day 6's fresh trigger was always available. *The time stop is the rule you will hate most and need most.*

**Scenario 3 — The streak.** Trades 31–37: seven consecutive stopped losses, −18% from equity high, every trade rule-clean. The audit says variance. The −15% breaker drops sizing to 3%. Trade 38 is an S tier semi and you want to skip it — "nothing works right now." Section 2: the year lives in 5–8 winners and this could be one. **Take the trade at 3%.** It doubles. The streak math was never broken. *Skipping trade 38 is how profitable systems produce losing traders.*

**Scenario 4 — The IV trap.** Breakdown closes −6% on huge volume, put-side S tier fires. IV Rank 81. The setup is real; the contract is poisoned — at 0.30Δ the premium is double normal. **Pass. Set the alert for the retest.** Two days later price rallies back to the breakdown level, IV Rank 52, a rejection forms — Playbook C entry at nearly half the vega cost, better strike, tighter invalidation. *The chart and the contract are separate qualifications, and the market pays patience on the put side.*

**Scenario 5 — Correlation wearing a disguise.** Monday's scan: three S tiers, all AI-semiconductor names. The greedy read: three great trades. The rule: one theme, one slot. Rank by contract quality (IV rank, spread, delta-band fit), take the best, set alerts on the others. Wednesday: sector-wide reversal on one bad guidance report; the position stops at −2.5% of account. All three would have been −7.5%. *The correlation rule pays for this manual annually.*

**Scenario 6 — The 5 DTE seduction.** Runner at +160%, target 2% away, position touches 5 DTE. "Two more days and it tags it." **Close it.** +160% banked. If the thesis is truly alive, a fresh 16 DTE contract re-qualifies as a new trade tomorrow. Inside 5 DTE the position stops being your system and becomes a coin flip with rent due hourly.

**Scenario 7 — HTF blocked.** A 4H chart prints a textbook bear flag breakdown, score 78, gorgeous. The panel reads "HTF blocked" — daily RSI is 54 and MACD just crossed bullish. **No trade.** The daily chart owns the thesis; the 4H chart only times it. Fighting the higher timeframe with a short-dated contract is paying theta to argue with the trend. *When the gate says blocked, the answer is not "smaller size." The answer is no.*

---

# 14. Failure Modes — How This System Actually Dies

Ranked by body count, not by drama:

1. **Selection creep.** B tier "close enough" trades. Each one nudges the 35% win rate toward 28%, and Section 2's math goes quietly negative over months. The screener gates exist so this is a choice, not an accident. *Defense: S/A+ only is definitional — a B tier trade isn't a worse trade in this system, it isn't a trade in this system.*
2. **Impatient profit-taking.** Whole position off at +40–60%, repeatedly. Feels disciplined; produces a negative-expectancy system (Section 2 shows the exact arithmetic). *Defense: half at +100% is mandatory, the runner's stop is placed not intended, and the journal tracks "runner P&L given up" as its own column.*
3. **Streak psychology.** Skipping qualified signals mid-streak (missing the recovery winners), then revenge-oversizing after (meeting the next streak at 10%). *Defense: the circuit breakers are the only sanctioned size changes. Every S/A+ gets taken.*
4. **Stop negotiation.** −50% becomes −65% "because support is right there." The stop's whole function is to fire *before* the chart proves anything — that is the design, not a flaw. *Defense: it is a standing order placed at entry, not a decision made at −48%.*
5. **Theta denial.** Holding flat positions past the time stop because "nothing bad happened." A slow bleed across many positions, invisible on any single one. *Defense: the SIGNAL AGE row is on the chart and the day-2 progress check is a calendar event. Literally schedule it.*
6. **Regime blindness.** Running the call book hard into a deteriorating tape because individual charts still look fine. A hostile regime blocks call-side S tier for a reason — respect what that's telling you, and remember the put book exists precisely for those tapes.

---

# 15. Routines

## Nightly (after the screener's prep message)

1. Read the S/A+ lists — both directions. For each: pull it up in the two-pane layout, verify the chart with your own eyes, locate *real* support/resistance (never outsource this to the synthetic target), and pre-write the plan: trigger, strike, delta, DTE, IV rank, max premium, stop, time-stop date, target.
2. Read Technical Watch and B tier for tomorrow's promotions. Set alerts at their triggers.
3. Scan the rejection codes for your open names — a held position whose underlying just went `Rejected` is management information tonight, not tomorrow.
4. Check open positions against the calendar: DTE remaining, time-stop dates, signal age, earnings creep.

## At Entry (90 seconds, every time)

The one-sentence thesis, said fluently or the order doesn't go in:

> "I'm buying the [ticker] [strike][C/P] [exp] at [premium] because [S/A+ + playbook], delta [x], IV rank [x], stop −50% = [$], time stop [date], half off at [2× premium], runner target [level], max account risk [x]%."

## Weekly Review

Process-versus-outcome tagging on every trade, including skips that later worked. Track: win rate by playbook (A/B/C/D), average winner (holding ≥ +150%?), average loser (holding ≤ −55%?), runner P&L given up, time-stopped trades that later worked (expect some — the rule is still right), correlation slots respected Y/N, current drawdown versus the breakers. **If the average winner sags below +120% or the average loser swells past −60% for 20+ trades, the system is drifting — find which of the five rules is being negotiated. It is always one of the five.**

---

# 16. Drills And Mastery

**Drill 1 — Streak inoculation.** Simulate 100 trades at 35% / +150% / −55% with a coin-flip script or dice. Watch real 6–8 loss streaks appear inside a profitable sequence. Repeat until a live streak feels like weather, not verdict.

**Drill 2 — Chain fluency.** Ten nights running: pick one S/A+ name, open the chain, find the 0.25–0.35Δ strikes at 14–21 DTE, compute the research strike by hand, and articulate any disagreement (elevated IV? overrun target?). Under three minutes = fluent.

**Drill 3 — Mark-to-market intuition.** For one contract, write down what it should be worth if the stock reaches the strike in 3 days versus 8 days, and if it sits still for 3 days. Check against an options calculator. Repeat until your estimates land within 20%. This drill is what makes the time stop feel obvious instead of cruel.

**Drill 4 — Put-side IV reps.** Find five past breakdown candles in your universe. Note IV before, at, and 3 days after each break. Price the hypothetical 0.30Δ put at each moment. Watch the retest entry beat the breakdown chase in four of five — now Playbook D's caution is a scar you got for free.

**Drill 5 — The kill-list recital.** From memory, cold: the five hard rules, the four playbook kill conditions, the two circuit breakers, the 5 DTE rule, the earnings rule, and the correlation rule. These fire in moments when you will not want to think. That is precisely why they must not require thinking.

**The mastery standard:** you are ready for full size when you can (1) run 20 consecutive paper or minimum-size trades with zero rule violations — outcomes irrelevant, (2) explain to another trader *why* the half-at-+100% rule is load-bearing using the actual arithmetic, and (3) name, without looking, which failure mode in Section 14 is most likely to be *yours*. Everyone has one. Knowing yours is the difference between reading this manual and being governed by it.

---

# 17. The Cheat Sheet

## Enter Only When Every Line Is True

```text
□ Screener grade S or A Plus (this direction), verified on chart by eye
□ Playbook A, B, C, or D trigger on a COMPLETED 4H candle — happening now
□ HTF gate passed (never trade "HTF blocked" at any size)
□ ≤ 40% of the move to target already gone
□ 14–21 DTE, no earnings inside the window
□ Delta 0.25–0.35, research strike agrees (or you know exactly why not)
□ IV Rank < 50 (50–70 only for S tier, eyes open)
□ Spread ≤ 10% of mid, OI ≥ 500, volume ≥ 100 — verified LIVE in broker
□ Daily ATR% ≥ 2.0 (the ATR FLOOR row is green)
□ ≤ 5% of account premium | ≤ 4 positions | theme slot free | ≤ 20% total at risk
□ Written: stop, time-stop date, scale point, runner plan, kill condition
□ One-sentence thesis said fluently
```

## While In The Trade

```text
−50% premium ............ OUT, immediately
Kill condition hit ....... OUT, at any P&L
Day 2–3, no progress ..... OUT (time stop — the SIGNAL AGE row is watching)
+100% .................... HALF OFF, runner stop to breakeven, trail 4H structure
Chart target ............. take it
5 DTE .................... OUT, or a fully re-qualified roll
```

## The Standard

An expert in this system can explain why a setup passes, why the contract is priced fairly, what the position should be worth in three days if nothing happens, which of the five rules is currently closest to firing, and why the losing streak they are in right now changes nothing. Aggression here is not an emotion and not a personality. It is a payoff structure — purchased with discipline, one rule at a time, on both sides of the market.

---

*Ali Swing Suite — Aggressive Profile. Enforced by SwingSuiteScreener (aggressive contract profile: 14–21 DTE, 0.25–0.35Δ, movement filter, both directions) and the AS Command / AS Momentum v2 TradingView indicators. Educational use only — not financial advice. Long options routinely expire worthless; never trade this profile with money whose loss would change your life.*
