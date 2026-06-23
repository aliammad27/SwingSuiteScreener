# SwingSuiteScreener

SwingSuiteScreener is a deterministic bullish call swing-trading screener for liquid
U.S. stocks with listed options. The daily Command Center selects candidates; the
daily and four-hour Momentum Engine confirms thesis and timing.

This is research and decision-support software only. It has no account, position,
order, paper-trading, or live-trading functionality.

## Quick Start

```bash
python3 -m pip install -r requirements.txt
python -m scanner.run_scan validate_configuration
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan four_hour --fixture
python -m scanner.run_scan daily_prep --fixture
python -m scanner.run_scan weekly_radar --fixture
```

Fixture reports are always labeled:

```text
SIMULATED FIXTURE OUTPUT — NOT CURRENT MARKET DATA
```

## Required Commands

```bash
python -m scanner.run_scan validate_configuration
python -m scanner.run_scan readiness_check
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan four_hour --fixture
python -m scanner.run_scan daily_prep --fixture
python -m scanner.run_scan weekly_radar --fixture
python -m scanner.run_scan test_notification
python -m scanner.notifications discover_chat_id
pytest
ruff check .
mypy scanner
```

Additional deterministic fixture scenarios:

```bash
python -m scanner.run_scan post_close --fixture --scenario s_tier
python -m scanner.run_scan post_close --fixture --scenario a_plus
python -m scanner.run_scan post_close --fixture --scenario technical_watch
python -m scanner.run_scan post_close --fixture --scenario zero
```

## Free-First Provider Mode

The default setup is designed to stay free:

- Equities: Alpaca Basic / free IEX feed through `ALPACA_FEED=iex`
- Options: Alpaca indicative options feed through `ALPACA_OPTION_FEED=indicative`
- Notifications: Telegram Bot API
- Storage: local JSON unless you later choose a free/paid external database

Alpaca's Basic plan has important limits: IEX-only equity coverage, indicative
options rather than OPRA, and latest-15-minute restrictions on historical data.
Because of that, free mode is intentionally conservative:

- True S tier still requires current good option liquidity.
- True A Plus still requires good or acceptable option liquidity.
- If a setup passes the technical gates but only indicative/unknown option data is
  available, it is labeled `Technical Watch`, not trade-ready.

This keeps the scanner useful without pretending free data is paid OPRA-quality.

Source: https://docs.alpaca.markets/us/docs/about-market-data-api

## Default Universe

The live default universe is a broad seed list of 161 liquid, optionable U.S.-listed
large-cap and mid-cap stocks across technology, financials, consumer, health care,
industrials, and energy. The scanner still applies the full strategy gates before
anything appears in `S`, `A+`, `TW`, or `Watch`.

The nightly `Watch` bucket is not the whole universe. It includes only names that
pass the strategy's daily watch-quality gates.

Nightly and weekly Telegram messages include compact reason lines, TradingView
chart links, target stock prices, research call strikes, 45-60 DTE windows, and
daily chart image attachments for the top ranked names.

## Providers

Provider interfaces exist for:

- equities market data
- options data
- catalysts
- notifications
- persistence

The production `AlpacaDataProvider` uses Alpaca's market data HTTP API directly
through environment credentials. Production code does not depend on Codex, MCP, or
the Alpaca plugin.

