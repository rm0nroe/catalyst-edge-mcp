from dataclasses import replace

import pytest

from catalyst_edge_mcp.capability_gates import (
    OPTIONS_ENTITLEMENTS,
    OPTIONS_REQUIRED_GATES,
    SENTIMENT_CANDIDATES,
    SENTIMENT_REQUIRED_GATES,
    CapabilityAudit,
    GateCheck,
    GateState,
    options_provider_ready,
    sentiment_candidate_ready,
)


def _passing_audit(category: str, gates: tuple[str, ...]) -> CapabilityAudit:
    return CapabilityAudit(
        candidate_id="fixture",
        category=category,
        revision="fixture",
        checks=tuple(GateCheck(name, GateState.PASSED, "fixture") for name in gates),
        evidence_urls=(),
    )


def test_UT_SENTIMENT_CANDIDATES_ARE_DISABLED_FAIL_CLOSED():
    assert SENTIMENT_CANDIDATES
    assert all(not sentiment_candidate_ready(name) for name in SENTIMENT_CANDIDATES)
    for audit in SENTIMENT_CANDIDATES.values():
        assert audit.blockers(SENTIMENT_REQUIRED_GATES)


@pytest.mark.parametrize(
    "failed_gate",
    (
        "commercial_use_rights",
        "python_310_compatibility",
        "deterministic_preprocessing",
        "labeled_quality_benchmark",
        "rounded_output",
        "fixed_thresholds",
    ),
)
def test_UT_SENTIMENT_GATE_REJECTS_EACH_MANDATORY_FAILURE(failed_gate):
    audit = _passing_audit("sentiment", SENTIMENT_REQUIRED_GATES)
    checks = tuple(
        replace(check, state=GateState.FAILED) if check.name == failed_gate else check
        for check in audit.checks
    )
    rejected = replace(audit, checks=checks)

    assert rejected.production_ready(SENTIMENT_REQUIRED_GATES) is False
    assert rejected.blockers(SENTIMENT_REQUIRED_GATES) == (failed_gate,)


def test_UT_SENTIMENT_GATE_REJECTS_INCOMPLETE_AUDIT_SCHEMA():
    audit = replace(_passing_audit("sentiment", SENTIMENT_REQUIRED_GATES), checks=())

    with pytest.raises(ValueError, match="missing required gate"):
        audit.production_ready(SENTIMENT_REQUIRED_GATES)


def test_UT_OPTIONS_ENTITLEMENTS_REMAIN_UNCOMPOSED():
    assert set(OPTIONS_ENTITLEMENTS) == {"flowalgo", "cheddarflow", "opra_vendor", "yfinance"}
    assert all(not options_provider_ready(name) for name in OPTIONS_ENTITLEMENTS)
    for audit in OPTIONS_ENTITLEMENTS.values():
        assert audit.blockers(OPTIONS_REQUIRED_GATES)


def test_UT_OPTIONS_GATE_CAN_PASS_ONLY_WITH_EVERY_RECORDED_RIGHT():
    audit = _passing_audit("options_flow", OPTIONS_REQUIRED_GATES)

    assert audit.production_ready(OPTIONS_REQUIRED_GATES) is True
