import gzip
import json
from datetime import datetime, timedelta

import httpx
import pytest

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.discovery_registry import DISCOVERY_ISSUER_INDEX
from catalyst_edge_mcp.evidence_store import EvidenceStore
from catalyst_edge_mcp.gdelt_web_ngrams import (
    GDELT_WEB_NGRAMS_BASE,
    GdeltWebNgramsRefresher,
)
from catalyst_edge_mcp.models import SourceStatus

NOW = datetime(2026, 7, 14, 23, 6, tzinfo=UTC)
STAMP = "20260714230100"


def _gzip_lines(*lines: str) -> bytes:
    return gzip.compress(("\n".join(lines) + "\n").encode())


def _transport(request: httpx.Request) -> httpx.Response:
    target = str(request.url)
    toc_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    ngrams_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz"
    if request.method == "HEAD":
        if target == toc_url:
            return httpx.Response(200, headers={"Content-Length": "512"})
        return httpx.Response(404)
    if target == ngrams_url:
        return httpx.Response(
            200,
            content=_gzip_lines(
                "1\tNVIDIA Corporation launches new\t2",
                "1\tNVIDIA launches new platform\t1",
                "2\tRocket Lab USA signs\t1",
                "3\tApple fruit growers report\t1",
            ),
        )
    if target == toc_url:
        return httpx.Response(
            200,
            content=_gzip_lines(
                json.dumps(
                    {
                        "ID": 1,
                        "date": "2026-07-14T23:01:00.000Z",
                        "lang": "en",
                        "title": "NVIDIA launches a new platform",
                        "url": "https://publisher.example/nvidia-platform",
                    }
                ),
                json.dumps(
                    {
                        "ID": 2,
                        "date": "2026-07-14T23:01:00.000Z",
                        "lang": "en",
                        "title": "Rocket Lab signs a launch agreement",
                        "url": "https://space.example/rocket-lab-agreement",
                    }
                ),
                json.dumps(
                    {
                        "ID": 3,
                        "date": "2026-07-14T23:01:00.000Z",
                        "lang": "en",
                        "title": "Apple growers report a strong harvest",
                        "url": "https://fruit.example/apple-harvest",
                    }
                ),
            ),
        )
    raise AssertionError(f"unexpected request: {request.method} {target}")


