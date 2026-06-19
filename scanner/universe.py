from __future__ import annotations

from scanner.config import load_config


def configured_symbols(fixture: bool = False) -> list[str]:
    if fixture:
        return ["SSTR", "APLUS", "ZERO"]
    config = load_config("universe")
    symbols = config.get("symbols", [])
    return [str(symbol) for symbol in symbols]
