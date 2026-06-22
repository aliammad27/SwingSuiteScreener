# SwingSuiteScreener: Codex Product and Engineering Specification

## 0. Repository and Delivery Contract

Repository name: `SwingSuiteScreener`

Codex is responsible for building the complete version one application in this repository.

Git workflow:

1. Work directly on the repository's `main` branch unless the repository default branch has another name.
2. Inspect `git status`, the active branch, and the configured remote before editing.
3. Preserve useful existing files.
4. Never commit secrets, `.env`, credentials, generated caches, local databases, or raw private data.
5. Pull or fetch remote changes before the final push and resolve conflicts safely.
6. Do not use destructive Git commands, rewrite remote history, or force push.
7. After implementation and validation are complete, commit all intended source, configuration, tests, fixtures, documentation, and deployment files.
8. Use a clear commit message, such as `feat: build SwingSuiteScreener v1`.
9. Push the completed and tested implementation to `origin/main`.
10. If authentication or permissions prevent the push, leave the working tree committed and report the exact command and error needed to finish the push.
11. Do not stop after writing a plan. Continue through implementation, testing, documentation, commit, and push.
12. Do not create paid cloud resources or deploy live infrastructure without explicit user approval.

The connected Alpaca Codex plugin may be used only for read-only exploration and validation while developing. The production application must use a direct provider implementation and must not depend on Codex, MCP, or an interactive agent.

## 1. Mission

Build and operate `SwingSuiteScreener`, a disciplined bullish swing trading screener for liquid United States stocks with listed options.

The intended trade is a bullish call option swing held for several days to roughly two weeks.

The daily chart selects the stock.

The four hour chart times the entry.

The system must prioritize quality over quantity. Returning zero qualifying setups is better than lowering standards.

The system is a research and decision support tool. It must never place, route, modify, or cancel brokerage orders.

## 2. Operating Principle

Code calculates.

The research and reasoning layer investigates, verifies, compares, explains, and ranks.

The user authorizes every trade.

Do not use language model judgment to replace deterministic indicator calculations.

Do not estimate technical values from screenshots when structured market data is available.

Every technical value used in grading must come from code or a verified market data source.

Never fabricate prices, indicators, option data, catalysts, event dates, citations, or market conclusions.

## 2A. Finalized Strategy and Indicator Architecture

This specification reflects the finalized Ali Swing Suite.

The strategy is bullish only and is designed for call option swings held for several days to roughly two weeks.

Use exactly two analytical tools:

```text
AS Call Command 1D
AS Momentum 4H Overlay
```

The daily chart selects the trade.

The four hour chart times the entry.

Do not use timeframes below four hours for qualification or entry timing in version one.

### AS Call Command 1D

This tool is a daily price chart overlay.

Its trend components are:

```text
EMA 21
SMA 50
SMA 200
Monthly anchored VWAP
```

The EMA 9 is not part of the finalized Command Center and must not be used in its score, trend stack, grading, or reports.

The finalized bullish trend relationship is:

```text
EMA 21 above SMA 50
SMA 50 above SMA 200
```

The Command Center owns the daily chart levels, including:

1. Daily breakout trigger.
2. Daily pullback support.
3. Latest confirmed support.
4. Latest confirmed resistance.
5. Rising support trend line.
6. Falling resistance trend line.

### AS Momentum 4H Overlay

This tool is a price chart overlay, not a lower oscillator pane.

Its TradingView implementation uses:

```text
overlay = true
scale = scale.none
```

RSI 14 and MACD 12, 26, 9 are calculated internally.

RSI and MACD values are presented through the on chart status table and are not plotted as oscillator waves on the stock price axis.

The momentum visual on price is:

```text
Momentum colored EMA 21
Muted EMA 50 reference
Trigger line
Support line
Warning line
Automatic trend lines
```

Signal markers are off by default.

The momentum status table is currently configured in the top right corner. Table location is a display preference only and must never affect scanner calculations, setup grades, or notifications.

When used on a four hour chart, the automatic higher timeframe is the daily chart.

When used on a daily chart for the daily momentum thesis check, the automatic higher timeframe is the weekly chart.

Use only the last completed higher timeframe candle for filtering.

### Governing Workflow

The scanner must follow this order:

1. Daily Command Center selects technically valid stocks.
2. Daily momentum confirms or rejects the broader thesis.
3. Four hour momentum determines whether entry timing is valid.
4. Option liquidity, implied volatility, catalyst, event risk, and market regime determine whether the trade is practical.
5. The user authorizes every trade.

A four hour bullish signal cannot rescue a failed daily setup.

Removing the lower pane changes display only. It does not change RSI, MACD, momentum scoring, higher timeframe filtering, triggers, support, warnings, or alerts.

### Final Go or No Go Checklist

Daily selection requires:

```text
Daily Command Score at least 75
Call Bias is Bullish, Breakout confirmed, or Pullback setup
Daily trend is an uptrend
Weekly alignment passed
Relative strength is leading
Price is above monthly anchored VWAP
Price is not extended
```

Daily momentum thesis check requires:

```text
Daily RSI at least 50
Daily MACD bullish or strengthening
Daily Overall state is not Warning active
```

Four hour timing requires:

```text
Four hour Momentum Score approximately 70 or higher
Higher timeframe filter passed
Overall state is Bullish or Strong bullish
Price closes above the active trigger, or holds active support with supportive volume
```

Hard avoids include:

1. Weak daily trend.
2. Price below major daily moving averages.
3. Relative strength lagging.
4. Price materially extended above EMA 21 or the upper Bollinger Band.
5. Four hour bullish momentum while the daily filter is blocked.
6. Insufficient distance to resistance.
7. Poor option liquidity.
8. Elevated implied volatility that makes the premium unattractive.
9. Unresolved earnings or event risk.

## 2B. Free First Operating Mode

The project should stay free unless the user explicitly approves a paid data, cloud, or database upgrade.

Default free mode uses:

