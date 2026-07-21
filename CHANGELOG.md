# Changelog

## Unreleased

- Added Telegram contract research cards with the selected call strike, expiration,
  refreshed quote quality, underlying objectives, risk levels, and holding constraints.
- Added typed, quote-anchored premium scenarios that use delta, optional gamma, and
  theta to display an immediate-to-maximum-hold range while failing closed on stale,
  unstable, invalid, or non-OPRA contract evidence.
- Added chart-delivery text fallback, configurable card limits, and a compact
  Developing watchlist without changing grading, HTML/JSON output, Pine, or research
  persistence schemas.
- Completed the PostgreSQL/Supabase notification-state adapter and made
  `STORAGE_BACKEND` select the configured durable backend.
- Made local notification-state writes atomic and retry-safe: failed Telegram digests
  no longer suppress the next unchanged scan.
- Rejected future-dated event sources and option quotes instead of treating them as
  fresh evidence.
- Corrected FOMC protection to remain active through the first fully completed
  regular-session hour after the statement.
- Sanitized leader option-eligibility failures so provider response details cannot
  enter reports.
- Made hosted cron schedules DST-safe through Eastern-time gates, skipped live scans
  on non-NYSE sessions, and hardened the Docker image with a non-root runtime.
- Upgraded official GitHub workflow actions to their Node 24 generations.
- Reduced the TradingView package to three chart-analysis indicators: Daily Command,
  Hourly Timing, and the optional Daily Pattern Atlas.
- Removed the Pine Screener and underlying-proxy strategy tester from the active
  repository.
- Enforced an indicator-only Pine contract that rejects `strategy()`, custom labels,
  pattern badges, and shapes.
- Added one compact, optional, last-bar quick-insights table to each indicator:
  Daily state/setup/levels/next step, Hourly timing gates/momentum/risk/next step,
  and Atlas pattern geometry/context.
- Replaced full-history decision levels with short current-state line objects and
  made pivot/2R planning levels optional and off by default.
- Disabled context-only Pattern Atlas geometry by default and moved pattern,
  lifecycle, score, and state evidence into the Data Window.
- Added automated release checks that reject future chart markers and enforce
  exactly one controlled quick-insights table per indicator.
- Made every indicator history function unconditional so TradingView compiles the
  suite without calculation-consistency warnings.
- Corrected the Pine v6 one-day timeframe guard to `1D` and aligned same-timeframe
  SPY, QQQ, and leadership data to the completed source bar.
- Corrected the hourly tactical-failure level to the prior four completed hourly
  lows so a close-below failure alert can occur.

## 5.0.0 - 2026-07-16

- Replaced the active strategy with Bullish Weekly Participation v5 and launched it
  under `validation_state: research_default`.
- Added separate Index Weekly and Leader Weekly lanes with 7-24 DTE hard bounds,
  lane-specific delta, hold, requalification, liquidity, depth, and theta controls.
- Replaced slower timing with completed 60-minute EMA, VWAP, RSI, MACD, volume,
  structure, and intraday-index confirmation.
- Added seven production continuation patterns and retained five context-only patterns
  in the visual atlas.
- Added a two-stage scanner that fetches chains only for technical and event-clear
  finalists, then re-quotes the top three contracts.
- Added SIP, OPRA, quote-stability, event-source freshness, Massive earnings, and
  official Fed/BLS macro-event trust gates.
- Added separate tactical warning, tactical failure, structural invalidation,
  confirmed pivot, and 2R planning-objective fields.
- Rebuilt the HTML screener as a dense sortable, filterable, comparable operational
  workspace with contract alternatives and precise rejection diagnostics.
- Added three Pine v6 chart indicators for daily command, hourly timing, and the
  bullish pattern atlas.
- Upgraded historical option research with trigger-aligned quotes, minute sequencing,
  pessimistic fills, commissions, purge/embargo folds, overlap metrics, frozen
  baseline comparison, stability checks, and shadow gates.
- Migrated the research ledger in place to store hourly timing, trust provenance,
  level separation, depth, theta/ask, quote age, expiration style, and re-quote data.
- Replaced hosted refresh jobs with six daylight-saving-safe intraday windows,
  including a management-only final scan.
- Replaced the build plan, training manual, engineering contract, CI, release audit,
  and active documentation with v5 material. Earlier releases remain available in
  Git history.
