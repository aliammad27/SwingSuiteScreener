# Changelog

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
