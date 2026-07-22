import json

import pytest

from catalyst_edge_mcp.collection_lifecycle import GdeltCollectionLifecycle
from catalyst_edge_mcp.registry_config import (
    DEFAULT_REGISTRY_PATH,
    load_registry_bundle,
)
from catalyst_edge_mcp.server import build_service
from catalyst_edge_mcp.settings import Settings


def _issuer(
    *,
    issuer_key="CIK0000789019",
    issuer_name="Microsoft Corporation",
    tickers=None,
    discovery_aliases=None,
    social_aliases=None,
    issuer_feed=None,
):
    return {
        "issuer_key": issuer_key,
        "issuer_name": issuer_name,
        "tickers": tickers or ["MSFT"],
        "reviewed_on": "2026-07-15",
        "discovery_aliases": discovery_aliases or ["Microsoft Corporation"],
        "social_aliases": social_aliases or ["Microsoft"],
        "issuer_feed": issuer_feed,
    }


def _write_registry(tmp_path, issuers):
    path = tmp_path / "registries.json"
    path.write_text(json.dumps({"version": 1, "issuers": issuers}))
    return path


def _rule(**overrides):
    rule = {
        "rule_id": "microsoft_legal_name",
        "version": "1",
        "alias": "Microsoft Corporation",
        "alias_kind": "legal_name",
        "match_mode": "phrase",
        "required_context": [],
        "negative_context": [],
        "valid_from": None,
        "valid_to": None,
        "canonical_cik": "CIK0000789019",
        "reviewed_on": "2026-07-21",
        "review_note": "Reviewed fixture rule.",
    }
    rule.update(overrides)
    return rule


def _write_v2_registry(tmp_path, rules, *, funds=None):
    issuer = _issuer()
    issuer.pop("discovery_aliases")
    issuer["discovery_rules"] = rules
    path = tmp_path / "registries-v2.json"
    payload = {"version": 2, "issuers": [issuer]}
    if funds is not None:
        payload["funds"] = funds
    path.write_text(json.dumps(payload))
    return path


def _fund(**overrides):
    fund = {
        "fund_name": "Fixture ETF",
        "registrant_cik": "CIK0001067839",
        "series_id": "S000101292",
        "class_id": "C000271435",
        "identity_status": "official_series_class",
        "ticker_versions": [
            {"ticker": "QQQ", "valid_from": None, "valid_to": None, "status": "active"}
        ],
        "sponsor_source": {
            "sponsor_name": "Fixture Sponsor",
            "notice_url": "https://funds.example.com/qqq",
            "official_hosts": ["funds.example.com"],
            "reviewed_on": "2026-07-21",
            "review_note": "Reviewed fixture sponsor source.",
        },
        "reviewed_on": "2026-07-21",
        "review_note": "Reviewed fixture fund identity.",
    }
    fund.update(overrides)
    return fund


