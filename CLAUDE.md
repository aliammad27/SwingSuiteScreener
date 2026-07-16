# Bullish Participation v4

Follow `AGENTS.md` as the engineering contract.

The active system is a deterministic, read-only bullish stock and long-call research
screener. `config/strategy.yaml` and `scanner/strategy_profile.py` are authoritative.
The daily chart selects the setup, the four-hour chart confirms timing, and only
completed candles count.

Never add brokerage execution or account access. Never describe a score as a
probability. Keep the Python scanner, HTML dashboard, Telegram output, Pine scripts,
fixtures, tests, build plan, and training manual in parity.