```text
Alpaca Basic equities through IEX
Alpaca Basic options through the indicative feed
Telegram Bot API
Local JSON state
GitHub Actions scheduled execution
```

Free Alpaca data is useful but limited. IEX does not represent full consolidated SIP market coverage, and indicative options are not OPRA-quality executable option liquidity.

Therefore:

1. Do not label a live setup S tier unless current tradable option liquidity is Good.
2. Do not label a live setup A Plus unless option liquidity is Good or Acceptable.
3. When a setup passes technical gates but only indicative or unknown option data is available, label it Technical Watch.
4. Technical Watch means research-worthy, not trade-ready.
5. Technical Watch must include trigger, support, invalidation, and the exact missing option-liquidity reason.
6. Never lower S tier or A Plus thresholds to compensate for free data limitations.
7. Never represent indicative option quotes as current OPRA-quality liquidity.
8. Never recommend a specific option contract from indicative, stale, unknown, or incomplete option data.

Technical Watch may appear in reports and Telegram completion counts in free mode, but it is not S tier or A Plus.

Free automation should use GitHub Actions by default. Required repository secrets are:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

The scheduled workflows must not print secret values. They should run on GitHub-hosted Linux runners using the included GitHub Actions minutes quota and should upload generated reports as workflow artifacts.

## 3. Notification Decision

Use Telegram as the notification destination for version one.

Use the existing Telegram bot identity:

```text
Bot display name: Ali's Screener Bot
Bot username: AlisScreenerBot
Bot link: https://t.me/AlisScreenerBot
```

Do not create a second Telegram bot unless the user explicitly requests one.

All market scan messages must be sent to a private Telegram chat between the user and `@AlisScreenerBot`.

Telegram is the only remote notification provider required for version one.

A provider interface must still be used so Discord, email, Slack, or another provider can be added later without changing technical calculations or grading logic.

When Telegram delivery fails, write the failure to the notification log and attempt a local macOS notification when macOS is available.

Notification delivery failure must never change a stock grade.

The Telegram token is a secret. Never place a real token in `AGENTS.md`, source code, YAML, reports, logs, test fixtures, screenshots, prompts, or committed files. Load it only from the local `.env` file.

If a Telegram token has ever been pasted into a chat, issue, document, or other shared location, treat it as compromised and require the user to revoke and regenerate it through BotFather before enabling live notifications.

## 4. Required Project Structure

Create and maintain this structure:

```text
SwingSuiteScreener/
    AGENTS.md
    README.md
    CHANGELOG.md
    pyproject.toml
    requirements.txt
    .env.example
    .gitignore
    Dockerfile
    .dockerignore
    render.yaml
    config/
        strategy.yaml
        universe.yaml
        schedule.yaml
        notifications.yaml
        providers.yaml
        storage.yaml
    scanner/
        __init__.py
        config.py
        models.py
        clocks.py
        calendars.py
        data_quality.py
        universe.py
        indicators.py
        daily_command.py
        momentum.py
        structure.py
        option_liquidity.py
        catalyst_research.py
        market_regime.py
        grading.py
        entry_plan.py
        reports.py
        notifications.py
        state.py
        run_scan.py
        providers/
            __init__.py
            base.py
            alpaca.py
            fixtures.py
        storage/
            __init__.py
            base.py
            local_json.py
            postgres.py
    tests/
        fixtures/
        test_configuration.py
        test_data_quality.py
        test_indicators.py
        test_daily_command.py
        test_momentum.py
        test_structure.py
        test_scoring.py
        test_grading.py
        test_option_liquidity.py
        test_market_calendar.py
        test_notifications.py
        test_state.py
        test_reports.py
        test_no_execution.py
    data/
        raw/
        processed/
        state/
    reports/
        post_close/
        premarket/
        four_hour/
        archive/
        engineering/
    logs/
    scripts/
        run_post_close.sh
        run_premarket.sh
        run_four_hour_refresh.sh
```

Use Python with type hints.

Keep data retrieval, technical calculations, research, grading, reports, notifications, and state management in separate modules.

All configurable values must live in YAML files.

Never hardcode API credentials.

Use environment variables and provide an `.env.example`.


## 4A. Engineering Standards

Use Python 3.12 unless a dependency requires another supported version.

Use:

1. Type hints on public functions and core data models.
2. `pytest` for automated tests.
3. `ruff` for linting and formatting.
4. `mypy` for static type checking where practical.
5. `pydantic` or typed dataclasses for validated domain models.
6. Structured logging with secret redaction.
7. UTC timestamps internally and `America/New_York` for exchange scheduling and user-facing market times.
8. Dependency injection for market data, option data, research, notifications, and persistence.
9. Deterministic fixtures for all automated tests.
10. Clear exception types and fail-closed behavior for stale, incomplete, or ambiguous data.

Prefer `pyproject.toml` as the central tool configuration. Keep `requirements.txt` when it improves deployment compatibility.

Every public command must return a nonzero exit code on unrecoverable failure.

Automated tests must not require live Alpaca, Telegram, web, database, or cloud credentials.

## 5. Commands

Support these commands:

```text
python -m scanner.run_scan post_close
python -m scanner.run_scan premarket
python -m scanner.run_scan four_hour
python -m scanner.run_scan daily_prep
python -m scanner.run_scan test_notification
python -m scanner.notifications discover_chat_id
python -m scanner.run_scan validate_configuration
```

When the user or Codex task says:

```text
Run post close
```

Execute the complete post close workflow.

When the user or Codex task says:

```text
Run premarket
```

Execute the premarket validation workflow.

When the user or Codex task says:

```text
Run four hour refresh
```

Execute the four hour entry refresh.

When the user or Codex task says:

```text
Send daily prep
```

Run the strict scanner and send one Telegram preparation message for the next
market session. The message must include S tier, A Plus, and Technical Watch
ticker lists, or explicitly state that no tickers qualified. The message must
stay concise, avoid strategy instructions, not fabricate market data, not lower
standards, and not imply that any setup is trade-ready without verified option
liquidity.

