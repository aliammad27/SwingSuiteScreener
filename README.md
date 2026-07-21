# SwingSuiteScreener

SwingSuiteScreener is the read-only research implementation of **Bullish Weekly
Participation v5**. It evaluates fast bullish continuation setups on daily charts,
confirms timing on completed 60-minute bars, and researches short-duration call
contracts without connecting to a brokerage account or placing orders.

V5 launches in `research_default`. A technically complete candidate remains
`Ready - Verify` until the historical and forward-shadow promotion gates pass.
Review states rank evidence; they are not recommendations, probabilities, or
performance forecasts.

## Strategy Lanes

| Lane | Universe | Preferred DTE | Hard DTE | Preferred Delta | Intended Hold | Requalify |
|---|---|---:|---:|---:|---:|---:|
| Index Weekly | SPY, QQQ | 10-16 | 7-21 | 0.60-0.75 | 1-4 sessions | 5 DTE |
| Leader Weekly | Liquid weekly-options leaders | 14-21 | 10-24 | 0.55-0.70 | 1-5 sessions | 7 DTE |

Leader candidates require price of at least $20 and 20-session average dollar volume
of at least $100 million. Zero through six DTE contracts are excluded. A nonstandard
weekly expiration is preferred unless a standard monthly expiration inside the same
lane window has materially stronger liquidity.

All thresholds are defined in `config/strategy.yaml` and loaded through
`scanner/strategy_profile.py`.

## Workflow

The scanner is deliberately staged:

1. Evaluate market regime, daily trend, leadership, production pattern, and completed
   hourly timing across the universe.
2. Check trusted event data for technical finalists.
3. Fetch option chains only for event-clear finalists.
4. Rank eligible contracts, re-quote the top three, and classify from refreshed data.

The daily chart owns trend, pattern, structural invalidation, confirmed pivot, and 2R
planning objective. A completed 60-minute bar owns EMA9/EMA21, session VWAP, RSI,
MACD histogram, relative volume, higher-low/reclaim structure, tactical levels, and
intraday SPY/QQQ confirmation.

New-entry timing is open from 10:30 AM through 2:45 PM ET. The scheduled 3:35 PM ET
scan is management-only.

## Production Patterns

- controlled pullback
- confirmed breakout
- bull flag
- breakout retest
- flat base
- VCP / tight base
- ascending triangle

The Pattern Atlas also displays cup with handle, double bottom, inverse head and
shoulders, falling wedge, and rounding base as context-only patterns. They cannot
qualify production candidates until held-out evidence promotes them.

Shared lifecycle defaults:

- ready within 0.30 ATR
- maximum confirmed extension of 0.75 ATR
- maximum confirmed age of one daily bar

## Data Requirements

A fully trusted evidence set requires:

- SIP stock data
- OPRA option data
- option quote age of two minutes or less
- stable refreshed quotes
- fresh event-source timestamps
- Massive Benzinga earnings when entitled
- official Federal Reserve and U.S. BLS macro calendars

Index contracts require spread at or below 3%, open interest of at least 2,000,
volume of at least 500, bid/ask size of at least 10, and daily theta at or below 5%
of ask.

Leader contracts require spread at or below 5%, open interest of at least 1,000,
volume of at least 200, bid/ask size of at least 5, and daily theta at or below 6%
of ask.

Missing, stale, or unknown event evidence fails closed.

## Local Setup

Python 3.12 is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Add read-only market-data and notification credentials to `.env`. SIP and OPRA
entitlements are required for full trust. `MASSIVE_API_KEY` is used for entitled
earnings and point-in-time historical option research.

## Commands

```bash
python -m scanner.run_scan intraday --fixture --scenario ready
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan replay --fixture --symbol SPY --horizon 5
python -m scanner.run_scan evaluate-signals --fixture
python -m scanner.run_scan research-report
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan readiness_check
python -m scanner.run_scan release-audit
```

Fixture output is simulated and explicitly labeled as not current market data.

## Dense Screener Workspace

Each scan writes Markdown, JSON, and a self-contained HTML workspace under the
matching `reports/` folder. The HTML view includes:

- sortable candidate columns
- state, lane, pattern, DTE, and data-trust filters
- quote age, theta/ask, depth, spread, and refreshed-contract visibility
- side-by-side candidate comparison
- primary and alternative contracts
- tactical warning, tactical failure, structural invalidation, confirmed pivot, and
  2R objective
- precise event, chart, universe, and contract rejection diagnostics
- responsive desktop, tablet, mobile, and print layouts

No server is required:

```bash
open reports/intraday/latest.html
```

## Pine v6 Indicators

- `AS_Weekly_Command_1D_v5.pine`: clean daily overlay with trend averages, current
  trigger/invalidation, optional planning levels, quick insights, and alerts.
- `AS_Weekly_Timing_1H_v5.pine`: clean completed-hour overlay with EMA9, EMA21,
  VWAP, current tactical levels, quick insights, and management alerts.
- `AS_Bullish_Pattern_Atlas_1D_v5.pine`: current trigger/invalidation geometry for
  all twelve bullish patterns, with context-only patterns disabled by default and
  a compact pattern-insight panel in the bottom-right corner.

The TradingView package contains indicators only. It has no Pine Screener script
and no `strategy()` backtest. The separate Python/HTML research screener described
above is independent of these chart indicators.

The indicators use no custom labels, shapes, or historical badges. Each contains one
optional last-bar quick-insights table, enabled by default and removable through
`Settings > Inputs > Show quick insights`. Only current decision levels are drawn,
and optional pivot/2R planning lines are off by default. Full numeric evidence and
codes remain available in the Data Window.

Shared constants are checked by:

```bash
python scripts/check_pine_parity.py
```

TradingView must compile each indicator in Pine Editor before live use. The repository
can verify structure and parity, but alert creation and chart-specific visual review
remain TradingView actions.

## Research Firewall

Point-in-time long-call research aligns quotes strictly at or after the completed
hourly trigger, uses minute-sequenced underlying evidence, pessimistic ask/bid fills,
commissions, two-minute stale-quote rejection, purge/embargo folds, and
overlapping-position-aware metrics.

Promotion review requires:

- at least 150 held-out contracts per lane
- at least 40 held-out contracts per promoted pattern
- positive median results in at least 60% of chronological folds
- improvement over the frozen longer-DTE baseline
- acceptable concentration and drawdown
- neighboring-parameter stability
- pessimistic-fill resilience
- at least 45 calendar days and 50 new eligible shadow opportunities

Passing gates does not change configuration automatically.

## Safety Boundaries

- market data only
- no account, position, order, exercise, or execution endpoints
- no secret output
- no incomplete-candle decisions
- no leader entry through protected earnings risk
- no index entry through active FOMC, CPI, or Employment Situation windows
- no fully trusted state without SIP, OPRA, and fresh event data
- no performance claims from fixtures or underlying-only evidence
- a long call can lose its full premium

## Documentation

- build and validation plan:
  `docs/Bullish_Weekly_Participation_v5_Build_Plan.md`
- canonical training source:
  `docs/Bullish_Weekly_Participation_v5_Training_Manual.md`
- Google Docs-ready manual:
  `docs/Ali_Swing_Suite_Bullish_Weekly_Participation_v5_Training_Manual.docx`

The intended native document title is **Ali Swing Suite: Bullish Weekly Participation
v5 Training Manual**.

## Quality Gates

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
