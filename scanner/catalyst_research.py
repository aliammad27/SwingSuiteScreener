from __future__ import annotations

from scanner.models import Catalyst


def catalyst_allows_primary_grade(catalyst: Catalyst) -> bool:
    return catalyst.verified and not catalyst.major_event_risk