When the user or Codex task says:

```text
Test Telegram
```

Send one clearly labeled Telegram test message without running a market scan.

When the user or Codex task says:

```text
Build version one
```

Inspect the repository, preserve useful existing work, implement the highest priority missing components, run tests, and report exactly what remains.

## 6. Schedule

Use the `America/New_York` timezone.

The scheduler must use the exchange calendar so runs do not occur on weekends or full market holidays.

### 6.1 Post Close Full Scan

Default time:

```text
4:20 PM America/New_York on regular trading days
```

Purpose:

1. Download completed daily and four hour market data.
2. Build the eligible universe.
3. Calculate the daily Swing Call Command Center.
4. Calculate daily momentum.
5. Calculate four hour momentum using the completed daily filter.
6. Remove weak, extended, illiquid, stale, and incomplete candidates.
7. Research catalysts and event risks for finalists.
8. Grade finalists.
9. Produce the next session watchlist.
10. Save calculations, reports, sources, and rejection reasons.
11. Always send one Telegram completion message.

### 6.2 Premarket Validation

Default time:

```text
8:45 AM America/New_York on regular trading days
```

Purpose:

1. Load the most recent post close finalists.
2. Check overnight company news.
3. Check SEC filings.
4. Check earnings updates and guidance.
5. Check analyst actions.
6. Check premarket gaps.
7. Check whether event risk changed.
8. Preserve valid candidates.
9. Demote or reject invalidated candidates.
10. Send Telegram only when something material changed or the run failed.

Do not run a complete universe scan during premarket unless explicitly requested.

### 6.3 Four Hour Entry Refresh

Default time:

```text
1:35 PM America/New_York on regular trading days
```

Purpose:

1. Load current S tier and A plus candidates.
2. Refresh completed four hour candles.
3. Recalculate four hour momentum.
4. Recalculate trigger, support, warning, trend line, and extension conditions.
5. Promote an A plus candidate only when every S tier requirement passes.
6. Demote or reject a candidate when support fails, the daily filter blocks, price becomes extended, or new risk appears.
7. Send Telegram only when something actionable or material changed.

Do not repeat deep catalyst research when no relevant news appeared.

### 6.4 Nightly Next-Session Prep

Default time:

```text
9:00 PM America/New_York every day
```

Purpose:

1. Send one Telegram preparation message for the next market session.
2. Run the strict scanner to produce S tier, A Plus, and Technical Watch ticker lists.
3. Keep the Telegram body short: date, S, A+, TW, and monitored tickers.
4. Explicitly state when no tickers qualify and standards were not lowered.
5. Include the broader monitored universe so the nightly message still contains tickers when no setup qualifies.
6. Use the exchange calendar to identify the next regular or half-day market session.
7. Keep it free and runnable from GitHub Actions.

Do not include fabricated tickers, market data, option data, catalysts, or earnings dates.
Do not describe Technical Watch as trade-ready.

## 7. Default Universe

Create `config/universe.yaml` with these defaults:

```yaml
country: US

security_types:
  - common_stock

options_required: true

minimum_price: 10

minimum_market_cap_usd: 1000000000

minimum_average_daily_dollar_volume_usd: 50000000

average_volume_lookback_days: 30

exclude_otc: true

exclude_penny_stocks: true

exclude_leveraged_etfs: true

exclude_inverse_etfs: true

exclude_shell_companies: true

exclude_missing_data: true
```

The universe may include liquid large cap and mid cap companies.

Reject any symbol with stale, incomplete, inconsistent, or improperly adjusted critical data.

## 8. Data Quality

Before scoring any stock:

1. Verify that the symbol is active.
2. Verify the market data provider.
3. Verify the retrieval timestamp.
4. Verify the market timezone.
5. Verify that daily candles are completed.
6. Verify that four hour candles are completed.
7. Verify that corporate actions are handled consistently.
8. Verify that benchmark data is available for matching timestamps.
9. Verify that volume data is present.
10. Verify the option chain timestamp.
11. Record the source and retrieval time.
12. Reject the candidate when critical data is missing.

Do not silently fill a missing value when doing so could alter a grade.

Do not use an incomplete daily or four hour candle as a completed candle.

All reports must display the market data timestamp.

## 9. Benchmarks

Default benchmark:

```text
QQQ
```

Broad market benchmark:

```text
SPY
```

Use QQQ by default for technology and growth stocks.

Use SPY when broad market comparison is more appropriate.

Record the benchmark used for each candidate.

## 10. Market Regime

Evaluate:

1. SPY daily trend.
2. QQQ daily trend.
3. Relevant sector ETF trend.
4. VIX condition when reliable data is available.
5. Major scheduled macro events during the expected holding period.

Classify the market regime:

```text
Supportive
Mixed
Hostile
```

A hostile regime normally blocks S tier.

Never invent macro event dates.

## 11. Daily Swing Call Command Center

Calculate all values using completed daily candles.

### 11.1 Moving Averages

Use:

```text
EMA 21
SMA 50
SMA 200
```

The EMA 9 was removed from the finalized Command Center.

Calculate:

1. Close above EMA 21.
2. EMA 21 above SMA 50.
3. Close above SMA 50.
4. SMA 50 above SMA 200.
5. Close above SMA 200.
6. SMA 200 above its value ten daily bars ago.
7. Full bullish stack, close above EMA 21, EMA 21 above SMA 50, and SMA 50 above SMA 200.

### 11.2 Monthly Anchored VWAP

Use monthly anchored VWAP by default.

Calculate:

1. Current anchored VWAP.
2. Price above or below anchored VWAP.
3. Percentage distance from anchored VWAP.

### 11.3 Relative Strength

Calculate:

```text
relative_strength_ratio = stock_close / benchmark_close
relative_strength_average = EMA 21 of relative_strength_ratio
```

Classify:

```text
Leading:
Ratio is above its EMA 21 and above its value five bars ago

Strong:
Ratio is above its EMA 21 but is not rising

Improving:
Ratio is below its EMA 21 but is rising

Lagging:
All other conditions
```

