from __future__ import annotations

from datetime import datetime

from scanner.models import ContractSelection, DataTrust, EventRisk, EventRiskStatus
from scanner.strategy_profile import StrategyProfile


def event_trust_reasons(
    event: EventRisk,
    as_of: datetime,
    profile: StrategyProfile,
) -> tuple[str, ...]:
    reasons: list[str] = []
    if event.status == EventRiskStatus.UNKNOWN:
        reasons.append("event_source_unknown")
    if event.source_timestamp is None:
        reasons.append("event_source_timestamp_missing")
    else:
        event_age_hours = max(
            (as_of - event.source_timestamp).total_seconds() / 3600,
            0.0,
        )
        if event_age_hours > profile.maximum_event_source_age_hours:
            reasons.append("event_source_stale")
    return tuple(reasons)


def assess_data_trust(
    *,
    stock_feed: str,
    contracts: ContractSelection,
    event: EventRisk,
    as_of: datetime,
    profile: StrategyProfile,
) -> DataTrust:
    stock_trusted = stock_feed.lower() == profile.required_stock_feed.lower()
    option_trusted = (
        contracts.feed.lower() == profile.required_option_feed.lower()
        and contracts.primary is not None
    )
    event_reasons = event_trust_reasons(event, as_of, profile)
    event_trusted = not event_reasons
    quote_age: float | None = None
    if contracts.primary_risk is not None:
        quote_age = contracts.primary_risk.quote_age_minutes
        option_trusted = (
            option_trusted
            and quote_age <= profile.maximum_quote_age_minutes
            and contracts.primary_risk.quote_stable
        )

    reasons: list[str] = []
    if not stock_trusted:
        reasons.append("stock_feed_not_sip")
    if contracts.feed.lower() != profile.required_option_feed.lower():
        reasons.append("option_feed_not_opra")
    if contracts.primary is None:
        reasons.append("eligible_contract_unavailable")
    if quote_age is not None and quote_age > profile.maximum_quote_age_minutes:
        reasons.append("option_quote_stale")
    if contracts.primary_risk is not None and not contracts.primary_risk.quote_stable:
        reasons.append("option_quote_unstable")
    reasons.extend(event_reasons)
    return DataTrust(
        stock_feed=stock_feed,
        option_feed=contracts.feed,
        event_source=event.source,
        stock_trusted=stock_trusted,
        option_trusted=option_trusted,
        event_trusted=event_trusted,
        quote_age_minutes=quote_age,
        reasons=tuple(reasons),
    )
