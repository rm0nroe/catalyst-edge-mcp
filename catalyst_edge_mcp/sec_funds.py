"""SEC-backed fund identity plus neutral N-CEN and NPORT evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import PurePosixPath
from typing import Any

import httpx
from lxml import etree

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    EvidenceContext,
    PolicyDecision,
    ReasonCode,
    ReasonScope,
    Source,
    SourceStatus,
)
from catalyst_edge_mcp.reason_records import scoped_reason
from catalyst_edge_mcp.registry_models import FundIdentity
from catalyst_edge_mcp.sec_filings import SEC_GATE

SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
TRACKED_FUND_FORMS = frozenset({"N-CEN", "N-CEN/A", "NPORT-P", "NPORT-P/A"})
MAX_FUND_DOCUMENT_BYTES = 25_000_000
PARSER_VERSION = "sec-funds-v1"


class SecFundAdapter:
    """Collect fund-only regulatory context without corporate or insider inference."""

    family = "filings_news"
    provider = "sec_funds"

    def __init__(
        self,
        user_agent: str,
        *,
        registry: Mapping[str, FundIdentity],
        client: httpx.AsyncClient | None = None,
        clock=None,
    ) -> None:
        if "@" not in user_agent:
            raise ValueError("SEC User-Agent must include a contact email address")
        self.user_agent = user_agent
        self.registry = registry
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))

    def supports(self, ticker: str) -> bool:
        return ticker in self.registry

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        if self._client is not None:
            return await self._collect(self._client, ticker, lookback_days)
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, application/xml, text/xml",
        }
        async with httpx.AsyncClient(
            headers=headers,
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            return await self._collect(client, ticker, lookback_days)

    async def _collect(
        self,
        client: httpx.AsyncClient,
        ticker: str,
        lookback_days: int,
    ) -> AdapterResult:
        now = self._as_utc(self._clock())
        fund = self.registry.get(ticker)
        if fund is None:
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                status=SourceStatus.NO_OBSERVATIONS,
                policy_decision=PolicyDecision.APPROVED,
                collected_at=now,
            )
        if fund.identity_status != "official_series_class":
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                warnings=[
                    f"{ticker} fund identity is typed {fund.identity_status}; "
                    "no series/class identity was inferred."
                ],
                status=SourceStatus.UNSUPPORTED,
                policy_decision=PolicyDecision.APPROVED,
                collected_at=now,
                reason_records=[
                    scoped_reason(
                        ReasonCode.SOURCE_UNSUPPORTED,
                        ReasonScope.EVALUATION,
                        ticker,
                        source_id=self.provider,
                        family=self.family,
                        observed_at=now,
                        detail=fund.identity_status,
                    )
                ],
            )

        cik = fund.registrant_cik.removeprefix("CIK")
        payload = await self._get_json(client, SUBMISSIONS_URL.format(cik=cik))
        entries = self._recent_entries(
            payload,
            cutoff=now - timedelta(days=lookback_days),
            expected_cik=cik,
        )
        evidence: list[Evidence] = []
        warnings: list[str] = []
        reasons = []
        for entry in entries:
            accession = entry["accession"]
            try:
                content = await self._get_bounded_bytes(client, entry["url"])
                facts = self._parse_document(content, form=entry["form"], fund=fund)
                evidence.append(
                    self._evidence(
                        fund=fund,
                        ticker=ticker,
                        entry=entry,
                        facts=facts,
                        content=content,
                        retrieved_at=now,
                    )
                )
            except (httpx.HTTPError, ValueError, etree.XMLSyntaxError):
                warnings.append(
                    f"SEC fund filing {accession} was unavailable, oversized, or invalid."
                )
                reasons.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNAVAILABLE,
                        ReasonScope.CANDIDATE,
                        accession,
                        source_id=self.provider,
                        family=self.family,
                        observed_at=entry["filed_at"],
                        detail="fund_document_unavailable_or_invalid",
                    )
                )
        if not evidence and not warnings:
            warnings.append(
                f"No N-CEN or NPORT filings found for {ticker} in the lookback window."
            )
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            status=(
                SourceStatus.FRESH
                if evidence
                else SourceStatus.UNAVAILABLE
                if warnings and entries
                else SourceStatus.NO_OBSERVATIONS
            ),
            policy_decision=PolicyDecision.APPROVED,
            collected_at=now,
            reason_records=reasons,
        )

    @classmethod
    def _recent_entries(
        cls,
        payload: dict[str, Any],
        *,
        cutoff: datetime,
        expected_cik: str,
    ) -> list[dict[str, Any]]:
        recent = payload.get("filings", {}).get("recent", {})
        if not isinstance(recent, dict) or not isinstance(recent.get("form"), list):
            raise ValueError("Unexpected SEC submissions schema")
        cik = str(payload.get("cik") or "").zfill(10)
        if not cik.isdigit() or cik != expected_cik:
            raise ValueError("SEC submissions CIK does not match reviewed fund identity")
        entries: list[dict[str, Any]] = []
        for index, form in enumerate(recent["form"]):
            if form not in TRACKED_FUND_FORMS:
                continue
            filed_at = cls._parse_datetime(cls._at(recent, "acceptanceDateTime", index))
            if filed_at is None:
                filed_at = cls._parse_datetime(cls._at(recent, "filingDate", index))
            if filed_at is None or filed_at < cutoff:
                continue
            accession = str(cls._at(recent, "accessionNumber", index) or "")
            primary_document = str(cls._at(recent, "primaryDocument", index) or "")
            if not accession or not primary_document:
                continue
            document = PurePosixPath(primary_document).name
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession.replace('-', '')}/{document}"
            )
            entries.append(
                {
                    "form": form,
                    "accession": accession,
                    "filed_at": filed_at,
                    "filing_date": str(cls._at(recent, "filingDate", index) or ""),
                    "report_date": str(cls._at(recent, "reportDate", index) or "") or None,
                    "url": url,
                }
            )
        return entries

    @classmethod
    def _parse_document(
        cls,
        content: bytes,
        *,
        form: str,
        fund: FundIdentity,
    ) -> dict[str, Any]:
        parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
        root = etree.fromstring(content, parser=parser)
        submission_type = cls._first_text(root, "submissionType")
        if submission_type != form:
            raise ValueError("SEC fund document form does not match submissions metadata")

        cik_values = {
            value.zfill(10)
            for name in ("cik", "regCik", "registrantCik")
            for value in cls._all_text(root, name)
            if value.isdigit()
        }
        expected_cik = fund.registrant_cik.removeprefix("CIK")
        if expected_cik not in cik_values:
            raise ValueError("SEC fund document CIK does not match reviewed identity")

        if form.startswith("NPORT"):
            series_ids = set(cls._all_text(root, "seriesId"))
            class_ids = set(cls._all_text(root, "classId")) | set(
                cls._all_attributes(root, "classId")
            )
            if fund.series_id not in series_ids or fund.class_id not in class_ids:
                raise ValueError("NPORT series/class does not match reviewed identity")
            report_date = cls._first_text(root, "repPdDate")
            reporting_period_end = cls._first_text(root, "repPdEnd")
            return {
                "report_date": report_date,
                "reporting_period_end": reporting_period_end,
                "series_name": cls._first_text(root, "seriesName"),
                "is_final_filing": cls._first_text(root, "isFinalFiling"),
                "holdings_count": len(root.xpath(".//*[local-name()='invstOrSec']")),
            }

        report_end = cls._first_attribute(root, "generalInfo", "reportEndingPeriod")
        return {
            "report_date": report_end,
            "reporting_period_end": report_end,
            "investment_company_type": cls._first_text(root, "investmentCompanyType"),
            "registrant_name": cls._first_text(root, "registrantFullName"),
        }

    @classmethod
    def _evidence(
        cls,
        *,
        fund: FundIdentity,
        ticker: str,
        entry: dict[str, Any],
        facts: dict[str, Any],
        content: bytes,
        retrieved_at: datetime,
    ) -> Evidence:
        form = entry["form"]
        base_form = form.removesuffix("/A")
        report_date = facts.get("report_date") or entry.get("report_date") or "unknown"
        reporting_period_end = facts.get("reporting_period_end") or report_date
        is_amendment = form.endswith("/A")
        if base_form == "NPORT-P":
            signal = "sec_fund_nport_report"
            event_type = "fund_nport_holdings_report"
            event_label = "Fund portfolio holdings report"
            why = (
                "NPORT is lagged, as-filed portfolio context. It does not establish "
                "current holdings, real-time flows, or a directional catalyst."
            )
            description = (
                f"SEC {form} reported {facts.get('holdings_count', 0)} holdings for "
                f"{ticker} as of {report_date}; period end {reporting_period_end}; "
                f"accepted {entry['filed_at'].isoformat()}."
            )
        else:
            signal = "sec_fund_ncen_report"
            event_type = "fund_ncen_annual_report"
            event_label = "Fund annual census report"
            why = (
                "N-CEN is annual, as-filed fund structure and classification context. "
                "It is not corporate operating news or a directional catalyst."
            )
            description = (
                f"SEC {form} reported annual fund context for {ticker} through "
                f"{reporting_period_end}; accepted {entry['filed_at'].isoformat()}."
            )
        sponsor_url = fund.sponsor_source.notice_url
        source = Source(
            name=f"SEC EDGAR {form}",
            source_id=cls.provider,
            source_tier="primary_regulator",
            url=entry["url"],
            canonical_url=entry["url"],
            accession_or_record_id=entry["accession"],
            published_at=entry["filed_at"],
            observed_at=entry["filed_at"],
            retrieved_at=retrieved_at,
            raw_sha256=hashlib.sha256(content).hexdigest(),
            parser_version=PARSER_VERSION,
            policy_decision=PolicyDecision.APPROVED,
            related_sources=[sponsor_url],
        )
        return Evidence(
            family=cls.family,
            signal=signal,
            direction=Direction.NEUTRAL,
            strength=0.25,
            confidence=1.0,
            timestamp=entry["filed_at"],
            source_quality=1.0,
            change=Change(description=description),
            context=EvidenceContext(
                event_type=event_type,
                event_label=event_label,
                novelty="amendment" if is_amendment else "as_filed",
                materiality="research_only",
                why_it_matters=why,
                source_record_count=1,
                source_tiers=["primary_regulator"],
            ),
            sources=[source],
            notes=(
                "Fund-only neutral evidence. Sponsor-primary URL is reviewed metadata; "
                "no sponsor notice, constituent event, flow, or insider inference is made."
            ),
            raw_signal={
                "form": form,
                "ticker": ticker,
                "registrant_cik": fund.registrant_cik,
                "series_id": fund.series_id,
                "class_id": fund.class_id,
                "identity_status": fund.identity_status,
                "report_date": report_date,
                "reporting_period_end": reporting_period_end,
                "filing_date": entry["filing_date"],
                "accepted_at": entry["filed_at"].isoformat(),
                "sponsor_name": fund.sponsor_source.sponsor_name,
                "sponsor_notice_url": sponsor_url,
                **facts,
            },
        )

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        async with SEC_GATE.request():
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected SEC JSON schema")
        return payload

    async def _get_bounded_bytes(self, client: httpx.AsyncClient, url: str) -> bytes:
        parts: list[bytes] = []
        size = 0
        async with SEC_GATE.request(), client.stream("GET", url) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > MAX_FUND_DOCUMENT_BYTES:
                    raise ValueError("SEC fund document exceeded the bounded response size")
                parts.append(chunk)
        return b"".join(parts)

    @staticmethod
    def _all_text(root, local_name: str) -> list[str]:
        values = root.xpath(f".//*[local-name()='{local_name}']/text()")
        return [" ".join(str(value).split()) for value in values if str(value).strip()]

    @staticmethod
    def _all_attributes(root, attribute_name: str) -> list[str]:
        values = root.xpath(f".//@*[local-name()='{attribute_name}']")
        return [" ".join(str(value).split()) for value in values if str(value).strip()]

    @classmethod
    def _first_text(cls, root, local_name: str) -> str | None:
        values = cls._all_text(root, local_name)
        return values[0] if values else None

    @staticmethod
    def _first_attribute(root, element_name: str, attribute_name: str) -> str | None:
        values = root.xpath(
            f"(.//*[local-name()='{element_name}']/@*[local-name()='{attribute_name}'])[1]"
        )
        return " ".join(str(values[0]).split()) if values else None

    @staticmethod
    def _at(recent: dict[str, Any], key: str, index: int) -> Any:
        values = recent.get(key, [])
        return values[index] if isinstance(values, list) and index < len(values) else None

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        try:
            if len(text) == 10:
                parsed = datetime.fromisoformat(f"{text}T00:00:00")
            else:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