### 11.4 Volume

Calculate:

```text
relative_volume = current_volume / SMA 20 volume
```

Classify:

```text
Expansion:
Relative volume is at least 1.30

Above average:
Relative volume is at least 1.00

Normal:
Relative volume is at least 0.70

Light:
Relative volume is below 0.70
```

Bullish volume expansion requires volume expansion and a bullish candle.

### 11.5 Volatility

Calculate:

```text
ATR length: 14
ATR percent: ATR divided by close multiplied by 100
ATR percent average: SMA 50
Bollinger basis: SMA 20
Bollinger deviation: 2
Bollinger width average: SMA 50
```

Classify:

```text
Squeeze:
Bollinger width is below 75 percent of its average

High:
ATR percent is above 125 percent of its average

Low:
ATR percent is below 80 percent of its average

Normal:
All other conditions
```

### 11.6 Market Structure

Use confirmed pivots.

Daily defaults:

```text
Pivot left bars: 5
Pivot right bars: 3
```

Track the two latest confirmed pivot highs and pivot lows.

Classify:

```text
Bullish:
Higher high and higher low

Improving:
Higher high or higher low

Bearish:
Lower high and lower low

Mixed:
All other conditions
```

### 11.7 Breakout Level

Calculate:

```text
breakout_level = highest high of the previous 20 completed daily bars
```

Do not include the current bar.

Breakout watch is true when price is below the breakout level and within 0.50 ATR of it.

Breakout confirmed is true when a completed daily candle closes across the breakout level.

### 11.8 Pullback Support

Choose the nearest valid level below current price from:

1. EMA 21.
2. SMA 50.
3. Monthly anchored VWAP.
4. Latest confirmed pivot low.

Pullback touched is true when the daily low comes within 0.30 ATR of support.

Pullback held is true when the candle closes above support and closes at or above its open.

### 11.9 Weekly Alignment

Use only the last completed weekly candle.

Weekly alignment passes when:

```text
Completed weekly close is above weekly EMA 21
```

### 11.10 Daily Command Score

Use this exact deterministic scoring system:

```text
Close above EMA 21: 10
EMA 21 above SMA 50: 10
Close above SMA 50: 10
SMA 50 above SMA 200: 15
Close above SMA 200: 10
SMA 200 rising versus ten bars ago: 5
Relative strength leading: 15
Relative strength strong but not leading: 8
Price above monthly anchored VWAP: 10
Bullish volume expansion: 10
Volume above average without bullish expansion: 5
Bullish structure: 5
Improving structure: 3
Weekly alignment: 5
Maximum score: 100
```

### 11.11 Extended Price Rule

Mark a stock extended only when both conditions are true:

```text
Close is above the upper Bollinger Band
Close minus EMA 21 is greater than 1.50 ATR
```

An extended stock cannot receive S tier.

### 11.12 Daily Call Bias

Use these finalized states:

```text
Avoid:
Price below SMA 200 or Daily Command Score below 45

Extended:
Finalized extended price rule is active

Breakout confirmed:
Completed daily close crossed above the daily breakout level and the setup passes required trend conditions

Pullback setup:
Daily Command Score at least 70, pullback support was touched and held, and price is above monthly anchored VWAP

Breakout watch:
Price is within 0.50 ATR below the breakout level and Daily Command Score is at least 65

Bullish:
Daily Command Score is at least 75

Watch:
Daily Command Score is at least 60

Mixed:
All remaining non Avoid states
```

A high quality daily setup requires:

```text
Daily Command Score at least 75
Weekly alignment passed
Relative strength leading
Price above monthly anchored VWAP
Active breakout setup or pullback setup
Price not extended
```


## 12. Momentum Engine

Use the same core momentum engine on completed daily and completed four hour candles.

Do not calculate or use one hour, thirty minute, fifteen minute, five minute, or one minute signals for version one.

The daily chart is authoritative for selection.

The four hour chart is authoritative for timing.


### 12.1 Indicators

```text
RSI: 14
MACD: 12, 26, 9
```

Calculate:

1. RSI value.
2. RSI rising or falling.
3. MACD above or below signal.
4. MACD above or below zero.
5. Histogram rising or falling.

### 12.2 Momentum Score

RSI regime score:

```text
RSI at least 75: 20
RSI at least 60 and below 75: 30
RSI at least 50 and below 60: 22
RSI at least 40 and below 50: 10
RSI below 40: 0
```

Additional score:

```text
RSI rising: 10
MACD above signal: 25
MACD above zero: 20
Histogram rising: 15
```

Divergence adjustment:

```text
Recent confirmed bullish RSI divergence: plus 5
Recent confirmed bearish RSI divergence: minus 5
```

Warning penalty:

```text
Recent RSI cross below 50 or MACD bearish cross: minus 10
```

Score limits:

```text
Minimum: 0
Maximum: 100
MACD below signal maximum: 74
RSI at least 75 maximum: 84
```

### 12.3 Daily Momentum Defaults

```text
Warning penalty duration: 2 daily bars
Divergence influence duration: 8 daily bars
Divergence pivot left: 5
Divergence pivot right: 5
```

### 12.4 Four Hour Momentum Defaults

```text
Warning penalty duration: 3 four hour bars
Divergence influence duration: 10 four hour bars
Divergence pivot left: 5
Divergence pivot right: 5
```

### 12.5 Strict Daily Filter for Four Hour Signals

Use the last completed daily candle.

The daily filter passes when:

```text
Daily RSI is at least 50
Daily MACD is above its signal line
```

Four hour bullish confirmation requires:

```text
Four hour RSI is at least 50
Four hour MACD is above its signal line
Four hour histogram is rising
Strict daily filter passed
```

### 12.6 Momentum Overlay Display Contract

The TradingView momentum indicator is a single price chart overlay.

The automated scanner does not need to reproduce TradingView visuals, but its calculations must match the values that drive them.

Visual references:

