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
```

Fixture reports are always labeled:

```text
SIMULATED FIXTURE OUTPUT — NOT CURRENT MARKET DATA
```

## Required Commands

```bash
python -m scanner.run_scan validate_configuration
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan four_hour --fixture
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
python -m scanner.run_scan post_close --fixture --scenario zero
```

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
```

Alpaca feed limitation: the default `.env.example` uses `iex`, which is available
on many plans but does not include the full SIP consolidated feed. Use a permitted
feed for the account and plan.

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
- scheduled shell scripts in `scripts/`

Render Cron Jobs can run the Docker commands in `render.yaml`. Google Cloud Run
Jobs can build the same container and schedule equivalent commands with Cloud
Scheduler. Do not create paid cloud resources without explicit approval.

Estimated operating cost depends on provider plans, scan frequency, and selected
cloud runtime. Fixture mode runs locally without paid services.

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
