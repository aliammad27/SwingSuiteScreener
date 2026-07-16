# Bullish Weekly Participation v5

Follow `AGENTS.md` as the engineering contract.

The active system is a deterministic, read-only bullish stock and weekly long-call
research screener. `config/strategy.yaml` and `scanner/strategy_profile.py` are
authoritative. The daily chart owns trend and production-pattern selection; a
completed 60-minute bar owns timing.

V5 remains `research_default`. Even complete candidates stay `Ready - Verify` until
the documented historical and shadow gates pass. Never add brokerage execution or
account access, and never describe a score as a probability or performance forecast.

Keep the Python scanner, dense HTML workspace, notifications, five Pine scripts,
fixtures, tests, build plan, and training manual in parity.