```text
Momentum colored EMA 21
Muted EMA 50
Green trigger line
Teal support line
Orange warning line
Rising teal support trend line
Falling orange resistance trend line
```

The status table reports:

```text
Momentum Score
RSI value and state
MACD state
Higher timeframe state
Overall state
Structure
Trigger
Support
Warning
```

The table corner, line colors, marker visibility, and pane placement are cosmetic and must not alter calculations.

## 13. Trend Lines and Price Structure

Trend lines are supporting evidence, not primary score inputs.

Use confirmed pivots only.

Daily defaults:

```text
Left bars: 3
Right bars: 3
```

Four hour defaults:

```text
Left bars: 4
Right bars: 3
```

Calculate:

1. Rising support from two confirmed higher pivot lows.
2. Falling resistance from two confirmed lower pivot highs.
3. Latest horizontal pivot support.
4. Latest horizontal pivot resistance.
5. Projected trend line value at the latest completed candle.
6. Trend line breakout or breakdown.

Do not add trend line points to the main score unless the user explicitly approves a scoring change.

## 14. Option Liquidity

A candidate cannot receive S tier or A plus when its options are not practically tradable.

Create these initial defaults in `config/strategy.yaml`:

```yaml
preferred_dte_target_minimum: 30
preferred_dte_target_maximum: 45
preferred_dte_hard_minimum: 30
preferred_dte_maximum: 60

preferred_delta_minimum: 0.45
preferred_delta_maximum: 0.65

maximum_bid_ask_spread_percent_of_mid: 10

minimum_open_interest: 500
minimum_contract_daily_volume: 100
```

Classify:

```text
Good:
All requirements pass

Acceptable:
One minor requirement misses by no more than 20 percent

Poor:
Spread, open interest, volume, or pricing quality is materially inadequate

Unknown:
Current option data is unavailable
```

Poor or unknown liquidity cannot receive S tier.

Unknown liquidity should normally prevent A plus unless the candidate is labeled technical watch only.

Do not recommend a specific contract unless the option data is current.

The intended holding period is several days to roughly two weeks.

Prefer expiration dates that provide at least two to three times the expected holding period.

The normal target is approximately 30 to 45 days to expiration. Contracts beyond 45 days may be used when liquidity, pricing, and the trade thesis justify them.

Avoid very short dated weekly contracts for the normal strategy.

Evaluate implied volatility before entry.

Prefer contracts when implied volatility is not materially elevated relative to the stock's recent range.

A technically valid breakout may still be rejected or downgraded when option premium is inflated by elevated implied volatility.


## 15. Catalyst and Event Research

Research catalysts only after deterministic technical filtering.

Prefer primary sources:

1. Company investor relations releases.
2. SEC filings.
3. Regulatory agency publications.
4. Exchange filings.
5. Official product announcements.
6. Official partnership announcements.
7. Official earnings materials.

Use reputable financial reporting only as secondary confirmation.

Never treat anonymous social media posts or unsourced screenshots as verified evidence.

For each finalist check:

1. Earnings date.
2. Guidance.
3. Investor day.
4. Product launch.
5. Regulatory decision.
6. Conference appearance.
7. Analyst action.
8. Offering or dilution risk.
9. Litigation.
10. Investigation.
11. Sector catalyst.
12. Broader market risk.

Default earnings restriction:

```yaml
earnings_blackout_calendar_days: 7
allow_earnings_event_trades: false
```

A candidate inside the blackout cannot receive S tier unless event trade mode is explicitly enabled.

## 16. Grading

Only S tier and A plus appear in the primary user report.

Everything else must be stored internally with explicit rejection reasons.

### 16.1 S Tier

Every requirement must pass:

```text
Daily Command Score is at least 85
Daily call bias is bullish, pullback setup, or breakout confirmed
Daily momentum is at least 80
Daily momentum state is bullish or strong bullish
Four hour momentum is at least 85
Four hour bullish confirmation is active
Strict daily filter passed
Relative strength is leading
Price is above monthly anchored VWAP
Price is not extended
Weekly alignment passed
Option liquidity is good
Catalyst is verified, or technical continuation has strong sector support
No unresolved major event risk exists
Market regime is not hostile
Entry is valid now or immediately approaching a valid trigger
```

S tier must be rare.

Never promote a candidate merely to fill the report.

### 16.2 A Plus Tier

Requirements:

```text
Daily Command Score is at least 75
Daily momentum is at least 70
Four hour momentum is at least 75
Price is not extended
Relative strength is leading or improving
Option liquidity is good or acceptable
Market regime is not hostile
No major unresolved risk exists
No more than one minor confirmation is missing
```

Permitted minor missing confirmations:

1. Waiting for a four hour breakout close.
2. Waiting for a support retest.
3. Waiting for volume confirmation.
4. Daily MACD improving but not fully bullish.
5. Four hour histogram improving but not yet rising.

Two meaningful missing confirmations disqualify A plus.

### 16.2A Technical Watch

Technical Watch is allowed only in free-first mode.

Requirements:

```text
Daily Command Score is at least 75
Daily momentum is at least 70
Four hour momentum is at least 75
Price is not extended
Relative strength is leading or improving
Market regime is not hostile
No major unresolved risk exists
Option liquidity is Unknown or Indicative because paid-quality option data is unavailable
```

Technical Watch must not be described as trade-ready.

Technical Watch must state:

```text
Current tradable option liquidity is unavailable on the free data plan.
Review the underlying technical setup only.
Do not enter an option trade until current bid, ask, spread, volume, open interest, DTE, delta, and IV are verified in the broker.
```

Technical Watch is not a downgrade path for weak setups. It is only for technically qualified setups blocked by free data limitations.

### 16.3 Automatic Rejection

Reject from the primary report when any condition applies:

1. Price is below SMA 200.
2. Daily Command Score is below 60.
3. Price is extended.
4. Critical data is stale or incomplete.
5. Options are illiquid.
6. Support already failed.
7. Market regime is hostile without exceptional justification.
8. An unverified catalyst is represented as fact.
9. Earnings blackout is violated.
10. A gap destroys planned reward to risk.
11. Daily filter is blocked and four hour momentum is the only bullish evidence.
12. Major dilution, legal, regulatory, or offering risk remains unresolved.

