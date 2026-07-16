from __future__ import annotations

from scanner.config import ConfigurationError, load_config
from scanner.models import AssetMetadata, StrategyLane


def _universe_config() -> dict[str, object]:
    return load_config("universe")


def index_core_symbols() -> list[str]:
    raw = _universe_config().get("index_core")
    if not isinstance(raw, dict) or not isinstance(raw.get("symbols"), list):
        raise ConfigurationError("universe.index_core.symbols must be a list.")
    return [str(symbol) for symbol in raw["symbols"]]


def leader_metadata() -> dict[str, AssetMetadata]:
    sectors = _universe_config().get("sectors")
    if not isinstance(sectors, dict):
        raise ConfigurationError("universe.sectors must be a mapping.")
    metadata: dict[str, AssetMetadata] = {}
    for sector, raw in sectors.items():
        if not isinstance(raw, dict) or not isinstance(raw.get("symbols"), list):
            raise ConfigurationError(f"Universe sector {sector} is invalid.")
        benchmark = str(raw.get("benchmark", "SPY"))
        for raw_symbol in raw["symbols"]:
            symbol = str(raw_symbol)
            if symbol in metadata:
                raise ConfigurationError(f"Duplicate universe symbol: {symbol}")
            metadata[symbol] = AssetMetadata(
                symbol=symbol,
                company=symbol,
                sector=str(sector),
                peer_etf=benchmark,
                lane=StrategyLane.LEADER_SWING,
            )
    return metadata


def metadata_for(symbol: str) -> AssetMetadata:
    if symbol in index_core_symbols():
        return AssetMetadata(
            symbol=symbol,
            company=symbol,
            sector="Index ETF",
            peer_etf="SPY" if symbol == "QQQ" else "QQQ",
            lane=StrategyLane.INDEX_CORE,
        )
    if symbol in {"SSTR", "APLUS", "BTIER", "ZERO"}:
        return AssetMetadata(
            symbol=symbol,
            company={
                "SSTR": "Swing Suite Strong Fixture Corp.",
                "APLUS": "Ready Verify Fixture Corp.",
                "BTIER": "Developing Fixture Corp.",
                "ZERO": "Rejected Fixture Corp.",
            }[symbol],
            sector="Technology",
            peer_etf="XLK",
            lane=StrategyLane.LEADER_SWING,
        )
    metadata = leader_metadata()
    if symbol not in metadata:
        raise ConfigurationError(f"Symbol is not configured: {symbol}")
    return metadata[symbol]


def configured_symbols(fixture: bool = False) -> list[str]:
    if fixture:
        return ["SPY", "QQQ", "SSTR", "APLUS", "BTIER", "ZERO"]
    return index_core_symbols() + list(leader_metadata())


def configured_leader_symbols(fixture: bool = False) -> list[str]:
    if fixture:
        return ["SSTR", "APLUS", "BTIER", "ZERO"]
    return list(leader_metadata())


def peer_benchmarks(fixture: bool = False) -> list[str]:
    if fixture:
        return ["XLK"]
    return sorted({asset.peer_etf for asset in leader_metadata().values()})
