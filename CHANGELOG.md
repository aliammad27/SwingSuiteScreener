# Changelog

## 3.0.0 - 2026-07-12

Bullish Participation profile.

- Changed the active screener to bullish-only operation and removed put commands from the CLI.
- Moved call research to 30-60 DTE and 0.45-0.65 delta, with 21-75 DTE hard bounds.
- Extended the planning window to 5-15 trading days and set re-qualification at 21 DTE.
- Replaced the distant OTM strike formula with a near-the-money research strike.
- Removed the minimum ATR and movement-capability gates that forced high-volatility names.
- Added pullback-first ranking and required a current trigger for the highest readiness state.
- Replaced user-facing tier language with Ready, Ready - Verify, Developing, and Verify Contract.
- Replaced universal premium-return management rules with underlying invalidation and time-based reassessment.
- Corrected synthetic target labeling: confirmed pivot resistance is used when available; otherwise the report says 2R planning objective.
- Centralized active contract settings in a typed strategy profile.
- Removed the duplicate 2,153-line specifications, obsolete aggressive prompt, and obsolete v2 training manual.
- Added a new Bullish Participation v3 Word training manual.

## 1.0.0 - 2026-06-19

- Built the version one deterministic Command Center and Momentum Engine.
- Added fixture and direct Alpaca provider surfaces.
- Added Telegram notification discovery, test messaging, retries, logging, and deduplication state.
- Added local JSON persistence and PostgreSQL-compatible production adapter surface.
- Added Markdown and JSON reports with fixture labeling.
- Added Docker, Render cron configuration, scripts, environment template, and cloud-readiness docs.
- Added automated tests for scoring, grading, notifications, reports, state, data quality, and no brokerage execution.

## 1.0.1 - 2026-06-19

- Added free-first mode for Alpaca Basic: IEX equities and indicative options.
- Added `Technical Watch` labeling when technical gates pass but paid-quality option liquidity is unavailable.
- Added local `.env` autoloading and a June 22, 2026 readiness check command.

## 1.0.2 - 2026-06-19

- Added free GitHub Actions scheduled automation for premarket, four-hour, and post-close scans.
- Added a manual GitHub Actions readiness workflow that validates secrets and sends a Telegram test.

## 1.0.3 - 2026-06-21

- Added a nightly 9 PM ET Telegram prep command for the next market session.
- Added a GitHub Actions workflow to send the nightly prep message automatically.
- Updated nightly prep to include strict-scan ticker lists and watch levels.
- Shortened nightly prep to a ticker-only watchlist format.
- Made the nightly Watch bucket strategy-based instead of showing the broad universe.
- Expanded the default live universe from 5 to 67 liquid optionable stock tickers.
- Added provider caching to reduce repeated market-data calls during larger scans.
- Added ranked reason lines, TradingView links, chart image attachments, and Sunday weekly radar.
- Expanded the live universe further to 161 liquid optionable stock tickers.
- Added an Eastern-time schedule gate and early GitHub Actions wakeups to reduce delayed market alerts.
- Added near-target backup wakeups and post-alert schedule holds to reduce missed alerts without duplicating texts.
- Added target stock prices, research call strikes, 45-60 DTE planning, and 5-14 day swing windows to alerts and reports.
- Added Alpaca 429/5xx retry throttling and made manual GitHub workflow runs bypass schedule gates.

## 2.0.0 - 2026-07-05

Aggressive contract profile v2 — approved by user; stock-selection gates intentionally unchanged.

- Moved the contract layer to a 14-21 DTE window (hard bounds 10-25) and a 0.25-0.35 absolute delta band.
- Added `delta_hard_floor: 0.20`; any contract below 0.20 absolute delta classifies as Poor liquidity.
- Replaced ATM research strikes with OTM placement: calls at `trigger + 0.5 * (target - trigger)` rounded up, puts at `trigger - 0.5 * (trigger - target)` rounded down.
- Shortened the intended hold window to 3-7 days.
- Added a movement-capability filter (target gain >= 1.5x required move including a 1% premium cushion, daily ATR percent >= 2.0) that blocks S tier and A Plus with reason codes `insufficient_movement_capability` and `atr_percent_below_floor`; B tier and watch remain reachable.
- Added a management footer to S tier and A Plus reports and Telegram messages.

## 2.0.1 - 2026-07-05

Notification clutter cleanup.

- Premarket and four-hour completion messages are now suppressed when nothing material changed since the previous run (per spec section 20); post-close still always sends.
- Nightly prep skips its chart attachments on days when the weekly radar already delivered them, removing the Sunday duplicate image burst.
- Backup GitHub Actions wakeups now skip cleanly when the primary scheduled run already succeeded, instead of failing red.
- Scanner state (`data/state`) now persists across GitHub Actions runs via a rolling cache so change detection works between scheduled jobs.