## 17. Entry Plan

For every qualifying candidate calculate:

1. Entry mode, breakout or pullback.
2. Breakout trigger.
3. Nearest support.
4. Invalidation level.
5. Nearest resistance.
6. Distance to trigger.
7. Distance to support.
8. ATR extension.
9. Underlying reward to risk estimate.
10. Entry status, valid now, approaching, or waiting.

Invalidation must come from price structure.

Do not manufacture false precision.

## 18. Telegram Notification Configuration

Create `config/notifications.yaml` with these defaults:

```yaml
enabled: true

provider: telegram

timezone: America/New_York

send_post_close_completion: true
send_zero_setup_completion: true

send_premarket_only_on_change: true
send_four_hour_only_on_change: true

maximum_candidates_per_message: 5

local_macos_fallback: true

notify_on:
  new_s_tier: true
  new_a_plus: true
  promotion_to_s_tier: true
  demotion: true
  rejection_of_active_candidate: true
  breakout_trigger_confirmed: true
  pullback_support_held: true
  support_lost: true
  invalidation_triggered: true
  price_became_extended: true
  catalyst_invalidated: true
  earnings_risk_discovered: true
  option_liquidity_deteriorated: true
  market_regime_became_hostile: true
  stale_data: true
  scan_failure: true
  unchanged_candidate: false
```

Required environment variables:

```text
TELEGRAM_BOT_USERNAME
TELEGRAM_BOT_URL
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

Use these nonsecret defaults:

```text
TELEGRAM_BOT_USERNAME=AlisScreenerBot
TELEGRAM_BOT_URL=https://t.me/AlisScreenerBot
```

Add all four names to `.env.example`. Keep `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` blank in `.env.example`.

The live `.env` file must contain the regenerated token and the discovered private chat identifier.

Never print the bot token in logs, reports, terminal output, exception messages, test output, or Codex responses.

## 19. Telegram Setup Workflow

The README must explain this exact setup for the existing bot.

Known nonsecret bot identity:

```text
Bot display name: Ali's Screener Bot
Bot username: AlisScreenerBot
Bot link: https://t.me/AlisScreenerBot
```

Security requirement before setup:

1. A token that has appeared in any chat or shared text must be treated as compromised.
2. Open `@BotFather` in Telegram.
3. Revoke or regenerate the token for `@AlisScreenerBot`.
4. Never paste the replacement token into AI chat, documentation, source code, or a committed file.
5. Store the replacement token only in the local `.env` file as `TELEGRAM_BOT_TOKEN`.

Connection workflow:

1. Install or open Telegram.
2. Open `https://t.me/AlisScreenerBot`.
3. Press Start or send a message such as `hello`.
4. Copy `.env.example` to `.env`.
5. Set the nonsecret values:

```text
TELEGRAM_BOT_USERNAME=AlisScreenerBot
TELEGRAM_BOT_URL=https://t.me/AlisScreenerBot
```

6. Put the newly regenerated secret token into `TELEGRAM_BOT_TOKEN` in `.env`.
7. Leave `TELEGRAM_CHAT_ID` blank initially.
8. Run:

```text
python -m scanner.notifications discover_chat_id
```

9. The command must read recent Telegram updates, identify the private chat associated with the user message, display only the detected chat identifier and safe bot identity, and optionally write the chat identifier to `.env` after explicit confirmation.
10. Set the detected value as `TELEGRAM_CHAT_ID`.
11. Run:

```text
python -m scanner.run_scan test_notification
```

12. The test message must include:

```text
ALI'S SCREENER BOT TEST

Telegram notifications are connected successfully.
This was a test only. No market scan was performed.
```

13. Confirm that the test message arrived in the private chat with `@AlisScreenerBot`.
14. Run `python -m scanner.run_scan validate_configuration`.
15. Do not enable scheduled scans until both the test notification and configuration validation succeed.

The `discover_chat_id` command must never display, return, log, or serialize the bot token.

The system must verify that the configured bot username is `AlisScreenerBot` when Telegram returns bot identity information. A username mismatch must produce a safe configuration error without exposing credentials.

## 20. Notification Rules

### 20.1 Post Close

Always send one completion message, including when zero setups qualify.

Example with candidates:

```text
POST CLOSE SCAN COMPLETE

Market regime: Supportive
S tier: 1
A plus: 2
Securities scanned: 487
Completed: 4:24 PM ET

Top setup: AMD
Grade: S
Trigger: 165.40
Support: 161.80

Full report: reports/post_close/latest.md
```

Example with zero candidates:

```text
POST CLOSE SCAN COMPLETE

No S tier or A plus setups qualified today.

Standards were not lowered.

Market regime: Mixed
Securities scanned: 487
Completed: 4:23 PM ET
```

### 20.2 Premarket

Notify only when:

1. A candidate is promoted.
2. A candidate is demoted.
3. A candidate is rejected.
4. A material catalyst appears.
5. A catalyst is invalidated.
6. Earnings or event risk changes.
7. A premarket gap changes the entry plan.
8. The scan fails.

### 20.3 Four Hour Refresh

Notify only when:

1. A candidate is promoted to S tier.
2. A new A plus candidate appears.
3. A breakout trigger is confirmed.
4. A pullback support test holds.
5. Support fails.
6. Invalidation is triggered.
7. Price becomes extended.
8. The strict daily filter changes.
9. The scan fails.

Do not notify for an unchanged candidate.

## 21. Candidate Notification Format

For S tier:

