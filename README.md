# SwingSuiteScreener

SwingSuiteScreener is a deterministic, bullish-only research screener for liquid
U.S. stocks and call options. The active strategy is **Bullish Participation v3**:
find leading stocks in healthy markets, wait for a controlled pullback or current
breakout confirmation, and use options with enough time and delta to participate
without requiring an immediate explosive move.

This project is decision support only. It does not connect to a brokerage account,
size positions, place orders, or manage live trades.

## Active Profile

- Direction: bullish only
- Preferred setup: controlled pullback in an established uptrend
- Secondary setup: current confirmed breakout that is not extended
- Preferred expiration: 30-60 DTE
- Hard expiration bounds: 21-75 DTE
- Preferred call delta: 0.45-0.65
- Hard call-delta floor: 0.35
- Planning window: 5-15 trading days
- Re-qualification point: 21 DTE
- Maximum spread: 8% of option mid
- Minimum open interest: 500
- Minimum daily contract volume: 100
- Earnings-event trades: disabled

The profile intentionally has no minimum ATR requirement. It seeks sustained
participation, not only high-volatility names capable of reaching distant OTM
strikes quickly.

## Setup States

- `Ready`: all technical, timing, market, event-risk, and option-quality gates pass.
- `Ready - Verify`: the setup is close, with one minor confirmation requiring review.
- `Developing`: the trend is constructive but the current entry is not ready.
- `Verify Contract`: the chart passes, but live option quality is unavailable or indicative.
- `Rejected`: one or more hard gates fail.

The stored JSON grade codes remain `S`, `A+`, `B`, and `Technical Watch` for
backward compatibility. Reports and notifications use the plain-language states.

## Selection Logic

The daily chart owns selection. Important inputs include:

- price, EMA 21, SMA 50, and SMA 200 trend alignment
- rising SMA 200
- relative strength against QQQ
- monthly anchored VWAP
- weekly EMA 21 alignment
- market structure and volume
- pullback support or breakout confirmation
- extension and market-regime gates

The four-hour chart owns timing. It must agree with the daily trend and use only
completed candles. Pullbacks receive a ranking advantage because they generally
offer clearer invalidation and avoid paying for post-breakout volatility expansion.

## Contract Research

The screener produces a near-the-money research strike. It is only a starting
point for opening the live chain. The usable contract must be verified against:

- 30-60 DTE preference
- 0.45-0.65 delta preference
- bid/ask spread
- open interest and daily volume
- implied volatility
- earnings and other event risk

The former OTM midpoint-strike formula and movement-capability filter are inactive.

## Target And Invalidation

The report always shows the nearest confirmed daily pivot resistance. If that pivot
offers sufficient room, it becomes the target. If it is too close, the report labels
the target as a `2R planning objective` and explicitly requires review of the path
through nearby resistance. A synthetic objective is never described as resistance.

Management output is based on the underlying thesis:

- exit when the underlying invalidation is confirmed
- reassess after five sessions without meaningful progress
- never hold through earnings
- exit or fully re-qualify the idea by 21 DTE
- size with the possibility of a full premium loss in mind

The screener does not claim a win rate, average return, or expected value.

## Commands

Run deterministic fixture scans without credentials:

```bash
python -m scanner.run_scan validate_configuration --fixture
python -m scanner.run_scan post_close --fixture
python -m scanner.run_scan premarket --fixture
python -m scanner.run_scan four_hour --fixture
python -m scanner.run_scan daily_prep --fixture
python -m scanner.run_scan weekly_radar --fixture
```

Useful fixture scenarios:

```bash
python -m scanner.run_scan post_close --fixture --scenario s_tier
python -m scanner.run_scan post_close --fixture --scenario a_plus
python -m scanner.run_scan post_close --fixture --scenario technical_watch
python -m scanner.run_scan post_close --fixture --scenario zero
```

Legacy put modules remain in the repository for compatibility and historical
tests, but put commands are not exposed by the active CLI and `enable_put_scans`
must remain `false` for this profile.

## Live Data

Live scans use read-only Alpaca market-data endpoints. Configure these values in
an untracked `.env` file:

```text
ALPACA_API_KEY_ID=
ALPACA_API_SECRET_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

The free Alpaca option feed may be indicative. An indicative result becomes
`Verify Contract`, never `Ready`. Contract selection must be confirmed in the
broker using current option-chain data.

## Automation

GitHub Actions run the following Eastern Time research routines:

- Nightly preparation: 9:00 PM
- Weekly radar: Sunday 8:00 PM
- Premarket validation: 8:45 AM
- Four-hour refresh: 1:35 PM
- Post-close scan: 4:20 PM

Reports are written to `reports/<scan_type>/latest.md` and `.json`. Runtime
reports, charts, logs, environment files, and local state are ignored by Git.

## Validation

```bash
python -m pytest
python -m ruff check scanner tests
python -m mypy scanner
```

The test suite covers indicators, grading, contract classification, reports,
notifications, fixtures, schedules, state, data quality, and the read-only
provider boundary.

## Important Limitations

- Technical scores are deterministic rankings, not probabilities.
- A qualifying chart does not prove that an option is fairly priced.
- Delta is not a guaranteed probability of profit.
- Options can lose the full premium, including when the long-term market trend is up.
- Historical upward drift does not guarantee appreciation during a specific option's life.
- The user remains responsible for independent review and every trading decision.
