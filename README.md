# SwingSuiteScreener

SwingSuiteScreener is the read-only research implementation of **Bullish
Participation v4**. It scans liquid U.S. stocks and index ETFs for bullish daily
setups, confirms timing on completed four-hour candles, and evaluates actual call
contracts without connecting to a brokerage account or placing orders.

The system is designed for research prioritization. A review state is not a
recommendation, probability, or performance forecast.

## What V4 Produces

Every scan creates:

- `latest.md`: human-readable audit report
- `latest.json`: structured evidence and contract payload
- `latest.html`: self-contained responsive screener dashboard
- Telegram digest and candidate summaries when configured
- research-ledger records for later outcome evaluation

Output folders follow the scan type under `reports/`.

## Strategy Lanes

| Lane | Symbols | Preferred DTE | Hard DTE | Preferred Delta | Intended Hold | Requalify |
|---|---|---:|---:|---:|---:|---:|
| Index Core | SPY, QQQ | 45-90 | 30-120 | 0.60-0.75 | 10-30 sessions | 30 DTE |
| Leader Swing | Curated liquid leaders | 30-60 | 21-75 | 0.45-0.65 | 5-15 sessions | 21 DTE |

All other thresholds are defined in `config/strategy.yaml` and loaded through
`scanner/strategy_profile.py`.

## Review States

- **Ready**: chart, market, event, risk, and trustworthy contract evidence pass.
- **Ready - Verify**: chart evidence passes, but an event or contract item still
  needs confirmation.
- **Verify Contract**: chart evidence passes while the option feed is indicative or
  otherwise insufficient for a contract decision.
- **Developing**: bullish geometry exists but one or more chart gates are incomplete.
- **Rejected**: a hard protection failed or the setup does not qualify.

Scores rank evidence. They do not estimate win probability.

## Bullish Pattern Library

The daily engine evaluates:

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

Every pattern uses the same forming, ready, confirmed, failed, and stale lifecycle.
Only completed candles can change a pattern state.

## Local Setup

Python 3.12 is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

For live scans, add read-only Alpaca market-data credentials and Telegram credentials
to `.env`. OPRA is required for a fully trustworthy contract state. The free
indicative option feed remains useful for chart research but always requires live
broker verification.

`MASSIVE_API_KEY` is optional and reserved for historical option research. Without
point-in-time historical option quotes, the project can evaluate underlying behavior
and forward paper evidence, but it cannot claim that long-call parameters are
validated after bid/ask costs.

## Commands

```bash
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan four_hour --fixture
python -m scanner.run_scan replay --fixture --symbol SPY --horizon 10
python -m scanner.run_scan evaluate-signals --fixture
python -m scanner.run_scan research-report
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan readiness_check
python -m scanner.run_scan release-audit
```

Fixture output is simulated and explicitly labeled as not current market data.

## Dashboard

Open the HTML produced by a fixture scan:

```bash
open reports/post_close/latest.html
```

The dashboard is self-contained and supports:

- review-state segmented filters
- symbol, sector, lane, and pattern search
- lane filtering
- market regime and breadth summary
- dense candidate comparison
- per-candidate evidence bars
- trigger, support, invalidation, and planning-objective levels
- selected contract and liquidity detail
- event status and pending checks
- rejected diagnostics
- mobile and print layouts

No server is required.

## Pine V6 Suite

- `AS_Command_1D_v4.pine`: daily trend, leadership, market proxy, the complete
  bullish pattern library, levels, review state, screener plots, and alerts.
- `AS_Momentum_4H_v4.pine`: four-hour RSI/MACD timing, confirmed daily filter,
  divergence warnings, reaction levels, screener plots, and alerts.

Both scripts use confirmed higher-timeframe values. Pine constants shared with the
Python strategy are checked by:

```bash
python scripts/check_pine_parity.py
```

TradingView must compile the scripts in Pine Editor before use. Script code exposes
alert conditions; the user still creates and activates alerts in TradingView.

## Research Standard

The current research stack has three levels:

1. **Sequential underlying replay**: proves signal generation uses only data
   available at each historical cutoff.
2. **Forward research ledger**: records signal, contract, config hash, and future
   observations without silently changing thresholds.
3. **Point-in-time long-call simulation**: uses historical bid/ask quotes,
   conservative fills, commissions, stale-quote rejection, same-bar pessimism,
   event exits, DTE requalification, and chronological walk-forward folds.

Research can make a parameter eligible for forward shadow validation. It never
automatically changes production configuration.

The complete optimization and release protocol is in
`docs/Bullish_Participation_v4_Build_Plan.md`.

## Safety Boundaries

- market data only
- no account, position, order, exercise, or execution endpoints
- no secret output
- no incomplete candles
- no event trade when earnings risk is blocked
- no fully ready state from indicative option data
- no performance claims from fixture or underlying-only evidence
- full premium loss is always possible for a long call

Read the training manual before using the system:

- canonical source: `docs/Bullish_Participation_v4_Training_Manual.md`
- visually verified DOCX:
  `docs/Ali_Swing_Suite_Bullish_Participation_v4_Training_Manual.docx`

## Quality Gates

```bash
python -m pytest
python -m ruff check scanner tests scripts
python -m mypy scanner
python scripts/check_pine_parity.py
python scripts/release_audit.py
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan post_close --fixture
```