```text
S TIER SETUP

Ticker: {symbol}
Company: {company}
Current price: {current_price}

Daily Command: {daily_command_score}
Daily Momentum: {daily_momentum_score}
Four Hour Momentum: {four_hour_momentum_score}
Daily Filter: {daily_filter}

Entry Mode: {entry_mode}
Trigger: {breakout_trigger}
Support: {support}
Invalidation: {invalidation}
Nearest Resistance: {nearest_resistance}

Relative Strength: {relative_strength}
Relative Volume: {relative_volume}
Option Liquidity: {option_liquidity}

Catalyst: {catalyst_summary}
Earnings: {earnings_date}
Status: {entry_status}

Report: {report_path}
```

For A plus:

```text
A PLUS SETUP

Ticker: {symbol}
Current price: {current_price}

Daily Command: {daily_command_score}
Daily Momentum: {daily_momentum_score}
Four Hour Momentum: {four_hour_momentum_score}

Trigger: {breakout_trigger}
Support: {support}
Invalidation: {invalidation}

Missing Confirmation: {missing_confirmation}
Reason It Is Not S Tier: {not_s_tier_reason}

Report: {report_path}
```

For invalidation:

```text
SETUP INVALIDATED

Ticker: {symbol}
Previous Grade: {previous_grade}
Reason: {reason}
Current Price: {current_price}
Failed Level: {failed_level}

Action: Remove from the active watchlist.
```

For a failed scan:

```text
SCREENER FAILURE

Run Type: {scan_type}
Failure Time: {failure_time}
Stage: {failure_stage}
Error: {safe_error_summary}
Last Successful Run: {last_successful_run}

No market conclusion was produced from this failed run.
```

## 22. Notification Deduplication

Do not repeatedly send the same notification.

Create a deterministic notification identifier using:

```text
Scan date
Run type
Ticker
Grade
Event type
Trigger value
Support value
Invalidation value
```

Store sent identifiers in:

```text
data/state/notification_state.json
```

A notification may be sent again only when something material changes:

1. Grade.
2. Entry status.
3. Trigger.
4. Support.
5. Invalidation.
6. Catalyst status.
7. Earnings status.
8. Option liquidity.
9. Market regime.
10. Daily filter.

Record every delivery attempt in `logs/notifications.log`.

Store:

```text
Timestamp
Provider
Notification identifier
Ticker
Event type
Delivery status
Safe error message
```

## 23. Telegram Delivery Requirements

Use the Telegram HTTP Bot API.

Set reasonable connection and response timeouts.

Retry temporary network failures with bounded exponential backoff.

Do not retry invalid credentials indefinitely.

Parse the provider response and confirm successful delivery.

Do not mark a notification delivered unless Telegram confirms success.

Split messages safely when they exceed the provider message length.

Never split in the middle of a ticker section when avoidable.

Escape formatting safely.

Do not allow report content to create unintended mentions or commands.

When Telegram fails and local macOS fallback is enabled, attempt:

```text
osascript
```

The local fallback message should contain only a concise failure summary and the report path.

## 24. Primary Report

Show no more than five total candidates.

The correct number may be zero.

Begin every report with:

```text
Scan type:
Generated at:
Market data timestamp:
Market regime:
Securities scanned:
Passed deterministic filters:
Received catalyst review:
```

Use this format:

```text
S TIER

1. TICKER

Grade:
Status:
Company:
Sector:
Benchmark:
Current price:
Daily Command Score:
Daily call bias:
Daily Momentum Score:
Daily momentum state:
Four Hour Momentum Score:
Four hour momentum state:
Daily filter:
Relative strength:
Relative volume:
Monthly anchored VWAP:
Weekly alignment:
Market structure:
Trend line structure:
Breakout trigger:
Pullback support:
Invalidation:
Nearest resistance:
Entry mode:
Entry status:
Option liquidity:
Preferred DTE range:
Catalyst:
Catalyst source:
Earnings date:
Event risk:
Market regime:
Why it qualifies:
What must happen next:
What invalidates it:
Reason it is S tier:
```

Then:

```text
A PLUS TIER
```

Use the same fields and add:

```text
Missing confirmation:
Reason it is not S tier:
```

When free mode produces Technical Watch candidates, add:

```text
FREE TECHNICAL WATCH
```

Each Technical Watch record must use the same fields and must clearly state that it is not trade-ready because current tradable option liquidity is unavailable or only indicative.

End every report with:

```text
NO TRADE CONDITIONS
```

Include:

1. Gap exceeds one ATR above the trigger.
2. Support fails before entry.
3. Option spread exceeds the configured limit.
4. Option data becomes stale.
5. New earnings or event risk appears.
6. Market regime turns hostile.
7. Price becomes extended.
8. Catalyst is contradicted.

When nothing qualifies, write exactly:

```text
No S tier or A plus setups qualified today.

Standards were not lowered.
```

## 25. Machine Readable Results

Save JSON in addition to Markdown.

Use this top level structure:

```json
{
  "scan_type": "",
  "generated_at": "",
  "market_data_timestamp": "",
  "market_regime": "",
  "universe_count": 0,
  "deterministic_pass_count": 0,
  "research_count": 0,
  "s_tier": [],
  "a_plus": [],
  "technical_watch": [],
  "rejected": []
}
```

Every rejected record must include:

```json
{
  "symbol": "",
  "stage": "",
  "reason_codes": [],
  "details": {}
}
```

Never discard rejection reasons.

## 26. Sources

Every catalyst, event date, filing, earnings date, and analyst action must include:

1. Source title.
2. Publisher or issuer.
3. Publication timestamp when available.
4. Retrieval timestamp.
5. Source link or source identifier.
6. Confidence, verified, corroborated, or unverified.

Do not use an unverified claim to increase a grade.

When sources conflict, report the conflict and prioritize the more authoritative source.

## 27. State Tracking

Persist:

1. Previous reports.
2. Previous candidate grades.
3. Trigger and support values.
4. Invalidation values.
5. Catalyst assessments.
6. Option liquidity state.
7. Promotion and demotion history.
8. Notification history.
9. Paper signal outcomes.

Classify updates:

```text
New
Promoted
Unchanged
Demoted
Rejected
```

Do not present the same unchanged setup as new.

## 28. Evaluation