def test_packaged_reviewed_registry_preserves_existing_defaults():
    bundle = load_registry_bundle(DEFAULT_REGISTRY_PATH)

    assert set(bundle.issuer_feed_index) == {"AAPL", "NVDA"}
    assert set(bundle.discovery_index) == {"AAPL", "NVDA", "TSLA", "RKLB", "BRK-A", "BRK-B"}
    assert set(bundle.social_index) == {"AAPL", "NVDA", "TSLA", "RKLB", "BRK-A", "BRK-B"}
    assert bundle.discovery_index["NVDA"].query_aliases == (
        "NVIDIA",
        "NVIDIA Corporation",
    )
    assert bundle.discovery_index["TSLA"].query_aliases == (
        "Tesla Inc",
        "Tesla Motors",
        "Tesla Energy",
        "Tesla",
    )
    assert bundle.discovery_index["TSLA"].entity_rules[2].required_context == (
        "battery",
        "storage",
        "Megapack",
        "Powerwall",
        "solar",
        "deployment",
    )
    assert bundle.publisher_quality_index["reuters.com"].quality == 0.70
    assert bundle.publisher_quality_index["businesswire.com"].tier == (
        "release_distribution"
    )
    assert set(bundle.fund_identity_index) == {
        "SPY",
        "QQQ",
        "DIA",
        "IWM",
        "XLE",
        "XLK",
        "GLD",
        "GDX",
    }
    expected_ids = {
        "QQQ": ("CIK0001067839", "S000101292", "C000271435"),
        "IWM": ("CIK0001100663", "S000004344", "C000012074"),
        "XLE": ("CIK0001064641", "S000006410", "C000017596"),
        "XLK": ("CIK0001064641", "S000006415", "C000017601"),
        "GDX": ("CIK0001137360", "S000009191", "C000024980"),
    }
    for ticker, identifiers in expected_ids.items():
        fund = bundle.fund_identity_index[ticker]
        assert (fund.registrant_cik, fund.series_id, fund.class_id) == identifiers
        assert fund.identity_status == "official_series_class"
        assert fund.ticker_versions[0].status == "active"
        assert fund.sponsor_source.notice_url.startswith("https://")
    assert bundle.fund_identity_index["SPY"].identity_status == (
        "unsupported_no_series_class"
    )
    assert bundle.fund_identity_index["DIA"].identity_status == (
        "unsupported_no_series_class"
    )
    assert bundle.fund_identity_index["GLD"].identity_status == (
        "unsupported_non_investment_company"
    )


def test_custom_registry_composes_all_collectors_from_one_validated_file(tmp_path):
    feed = {
        "feed_url": "https://news.microsoft.com/source/feed/",
        "official_hosts": ["news.microsoft.com"],
        "refresh_seconds": 900,
        "review_note": "Issuer-controlled public feed; metadata and links only.",
    }
    path = _write_registry(tmp_path, [_issuer(issuer_feed=feed)])
    settings = Settings(
        registry_path=str(path),
        evidence_store_path=str(tmp_path / "events.sqlite3"),
    )

    service = build_service(settings)
    registries = {adapter.provider: adapter.registry for adapter in service.adapters}

    assert set(registries) == {"issuer_feed", "gdelt", "bluesky"}
    assert set(registries["issuer_feed"]) == {"MSFT"}
    assert set(registries["gdelt"]) == {"MSFT"}
    assert set(registries["bluesky"]) == {"MSFT"}
    assert registries["gdelt"]["MSFT"].issuer_key == "CIK0000789019"

    lifecycle = GdeltCollectionLifecycle(settings)
    try:
        assert lifecycle.tickers == ("MSFT",)
        assert set(lifecycle.discovery_index) == {"MSFT"}
    finally:
        lifecycle.store.close()


def test_registry_rejects_unknown_fields(tmp_path):
    issuer = _issuer()
    issuer["unreviewed_option"] = True
    path = _write_registry(tmp_path, [issuer])

    with pytest.raises(ValueError, match="unknown fields"):
        load_registry_bundle(path)


def test_registry_rejects_duplicate_ticker_ownership(tmp_path):
    path = _write_registry(
        tmp_path,
        [
            _issuer(),
            _issuer(
                issuer_key="CIK0001652044",
                issuer_name="Alphabet Inc.",
                tickers=["MSFT"],
                discovery_aliases=["Alphabet Inc"],
                social_aliases=["Alphabet"],
            ),
        ],
    )

    with pytest.raises(ValueError, match="assigned to multiple issuers"):
        load_registry_bundle(path)


def test_registry_rejects_ambiguous_cross_issuer_aliases(tmp_path):
    path = _write_registry(
        tmp_path,
        [
            _issuer(discovery_aliases=["Shared Company"]),
            _issuer(
                issuer_key="CIK0001652044",
                issuer_name="Alphabet Inc.",
                tickers=["GOOG"],
                discovery_aliases=["shared company"],
                social_aliases=["Alphabet"],
            ),
        ],
    )

    with pytest.raises(ValueError, match="Ambiguous discovery alias"):
        load_registry_bundle(path)