@pytest.mark.asyncio
async def test_web_ngrams_batch_download_matches_multiple_issuers_once(tmp_path):
    requests = []

    def transport(request):
        requests.append((request.method, str(request.url)))
        return _transport(request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        results = await refresher.refresh(["NVDA", "RKLB", "AAPL"], 14)

    assert results["NVDA"].status == SourceStatus.FRESH
    assert results["NVDA"].evidence_count == 1
    assert results["NVDA"].matched_documents == 1
    assert results["RKLB"].status == SourceStatus.FRESH
    assert results["RKLB"].evidence_count == 1
    assert results["AAPL"].status == SourceStatus.NO_OBSERVATIONS
    assert results["AAPL"].evidence_count == 0
    assert requests.count(("GET", f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz")) == 1
    assert requests.count(("GET", f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz")) == 1


@pytest.mark.asyncio
async def test_web_ngrams_stores_metadata_only_with_provenance(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(_transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            store=store,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        await refresher.refresh(["NVDA"], 14)

    issuer = DISCOVERY_ISSUER_INDEX["NVDA"]
    event = store.list_events_for_source(
        issuer.issuer_key, "gdelt", NOW - timedelta(days=1)
    )[0]
    assert event.title == "NVIDIA launches a new platform"
    assert event.primary_source.parser_version.startswith("gdelt-web-ngrams-v2+")
    assert event.primary_source.raw_sha256
    assert event.primary_source.canonical_url == "https://publisher.example/nvidia-platform"
    state = store.collector_state("gdelt", issuer.issuer_key)
    assert state["status"] == SourceStatus.FRESH.value
    assert state["last_success_at"] == NOW.isoformat()
    audit = store.entity_match_audits(issuer.issuer_key)
    assert len(audit) == 1
    assert audit[0]["accepted"] is True
    assert audit[0]["reason_code"] == "accepted"
    assert audit[0]["selected_rule_id"] == "nvidia_corporation_legal_name"


@pytest.mark.asyncio
async def test_web_ngrams_preserves_multilingual_titles_and_skips_symbol_only_titles(
    tmp_path,
):
    toc_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    ngrams_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz"

    def transport(request):
        target = str(request.url)
        if request.method == "HEAD":
            return httpx.Response(
                200 if target == toc_url else 404,
                headers={"Content-Length": "512"},
            )
        if target == ngrams_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    "1\tNVIDIA Corporation launches new\t1",
                    "2\tNVIDIA Corporation market update\t1",
                ),
            )
        if target == toc_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    json.dumps(
                        {
                            "ID": 1,
                            "date": "2026-07-14T23:01:00.000Z",
                            "lang": "ru",
                            "title": "Уход спонсоров Гейтса: последние новости",
                            "url": "https://publisher.example/multilingual-title",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "ID": 2,
                            "date": "2026-07-14T23:01:00.000Z",
                            "lang": "en",
                            "title": "🔥 !!!",
                            "url": "https://publisher.example/symbol-only-title",
                        }
                    ),
                ),
            )
        raise AssertionError(f"unexpected request: {request.method} {target}")

    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            store=store,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        result = (await refresher.refresh(["NVDA"], 14))["NVDA"]

    events = store.list_events_for_source(
        DISCOVERY_ISSUER_INDEX["NVDA"].issuer_key,
        "gdelt",
        NOW - timedelta(days=1),
    )
    assert result.status == SourceStatus.FRESH
    assert result.degraded is False
    assert result.matched_documents == 1
    assert [event.title for event in events] == [
        "Уход спонсоров Гейтса: последние новости"
    ]


@pytest.mark.asyncio
async def test_web_ngrams_no_recent_file_is_typed_stale(tmp_path):
    def transport(request):
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=6,
        )
        result = (await refresher.refresh(["NVDA"], 14))["NVDA"]

    assert result.status == SourceStatus.STALE
    assert result.degraded is True
    assert result.files_processed == 0
    assert "NoRecentWebNgramsFile" in result.warnings[0]


@pytest.mark.asyncio
async def test_web_ngrams_rejects_malformed_gzip_without_leaking_content(tmp_path):
    def transport(request):
        if request.method == "HEAD":
            return httpx.Response(200, headers={"Content-Length": "20"})
        return httpx.Response(200, content=b"secret malformed compressed payload")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        result = (await refresher.refresh(["NVDA"], 14))["NVDA"]

    assert result.status == SourceStatus.SCHEMA_ERROR
    assert result.degraded is True
    assert "secret malformed compressed payload" not in repr(result)


def test_web_ngrams_endpoint_is_exact_https_google_storage_path():
    valid = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    GdeltWebNgramsRefresher._require_endpoint(valid)
    with pytest.raises(ValueError):
        GdeltWebNgramsRefresher._require_endpoint(valid.replace("https://", "http://"))
    with pytest.raises(ValueError):
        GdeltWebNgramsRefresher._require_endpoint(
            valid.replace("storage.googleapis.com", "attacker.example")
        )


@pytest.mark.asyncio
async def test_tsla_entity_rules_reject_noise_and_accept_company_context(tmp_path):
    toc_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    ngrams_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz"

    def transport(request):
        target = str(request.url)
        if request.method == "HEAD":
            return httpx.Response(
                200 if target == toc_url else 404,
                headers={"Content-Length": "512"},
            )
        if target == ngrams_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    "1\tNikola Tesla coil museum\t1",
                    "2\tTesla appears in documentary\t1",
                    "3\tTesla vehicle deliveries rise\t1",
                    "4\tTesla Energy battery deployment\t1",
                ),
            )
        if target == toc_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    *(
                        json.dumps(
                            {
                                "ID": document_id,
                                "date": "2026-07-14T23:01:00.000Z",
                                "lang": "en",
                                "title": f"Candidate article {document_id}",
                                "url": f"https://publisher.example/tesla-{document_id}",
                            }
                        )
                        for document_id in range(1, 5)
                    )
                ),
            )
        raise AssertionError(f"unexpected request: {request.method} {target}")

    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            store=store,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        result = (await refresher.refresh(["TSLA"], 14))["TSLA"]

    issuer = DISCOVERY_ISSUER_INDEX["TSLA"]
    events = store.list_events_for_source(issuer.issuer_key, "gdelt", NOW - timedelta(days=1))
    audits = store.entity_match_audits(issuer.issuer_key)
    assert result.status == SourceStatus.FRESH
    assert result.candidate_documents == 4
    assert result.accepted_documents == 2
    assert result.matched_documents == 2
    assert result.rejected_documents == 2
    assert dict(result.rejection_reasons) == {
        "missing_required_context": 1,
        "negative_context": 1,
    }
    assert len(events) == 2
    assert len(audits) == 4
    assert {item["reason_code"] for item in audits if not item["accepted"]} == {
        "missing_required_context",
        "negative_context",
    }
    accepted_rules = {
        item["selected_rule_id"] for item in audits if item["accepted"]
    }
    assert accepted_rules == {"tesla_brand_contextual", "tesla_energy_brand"}
    assert all(len(item["context_sha256"]) == 64 for item in audits)
    assert all("quadgram" not in item for item in audits)