Track every paper signal.

Record:

1. Entry trigger time.
2. Maximum favorable excursion.
3. Maximum adverse excursion.
4. Performance after one trading day.
5. Performance after three trading days.
6. Performance after five trading days.
7. Performance after ten trading days.
8. Whether support failed first.
9. Whether resistance was reached first.
10. Whether the catalyst changed.
11. Whether the grade was justified.

Do not optimize thresholds from a tiny sample.

Wait for at least 50 completed signals before drawing meaningful performance conclusions.

## 29. Prohibited Behavior

Never:

1. Place a trade.
2. Connect to a brokerage account.
3. Fabricate market data.
4. Fabricate citations.
5. Use incomplete candles as completed candles.
6. Lower standards to produce candidates.
7. Hide missing data.
8. Label a candidate S tier when a required condition fails.
9. Recommend illiquid options.
10. Guarantee profit.
11. Delete historical reports.
12. Delete rejection records.
13. Delete notification history.
14. Expose Telegram credentials.
15. Alter scoring formulas without user approval.

## 30. Testing

Write tests for:

1. RSI score boundaries.
2. MACD score cap.
3. Extended RSI score cap.
4. Command Score maximum.
5. EMA 21 above SMA 50 Command Score component.
6. Confirmation that EMA 9 is not used by the finalized Command Center.
7. Strict daily filter.
8. Incomplete candle rejection.
9. Breakout lookback excluding the current bar.
10. Pullback support selection.
11. Extended price detection.
12. Daily Call Bias boundaries.
13. S tier requirements.
14. A plus one missing confirmation rule.
15. Zero qualifying setups.
16. Stale data rejection.
17. Option liquidity classifications.
18. DTE rules.
19. Implied volatility downgrade or rejection logic.
20. Telegram message generation.
21. Telegram successful delivery using a mock.
22. Telegram rejected credentials using a mock.
23. Telegram temporary failure and retry.
24. Notification deduplication.
25. Post close zero setup notification.
26. Premarket unchanged candidate producing no notification.
27. Four hour promotion notification.
28. Scan failure notification.
29. Local macOS fallback behavior.

Automated tests must never send real Telegram messages.

Use mocked clients.

Fail loudly when critical data is unavailable.

## 31. Security

Never commit `.env`.

Never print secret values.

Mask secrets in exception messages.

Do not store Telegram tokens in reports, JSON output, logs, screenshots, or test fixtures.

Do not expose the full Telegram response when it contains sensitive request information.

Use least privilege for all data provider credentials.

## 32. Build Order

Build in this order:

1. Project structure.
2. Configuration.
3. Environment template.
4. Data provider interface.
5. Data quality validation.
6. Indicator calculations.
7. Daily Command Center.
8. Daily momentum.
9. Four hour momentum.
10. Strict daily filter.
11. Deterministic filtering.
12. Grading.
13. JSON report.
14. Markdown report.
15. State tracking.
16. Telegram provider.
17. Telegram test command.
18. Notification deduplication.
19. Catalyst research.
20. Option liquidity.
21. Scheduled scripts.
22. Paper outcome tracking.
23. Tests.
24. Documentation.

Do not begin by asking an AI agent to research the entire market.

Technical filtering must occur first.


## 32A. Cloud Runtime and Persistence

The finished application must be capable of running while the user's laptop is off.

Prepare for scheduled container execution on Render Cron Jobs or Google Cloud Run Jobs.

Requirements:

1. Containerized, reproducible runtime.
2. Environment-based configuration.
3. No dependency on a local desktop session.
4. Exchange-calendar checks inside the application.
5. Idempotent scheduled runs.
6. Run locking to prevent duplicate simultaneous scans.
7. Persistent external storage support for production.
8. Local JSON storage only for development and fixtures.
9. PostgreSQL-compatible production storage adapter, suitable for Supabase.
10. Safe retries for transient provider and notification failures.
11. Durable notification deduplication.
12. Completion and failure records for every scheduled run.
13. No automatic creation of paid infrastructure.
14. Clear deployment documentation and estimated operating cost.

## 33. Definition of Done

Version one is complete when:

1. One command runs the post close scan.
2. The configured universe is processed.
3. Technical calculations are deterministic and tested.
4. S tier and A plus grades follow this file.
5. The report contains no more than five candidates.
6. A zero candidate report works.
7. Every candidate includes trigger, support, invalidation, and risk.
8. Catalyst claims include sources.
9. Markdown and JSON results are saved.
10. Telegram setup is documented.
11. Chat identifier discovery works.
12. Test notification works.
13. Post close always sends completion.
14. Premarket and four hour runs suppress unchanged messages.
15. Notification deduplication works.
16. Unit tests pass.
17. Brokerage execution does not exist.
18. README includes installation, provider configuration, Telegram setup, and run commands.
19. The completed implementation is committed and pushed to `origin/main`.

## 33A. Finalized Strategy Version

This file represents the finalized v3 strategy architecture.

Key finalized changes:

1. The Command Center uses EMA 21, SMA 50, SMA 200, and monthly anchored VWAP.
2. EMA 9 was removed from the Command Center.
3. The Command Score awards ten points for EMA 21 above SMA 50.
4. Momentum is a single price chart overlay with no lower pane.
5. Momentum uses `overlay = true` and `scale = scale.none` in TradingView.
6. RSI and MACD remain calculation inputs even though their oscillator waves are not plotted.
7. The four hour chart uses the completed daily candle as its higher timeframe filter.
8. The daily momentum view uses the completed weekly candle as its higher timeframe filter.
9. No timeframe below four hours is part of version one.
10. Signal markers are off by default.
11. The momentum status table is currently displayed in the top right corner, but location is cosmetic.
12. Telegram remains the version one notification channel.

## 34. Response Style

Be direct.

Lead with results.

Separate calculated facts from research-layer interpretation.

State missing data clearly.

Do not use promotional language.

Do not produce a broad list of mediocre stocks.

The primary report must contain only S tier and A plus candidates.