Required live market variables:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
ALPACA_DATA_BASE_URL
ALPACA_FEED
ALPACA_OPTION_FEED
```

Alpaca feed limitation: the default `.env.example` uses `iex` for equities and
`indicative` for options so the project can stay free. SIP equities and OPRA
options require paid access.

## Telegram Setup

Use the existing bot:

- Bot display name: Ali's Screener Bot
- Bot username: `AlisScreenerBot`
- Bot link: https://t.me/AlisScreenerBot

If a token has appeared in chat, documentation, issue text, or any shared location,
treat it as compromised and regenerate it through BotFather.

Setup:

1. Open https://t.me/AlisScreenerBot.
2. Press Start or send `hello`.
3. Copy `.env.example` to `.env`.
4. Put the regenerated token only in `.env` as `TELEGRAM_BOT_TOKEN`.
5. Leave `TELEGRAM_CHAT_ID` blank.
6. Run `python -m scanner.notifications discover_chat_id`.
7. Set the detected chat id in `.env`.
8. Run `python -m scanner.run_scan test_notification`.
9. Run `python -m scanner.run_scan validate_configuration`.

The token is never printed by discovery, tests, reports, or logs.

The application loads the local `.env` file automatically for scanner and
notification commands. You do not need to run `source .env`.

## Nightly Prep Telegram

`python -m scanner.run_scan daily_prep` sends one Telegram prep note for the
next market session. It runs the same strict scanner, includes the S Tier, A Plus,
and Technical Watch ticker lists, and explicitly says when no tickers qualified.
The Telegram body is intentionally short:

- next market session date
- `S`, `A+`, `TW`, and `Watch` ticker buckets
- `Watch` includes only strategy-qualified daily watch names, not the whole universe
- top ranked ticker reasons and TradingView links
- target stock price, research call strike, 45-60 DTE window, and 5-14 day swing window
- daily chart image attachments for the top ranked names
- a short note only when Technical Watch appears

Use `python -m scanner.run_scan daily_prep --fixture` to print the message
without sending Telegram.

## Weekly Radar Telegram

`python -m scanner.run_scan weekly_radar` sends a Sunday radar note using the same
strict scanner, ranked reasons, TradingView links, and chart attachments. It is a
weekly planning view, not a separate strategy.

## Reports

Markdown and JSON reports are written to:

- `reports/post_close/latest.md` and `.json`
- `reports/premarket/latest.md` and `.json`
- `reports/four_hour/latest.md` and `.json`

Only S tier and A Plus candidates appear in the primary report. Rejections and
reason codes are retained in JSON.

## Persistence

Development and fixture runs use local JSON state in `data/state`. Production can
select a PostgreSQL-compatible adapter suitable for Supabase through `DATABASE_URL`.
The adapter surface is isolated behind `scanner.storage.base.Storage`.

## Cloud Readiness

The repository includes:

- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- GitHub Actions schedules in `.github/workflows/`
- scheduled shell scripts in `scripts/`

Default free automation uses GitHub Actions:

- Nightly prep: sends at 9:00 PM ET
- Weekly radar: sends Sunday at 8:00 PM ET
- Premarket validation: runs at 8:45 AM ET
- Four-hour refresh: runs at 1:35 PM ET
- Post-close scan: runs at 4:20 PM ET

GitHub scheduled events are best-effort and can start late. To reduce late
market texts, each workflow now wakes several hours early during daylight saving
time, has a near-target backup wakeup, and uses `python -m scanner.schedule_gate`
to wait inside the runner until the intended America/New_York time. After a
successful alert, the workflow holds the concurrency window open until stale
backup runs would be blocked. If GitHub wakes the job more than 20 minutes after
the intended time, the gate fails the job instead of sending a stale scan. The
app still validates market calendar rules internally.

Render Cron Jobs can run the Docker commands in `render.yaml`. Google Cloud Run
Jobs can build the same container and schedule equivalent commands with Cloud
Scheduler. Do not create paid cloud resources without explicit approval.

Estimated operating cost depends on provider plans, scan frequency, and selected
cloud runtime. GitHub Actions is free for public repositories and includes a free
minutes quota for private repositories. This scanner's scheduled Linux jobs are
intended to stay inside that included quota.

Required GitHub Actions secrets:

```text
ALPACA_API_KEY_ID
ALPACA_API_SECRET_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
```

## Security

`.env`, local state, logs, generated reports, raw data, and caches are ignored by
Git. Never commit credentials or private market data.

## Development Checks

```bash
pytest
ruff check .
mypy scanner
docker build -t swingsuite-screener .
```

## June 22, 2026 Readiness

June 19, 2026 is a U.S. market holiday. The next regular market open is Monday,
June 22, 2026. Run this before then:

```bash
python -m scanner.run_scan readiness_check
python -m scanner.run_scan test_notification
python -m scanner.run_scan post_close --fixture
```

Live scans require free Alpaca API keys in `.env`. Do not add paid plans unless
you explicitly decide the OPRA/SIP upgrade is worth it.

GitHub Actions scheduled runs require the same values as GitHub repository
secrets. After secrets are set and workflows are pushed, the scanner runs while
your laptop is off.
