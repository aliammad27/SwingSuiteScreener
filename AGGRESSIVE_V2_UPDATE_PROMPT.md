# Aggressive Contract Profile v2 — Screener Update Prompt

Paste everything below this line into Claude Code inside the SwingSuiteScreener repo,
or just tell Claude Code: "Follow AGGRESSIVE_V2_UPDATE_PROMPT.md".

---

I'm updating SwingSuiteScreener to an aggressive contract profile (v2). I explicitly
approve these changes to the strategy configuration and the CLAUDE.md spec.

## Scope guard — read first

Do NOT change any of the following. The stock-selection layer stays byte-for-byte
identical:

- Command Score math or components (calls or puts)
- Momentum scoring, RSI/MACD logic, higher-timeframe filters
- S tier, A Plus, Technical Watch, or B tier requirement lists
- Automatic rejection logic (except adding the two new reason codes below)
- Universe rules, data quality rules, market regime logic
- Notification deduplication, state tracking, scheduling, Telegram delivery
- Earnings blackout (stays 7 days, `allow_earnings_event_trades: false`)

Only the options contract layer changes, plus one new movement filter.

## 1. `config/strategy.yaml`

```yaml
preferred_dte_target_minimum: 14
preferred_dte_target_maximum: 21
preferred_dte_hard_minimum: 10
preferred_dte_maximum: 25
preferred_delta_minimum: 0.25
preferred_delta_maximum: 0.35
delta_hard_floor: 0.20        # new key
```

- `delta_hard_floor`: any contract below 0.20 absolute delta is classified Poor
  liquidity regardless of other checks.
- Keep spread (10% of mid), open interest (500), contract volume (100), and
  earnings blackout settings unchanged.

## 2. Call side — `scanner/entry_plan.py`

- `PREFERRED_DTE_MINIMUM = 14`, `PREFERRED_DTE_MAXIMUM = 21`
- `INTENDED_HOLD_DAYS_MINIMUM = 3`, `INTENDED_HOLD_DAYS_MAXIMUM = 7`
- Replace `research_call_strike(trigger)` with an OTM placement:
  `research_call_strike(trigger, target)` returning
  `trigger + 0.5 * (target - trigger)` rounded UP to the strike increment.
  Keep the existing `_strike_increment` table.
- Label clearly in models and reports: this is a research strike that must be
  validated against a 0.25–0.35 delta band in the broker. The delta band is
  primary; the computed strike is a sanity check.

## 3. Put side — `scanner/put_entry_plan.py`

- `PREFERRED_DTE_MINIMUM = 14`, `PREFERRED_DTE_MAXIMUM = 21`
- `INTENDED_HOLD_DAYS_MINIMUM = 3`, `INTENDED_HOLD_DAYS_MAXIMUM = 7`
- Replace `research_put_strike(price)` with the mirrored OTM placement:
  `research_put_strike(trigger, target)` returning
  `trigger - 0.5 * (trigger - target)` rounded DOWN to the strike increment.
- Same labeling: research strike only, validated against a 0.25–0.35 absolute
  delta band; `delta_hard_floor: 0.20` applies to puts too.
- Keep the existing 22%-below-trigger target floor.

## 4. New movement filter (calls and puts)

Add to `scanner/entry_plan.py` / `scanner/put_entry_plan.py` (or one small shared
module), applied before grading:

- `required_move_percent` = percent move from current close to the research
  strike, plus an assumed premium cushion of 1.0% of the underlying price.
  (Calls: close up to strike. Puts: close down to strike.)
- Requirement A: `target_gain_percent >= 1.5 * required_move_percent`
- Requirement B: daily ATR percent >= 2.0
- When either fails, the candidate cannot be S tier or A Plus. It may still
  appear as B tier / watch.
- New rejection reason codes: `insufficient_movement_capability` and
  `atr_percent_below_floor`. Wire them into `automatic_rejections` in
  `scanner/grading.py` (and the put grading equivalent) via the rejection
  reasons list — do not modify the tier requirement lists themselves.

## 5. Reports and Telegram templates

- Every occurrence of "DTE Window: 45-60", "Preferred DTE range: 45-60",
  "Hold Window: 5-14 days" (and the put-side 45-70 equivalents) becomes
  "DTE Window: 14-21", "Preferred DTE range: 14-21", "Hold Window: 3-7 days".
- Add one management footer line to S tier and A Plus records (calls and puts):

```text
Management: -50% premium hard stop | 2-3 day time stop | sell half at +100% |
exit or roll by 5 DTE | max 5% of account per trade | max 4 concurrent
positions, correlated sector names count as one
```

## 6. `CLAUDE.md` spec update

Update sections 14 (option liquidity defaults), 17 (entry plan), and 21
(notification format) to reflect: new DTE window, delta band, delta hard floor,
hold window, OTM research strike formulas (both sides), and the movement filter.
Add a changelog note: "aggressive contract profile v2 — approved by user;
stock-selection gates intentionally unchanged."

## 7. Tests

Update existing DTE/strike/entry-plan tests (calls and puts) for the new
constants and strike formulas. Add new tests:

- Movement filter boundaries: target_gain exactly at 1.5x required move;
  ATR percent exactly at 2.0 (both sides of each boundary).
- Call research strike rounds UP and lands strictly between trigger and target.
- Put research strike rounds DOWN and lands strictly between target and trigger.
- Delta hard floor causes Poor classification.
- New rejection reason codes appear in JSON output.
- S tier, A Plus, Technical Watch, and B tier threshold lists are unchanged
  (calls and puts).

Run the full test suite, ruff, and mypy. Automated tests must not send real
Telegram messages.

## Build order

1. Config changes (item 1) + config validation.
2. Call entry plan (item 2), then put entry plan (item 3).
3. Movement filter + rejection codes (item 4).
4. Reports/templates (item 5).
5. CLAUDE.md (item 6).
6. Tests (item 7), then full suite + ruff + mypy green.
7. Commit: `feat: aggressive contract profile v2 (14-21 DTE, 0.25-0.35 delta OTM, movement filter)`
8. Push per the repo's git workflow.

## Post-run sanity checks (manual)

- A generated report shows the call research strike above trigger and below
  target; put research strike below trigger and above target.
- A slow megacap with a 90 Command Score shows
  `insufficient_movement_capability` or `atr_percent_below_floor` in rejected
  output instead of reaching the trade tiers.
- Telegram/report templates show 14-21 DTE and the management footer.
- Earnings blackout still rejects a candidate with earnings inside 7 days.
