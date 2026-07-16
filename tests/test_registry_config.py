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


def test_packaged_reviewed_registry_preserves_existing_defaults():
    bundle = load_registry_bundle(DEFAULT_REGISTRY_PATH)

    assert set(bundle.issuer_feed_index) == {"AAPL", "NVDA"}
    assert set(bundle.discovery_index) == {"AAPL", "NVDA", "TSLA", "RKLB", "BRK-A", "BRK-B"}
    assert set(bundle.social_index) == {"AAPL", "NVDA", "TSLA", "RKLB", "BRK-A", "BRK-B"}
    assert bundle.discovery_index["NVDA"].query_aliases == (
        "NVIDIA",
        "NVIDIA Corporation",
    )
    assert bundle.publisher_quality_index["reuters.com"].quality == 0.70
    assert bundle.publisher_quality_index["businesswire.com"].tier == (
        "release_distribution"
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