@pytest.mark.asyncio
async def test_reject_only_refresh_is_successful_no_observations(tmp_path):
    toc_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    ngrams_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz"

    def transport(request):
        target = str(request.url)
        if request.method == "HEAD":
            return httpx.Response(
                200 if target == toc_url else 404,
                headers={"Content-Length": "512"},
            )
        if target == ngrams_url:
            return httpx.Response(200, content=_gzip_lines("1\tNikola Tesla coil museum\t1"))
        if target == toc_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    json.dumps(
                        {
                            "ID": 1,
                            "date": "2026-07-14T23:01:00.000Z",
                            "lang": "en",
                            "title": "Museum restores a historic electrical coil",
                            "url": "https://publisher.example/nikola-tesla-museum",
                        }
                    )
                ),
            )
        raise AssertionError(f"unexpected request: {request.method} {target}")

    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            store=store,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        result = (await refresher.refresh(["TSLA"], 14))["TSLA"]

    issuer = DISCOVERY_ISSUER_INDEX["TSLA"]
    assert result.status == SourceStatus.NO_OBSERVATIONS
    assert result.degraded is False
    assert result.candidate_documents == 1
    assert result.accepted_documents == 0
    assert result.rejected_documents == 1
    assert dict(result.rejection_reasons) == {"negative_context": 1}
    assert store.list_events_for_source(issuer.issuer_key, "gdelt", NOW - timedelta(days=1)) == []
    assert store.collector_state("gdelt", issuer.issuer_key)["status"] == SourceStatus.FRESH.value


@pytest.mark.asyncio
async def test_rejected_candidates_do_not_starve_later_accepted_match(tmp_path):
    toc_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.toc.json.gz"
    ngrams_url = f"{GDELT_WEB_NGRAMS_BASE}/{STAMP}.ngrams.txt.gz"
    rejected_lines = tuple(
        f"{document_id}\tTesla documentary subject\t1" for document_id in range(1, 61)
    )

    def transport(request):
        target = str(request.url)
        if request.method == "HEAD":
            return httpx.Response(
                200 if target == toc_url else 404,
                headers={"Content-Length": "4096"},
            )
        if target == ngrams_url:
            return httpx.Response(
                200,
                content=_gzip_lines(*rejected_lines, "61\tTesla vehicle deliveries rise\t1"),
            )
        if target == toc_url:
            return httpx.Response(
                200,
                content=_gzip_lines(
                    *(
                        json.dumps(
                            {
                                "ID": document_id,
                                "date": "2026-07-14T23:01:00.000Z",
                                "lang": "en",
                                "title": f"Candidate {document_id}",
                                "url": f"https://publisher.example/candidate-{document_id}",
                            }
                        )
                        for document_id in range(1, 62)
                    )
                ),
            )
        raise AssertionError(f"unexpected request: {request.method} {target}")

    async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
        result = (
            await GdeltWebNgramsRefresher(
                str(tmp_path / "events.sqlite3"),
                registry=DISCOVERY_ISSUER_INDEX,
                client=client,
                clock=lambda: NOW,
                candidate_minutes=5,
                max_files=1,
            ).refresh(["TSLA"], 14)
        )["TSLA"]

    assert result.candidate_documents == 61
    assert result.rejected_documents == 60
    assert result.accepted_documents == 1
    assert result.ingested_documents == 1
    assert result.matched_documents == 1


@pytest.mark.asyncio
async def test_entity_match_audit_is_idempotent_for_replayed_minute(tmp_path):
    store = EvidenceStore(str(tmp_path / "events.sqlite3"))
    async with httpx.AsyncClient(transport=httpx.MockTransport(_transport)) as client:
        refresher = GdeltWebNgramsRefresher(
            str(tmp_path / "events.sqlite3"),
            registry=DISCOVERY_ISSUER_INDEX,
            store=store,
            client=client,
            clock=lambda: NOW,
            candidate_minutes=5,
            max_files=1,
        )
        await refresher.refresh(["NVDA"], 14)
        await refresher.refresh(["NVDA"], 14)

    issuer_key = DISCOVERY_ISSUER_INDEX["NVDA"].issuer_key
    assert len(store.entity_match_audits(issuer_key)) == 1
    assert store.entity_match_audit_summary(issuer_key) == {
        "candidate_documents": 1,
        "accepted_documents": 1,
        "rejected_documents": 0,
        "rejection_reasons": {},
    }
