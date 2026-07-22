from datetime import datetime

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX
from catalyst_edge_mcp.entity_resolution import (
    decide_entity_candidate,
    match_entity_rules,
    ruleset_version,
)

TSLA = DISCOVERY_ISSUER_INDEX["TSLA"]


def _decision(text: str, year: int = 2026):
    return decide_entity_candidate(
        TSLA,
        match_entity_rules(text, TSLA),
        datetime(year, 7, 21, tzinfo=UTC),
    )


def test_entity_ruleset_version_changes_with_rule_content():
    assert ruleset_version(TSLA).startswith("entity-rules-v2:")
    assert len(ruleset_version(TSLA).split(":", 1)[1]) == 64


def test_tesla_former_name_respects_publication_validity():
    assert _decision("Tesla Motors announces update", 2016).accepted is True
    current = _decision("Tesla Motors announces update", 2026)
    assert current.accepted is False
    assert current.reason_code == "outside_validity"


def test_tesla_energy_requires_reviewed_product_context():
    missing = _decision("Tesla Energy appears in documentary")
    accepted = _decision("Tesla Energy battery deployment")

    assert missing.accepted is False
    assert missing.reason_code == "missing_required_context"
    assert accepted.accepted is True
    assert accepted.selected_rule_id == "tesla_energy_brand"


def test_negative_context_overrides_positive_issuer_terms():
    decision = _decision("Nikola Tesla Inc museum")

    assert decision.accepted is False
    assert decision.reason_code == "negative_context"
    assert set(decision.negative_context_matches) == {"Nikola", "museum"}
