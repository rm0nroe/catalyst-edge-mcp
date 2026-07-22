"""Deterministic scoped missingness and disposition reason records."""

from __future__ import annotations

import hashlib
from datetime import datetime

from catalyst_edge_mcp.models import ReasonCode, ReasonScope, ScopedReason

REASON_PRECEDENCE = {
    ReasonCode.SOURCE_UNAVAILABLE: 10,
    ReasonCode.SOURCE_UNSUPPORTED: 20,
    ReasonCode.ENTITY_REJECTED: 30,
    ReasonCode.OBSERVED_NONE: 40,
    ReasonCode.DISCOVERY_ONLY: 50,
    ReasonCode.EVALUATED_NOT_MATERIAL: 60,
}


def scoped_reason(
    code: ReasonCode,
    scope: ReasonScope,
    scope_id: str,
    *,
    source_id: str | None = None,
    family: str | None = None,
    observed_at: datetime | None = None,
    detail: str | None = None,
) -> ScopedReason:
    observed = observed_at.isoformat() if observed_at is not None else ""
    payload = "\x1f".join(
        (code.value, scope.value, scope_id, source_id or "", family or "", observed, detail or "")
    )
    return ScopedReason(
        reason_id=f"rsn_{hashlib.sha256(payload.encode()).hexdigest()}",
        code=code,
        scope=scope,
        scope_id=scope_id,
        display_precedence=REASON_PRECEDENCE[code],
        source_id=source_id,
        family=family,
        observed_at=observed_at,
        detail=detail,
    )


def ordered_reasons(reasons: list[ScopedReason]) -> list[ScopedReason]:
    unique = {reason.reason_id: reason for reason in reasons}
    return sorted(
        unique.values(),
        key=lambda reason: (
            reason.display_precedence,
            reason.code.value,
            reason.scope.value,
            reason.scope_id,
            reason.reason_id,
        ),
    )