def test_registry_rejects_feed_outside_exact_official_host(tmp_path):
    feed = {
        "feed_url": "https://attacker.example/source/feed/",
        "official_hosts": ["news.microsoft.com"],
        "refresh_seconds": 900,
        "review_note": "Issuer-controlled public feed; metadata and links only.",
    }
    path = _write_registry(tmp_path, [_issuer(issuer_feed=feed)])

    with pytest.raises(ValueError, match="host must be listed"):
        load_registry_bundle(path)


def test_registry_rejects_noncanonical_ticker_aliases(tmp_path):
    path = _write_registry(tmp_path, [_issuer(tickers=["brk.b"])])

    with pytest.raises(ValueError, match="canonical uppercase dash tickers"):
        load_registry_bundle(path)


def test_registry_v1_aliases_translate_to_compatibility_rules(tmp_path):
    bundle = load_registry_bundle(_write_registry(tmp_path, [_issuer()]))

    issuer = bundle.discovery_index["MSFT"]
    assert issuer.query_aliases == ("Microsoft Corporation",)
    assert issuer.entity_rules == ()
    assert issuer.effective_entity_rules[0].rule_id == "legacy_alias_1"


def test_registry_v2_loads_per_alias_entity_rules(tmp_path):
    bundle = load_registry_bundle(_write_v2_registry(tmp_path, [_rule()]))

    rule = bundle.discovery_index["MSFT"].entity_rules[0]
    assert rule.rule_id == "microsoft_legal_name"
    assert rule.canonical_cik == "CIK0000789019"
    assert rule.match_mode == "phrase"


@pytest.mark.parametrize(
    ("rules", "message"),
    [
        (
            [_rule(), _rule(alias="Microsoft Corp")],
            "duplicate rule_id",
        ),
        ([_rule(alias_kind="executive")], "alias_kind is not supported"),
        ([_rule(match_mode="substring")], "match_mode is not supported"),
        (
            [_rule(valid_from="2026-07-22", valid_to="2026-07-21")],
            "validity window is reversed",
        ),
        (
            [_rule(required_context=["cloud"], negative_context=["CLOUD"])],
            "required and negative context overlap",
        ),
        (
            [_rule(canonical_cik="CIK0001652044")],
            "canonical_cik must match",
        ),
    ],
)
def test_registry_v2_rejects_invalid_entity_rules(tmp_path, rules, message):
    with pytest.raises(ValueError, match=message):
        load_registry_bundle(_write_v2_registry(tmp_path, rules))


@pytest.mark.parametrize(
    ("fund", "message"),
    [
        (_fund(class_id=None), "requires series_id and class_id"),
        (
            _fund(identity_status="unsupported_no_series_class"),
            "must not invent series/class IDs",
        ),
        (
            _fund(
                sponsor_source={
                    "sponsor_name": "Fixture Sponsor",
                    "notice_url": "https://attacker.example/qqq",
                    "official_hosts": ["funds.example.com"],
                    "reviewed_on": "2026-07-21",
                    "review_note": "Reviewed fixture sponsor source.",
                }
            ),
            "official host",
        ),
        (
            _fund(
                ticker_versions=[
                    {
                        "ticker": "QQQ",
                        "valid_from": "2020-01-01",
                        "valid_to": None,
                        "status": "active",
                    },
                    {
                        "ticker": "QQQ",
                        "valid_from": "2025-01-01",
                        "valid_to": None,
                        "status": "active",
                    },
                ]
            ),
            "overlapping versions",
        ),
    ],
)
def test_registry_v2_rejects_invalid_fund_identity(tmp_path, fund, message):
    with pytest.raises(ValueError, match=message):
        load_registry_bundle(_write_v2_registry(tmp_path, [_rule()], funds=[fund]))
