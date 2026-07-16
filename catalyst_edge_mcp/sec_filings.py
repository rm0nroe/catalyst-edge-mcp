"""Primary-source SEC submissions evidence adapter."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
from lxml import html
from pydantic import HttpUrl, TypeAdapter

from catalyst_edge_mcp.adapters.base import ProviderGate
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    EvidenceContext,
    PolicyDecision,
    Source,
    SourceStatus,
)
from catalyst_edge_mcp.sec_document_rules import (
    RULESET_VERSION,
    classify_sec_primary_document,
)

TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
TRACKED_FORMS = frozenset(
    {"8-K", "8-K/A", "10-Q", "10-Q/A", "10-K", "10-K/A", "6-K", "20-F", "40-F"}
)
FORM_STRENGTH = {
    "8-K": 0.8,
    "6-K": 0.75,
    "10-Q": 0.65,
    "10-K": 0.7,
    "20-F": 0.7,
    "40-F": 0.7,
}
BEARISH_8K_ITEMS = frozenset({"1.03", "3.01", "4.02"})
BEARISH_ITEM_SIGNALS = {
    "1.03": "bankruptcy",
    "3.01": "delisting",
    "4.02": "restatement",
}
ITEM_PRIORITY = (
    "1.03",
    "2.04",
    "4.02",
    "3.01",
    "2.01",
    "2.02",
    "2.03",
    "2.05",
    "2.06",
    "1.01",
    "1.02",
    "3.02",
    "3.03",
    "4.01",
    "5.02",
    "5.03",
    "5.07",
    "7.01",
    "8.01",
    "9.01",
)
MAX_PRIMARY_DOCUMENT_BYTES = 2_000_000
SEC_GATE = ProviderGate(concurrency=2, requests_per_second=2)
PARSER_VERSION = "sec-events-v1"
HTTP_URL_LIST = TypeAdapter(list[HttpUrl])
ITEM_CONTEXT = {
    "1.01": (
        "material_agreement",
        "Material definitive agreement",
        "A new or amended material contract can change committed economics, "
        "obligations, or strategic scope.",
        "material",
    ),
    "1.02": (
        "material_agreement_termination",
        "Termination of a material agreement",
        "Ending a material contract can change expected economics, counterparties, "
        "or operating plans.",
        "material",
    ),
    "1.03": (
        "bankruptcy",
        "Bankruptcy or receivership",
        "Bankruptcy or receivership directly changes solvency, control, and claim priority.",
        "critical",
    ),
    "2.01": (
        "acquisition_or_disposition",
        "Acquisition or disposition",
        "A completed acquisition or disposition can materially change assets, "
        "liabilities, and operating scope.",
        "material",
    ),
    "2.02": (
        "financial_results",
        "Results of operations and financial condition",
        "Reported operating or financial results update the primary evidence for "
        "recent company performance.",
        "material",
    ),
    "2.03": (
        "financial_obligation",
        "Creation of a financial obligation",
        "A material financial obligation can change leverage, liquidity, and future "
        "cash commitments.",
        "material",
    ),
    "2.04": (
        "obligation_trigger",
        "Triggering events for financial obligations",
        "An acceleration or similar trigger can change near-term liquidity and repayment risk.",
        "critical",
    ),
    "2.05": (
        "restructuring",
        "Exit or disposal activities",
        "A restructuring or disposal plan can change costs, staffing, and operating capacity.",
        "material",
    ),
    "2.06": (
        "impairment",
        "Material impairment",
        "A material impairment changes the carrying value of assets and may signal "
        "weaker expected economics.",
        "material",
    ),
    "3.01": (
        "delisting",
        "Delisting or listing-rule notice",
        "A listing notice can affect market access and may require remediation within "
        "a stated period.",
        "critical",
    ),
    "3.02": (
        "unregistered_security_sale",
        "Unregistered sale of equity securities",
        "A securities issuance can change capitalization and potential dilution.",
        "material",
    ),
    "3.03": (
        "security_holder_rights",
        "Material modification of security-holder rights",
        "A rights modification can change the economics or control attached to "
        "outstanding securities.",
        "material",
    ),
    "4.01": (
        "auditor_change",
        "Change in certifying accountant",
        "An auditor change warrants review of the stated reason, disagreements, and "
        "transition disclosures.",
        "material",
    ),
    "4.02": (
        "restatement",
        "Non-reliance on prior financial statements",
        "A non-reliance determination can invalidate prior financial information and "
        "require corrected reporting.",
        "critical",
    ),
    "5.02": (
        "leadership_change",
        "Director or executive change",
        "A board or executive transition can change governance, operating responsibility, "
        "or succession risk.",
        "material",
    ),
    "5.03": (
        "governance_change",
        "Charter or bylaw amendment",
        "A governing-document change can alter shareholder rights or corporate decision rules.",
        "contextual",
    ),
    "5.07": (
        "shareholder_vote",
        "Shareholder vote results",
        "Voting results establish which proposals and governance actions received "
        "shareholder approval.",
        "contextual",
    ),
    "7.01": (
        "regulation_fd",
        "Regulation FD disclosure",
        "A Regulation FD disclosure points to information the issuer considered "
        "appropriate for broad public dissemination.",
        "contextual",
    ),
    "8.01": (
        "other_material_event",
        "Other material event",
        "The issuer elected to report an event it considered material or useful to investors.",
        "material",
    ),
    "9.01": (
        "exhibits",
        "Financial statements and exhibits",
        "Filed exhibits may contain the detailed primary facts supporting the current report.",
        "supporting",
    ),
}
FORM_CONTEXT = {
    "6-K": (
        "foreign_issuer_report",
        "Foreign issuer current report",
        "A Form 6-K supplies current information disclosed by a foreign private issuer.",
        "material",
    ),
    "10-Q": (
        "quarterly_report",
        "Quarterly report",
        "A Form 10-Q updates financial statements, risks, and management discussion "
        "for the latest quarter.",
        "material",
    ),
    "10-K": (
        "annual_report",
        "Annual report",
        "A Form 10-K updates audited financials, risks, controls, and the issuer's "
        "annual operating record.",
        "material",
    ),
    "20-F": (
        "foreign_annual_report",
        "Foreign issuer annual report",
        "A Form 20-F updates the foreign issuer's annual financial and operating record.",
        "material",
    ),
    "40-F": (
        "canadian_annual_report",
        "Canadian issuer annual report",
        "A Form 40-F updates the Canadian issuer's annual financial and operating record.",
        "material",
    ),
}


def resolve_sec_ticker(ticker_to_cik: dict[str, str], ticker: str) -> str | None:
    """Resolve display-style class tickers against SEC's dash-style symbols."""
    return ticker_to_cik.get(ticker) or ticker_to_cik.get(ticker.replace(".", "-"))


class SecFilingsAdapter:
    """Collect recent filing metadata from the official SEC submissions API."""

    family = "filings_news"
    provider = "sec"

    def __init__(
        self,
        user_agent: str,
        *,
        client: httpx.AsyncClient | None = None,
        clock=None,
    ) -> None:
        if "@" not in user_agent:
            raise ValueError("SEC User-Agent must include a contact email address")
        self.user_agent = user_agent
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._ticker_to_cik: dict[str, str] | None = None

    async def collect(self, ticker: str, lookback_days: int) -> AdapterResult:
        if self._client is not None:
            return await self._collect(self._client, ticker, lookback_days)
        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(headers=headers, timeout=6.0, follow_redirects=True) as client:
            return await self._collect(client, ticker, lookback_days)

    async def _collect(
        self, client: httpx.AsyncClient, ticker: str, lookback_days: int
    ) -> AdapterResult:
        cik = await self._resolve_cik(client, ticker)
        if cik is None:
            return AdapterResult(
                family=self.family,
                provider=self.provider,
                warnings=[f"SEC submissions mapping has no CIK for {ticker}."],
            )
        async with SEC_GATE.request():
            response = await client.get(SUBMISSIONS_URL.format(cik=cik))
        response.raise_for_status()
        retrieved_at = self._as_utc(self._clock())
        cutoff = retrieved_at - timedelta(days=lookback_days)
        evidence = self._normalize_recent(response.json(), cik, cutoff, retrieved_at)
        warnings = []
        for item in evidence:
            source = item.sources[0]
            accession = source.accession_or_record_id
            form = str((item.raw_signal or {}).get("form") or "")
            if not accession or form.removesuffix("/A") not in {"8-K", "6-K"}:
                continue
            if item.context and item.context.event_type == "other_material_event":
                try:
                    await self._enrich_primary_document(client, item)
                except (httpx.HTTPError, ValueError):
                    warnings.append(
                        f"SEC {accession} primary document was unavailable or malformed."
                    )
            try:
                source.related_sources = await self._exhibit_links(client, cik, accession)
            except (httpx.HTTPError, ValueError):
                warnings.append(f"SEC {accession} exhibit index was unavailable or malformed.")
        if not evidence:
            warnings.append(f"No tracked SEC filings found for {ticker} in the lookback window.")
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            status=SourceStatus.FRESH if evidence else SourceStatus.NO_OBSERVATIONS,
            policy_decision=PolicyDecision.APPROVED,
            collected_at=retrieved_at,
        )

    async def _exhibit_links(
        self, client: httpx.AsyncClient, cik: str, accession: str
    ) -> list[HttpUrl]:
        accession_path = accession.replace("-", "")
        index_url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_path}/index.json"
        )
        async with SEC_GATE.request():
            response = await client.get(index_url)
        response.raise_for_status()
        payload = response.json()
        items = payload.get("directory", {}).get("item", [])
        if not isinstance(items, list):
            raise ValueError("Unexpected SEC filing index schema")
        links = []
        for row in items:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "")
            document_type = str(row.get("type") or "").upper()
            normalized_name = name.lower().replace("-", "").replace("_", "")
            if document_type.startswith("EX-99") or "ex99" in normalized_name:
                links.append(index_url.rsplit("/", 1)[0] + "/" + name)
        return HTTP_URL_LIST.validate_python(links[:20])

    async def _enrich_primary_document(
        self,
        client: httpx.AsyncClient,
        evidence: Evidence,
    ) -> None:
        source = evidence.sources[0]
        url = str(source.canonical_url or source.url or "")
        self._require_archive_url(url)
        async with SEC_GATE.request():
            response = await client.get(url)
        response.raise_for_status()
        self._require_archive_url(str(response.url))
        content = response.content
        if len(content) > MAX_PRIMARY_DOCUMENT_BYTES:
            raise ValueError("SEC primary document exceeded the bounded response size")
        self._apply_primary_document_context(evidence, content)
        source.raw_sha256 = hashlib.sha256(content).hexdigest()

    @classmethod
    def _apply_primary_document_context(cls, evidence: Evidence, content: bytes) -> None:
        try:
            tree = html.fromstring(content)
        except (ValueError, TypeError) as exc:
            raise ValueError("SEC primary document HTML was malformed") from exc
        for element in tree.xpath("//script|//style|//noscript"):
            element.drop_tree()
        text = " ".join(" ".join(tree.xpath("//body//text()")).split())
        decision = classify_sec_primary_document(text)
        if isinstance(evidence.raw_signal, dict):
            evidence.raw_signal["document_enrichment"] = {
                "ruleset_version": decision.ruleset_version,
                "status": decision.status,
                "rule_id": (
                    decision.selected_rule.rule_id if decision.selected_rule else None
                ),
                "rule_version": (
                    decision.selected_rule.version if decision.selected_rule else None
                ),
                "candidate_rule_ids": list(decision.candidate_rule_ids),
            }
        rule = decision.selected_rule
        if rule is None:
            return

        evidence.context = EvidenceContext(
            event_type=rule.event_type,
            event_label=rule.label,
            novelty=(evidence.context.novelty if evidence.context else "new_event"),
            materiality=rule.materiality,
            why_it_matters=rule.why_it_matters,
            source_record_count=(
                evidence.context.source_record_count if evidence.context else 1
            ),
            corroborating_source_count=(
                evidence.context.corroborating_source_count if evidence.context else 0
            ),
            source_tiers=(
                list(evidence.context.source_tiers)
                if evidence.context
                else ["primary_regulator"]
            ),
            correction_of_event_id=(
                evidence.context.correction_of_event_id if evidence.context else None
            ),
        )
        evidence.change = Change(description=f"SEC 8-K reported {rule.label.lower()}.")
        if isinstance(evidence.raw_signal, dict):
            evidence.raw_signal["document_event_type"] = rule.event_type
        if evidence.sources:
            evidence.sources[0].parser_version = f"{PARSER_VERSION}+{RULESET_VERSION}"
        evidence.notes = (
            f"{evidence.notes or 'SEC filing metadata.'} {rule.label} identified "
            f"by {rule.rule_id}@{rule.version}."
        )

    @staticmethod
    def _require_archive_url(url: str) -> None:
        parsed = urlsplit(url)
        decoded_path = unquote(parsed.path)
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower().rstrip(".") != "www.sec.gov"
            or not parsed.path.startswith("/Archives/edgar/data/")
            or decoded_path != parsed.path
            or "\\" in decoded_path
            or any(segment in {".", ".."} for segment in decoded_path.split("/"))
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("SEC primary document URL is outside the official archive")

    async def _resolve_cik(self, client: httpx.AsyncClient, ticker: str) -> str | None:
        if self._ticker_to_cik is None:
            async with SEC_GATE.request():
                response = await client.get(TICKER_MAP_URL)
            response.raise_for_status()
            payload = response.json()
            fields = payload.get("fields", [])
            try:
                ticker_index = fields.index("ticker")
                cik_index = fields.index("cik")
            except ValueError as exc:
                raise ValueError("Unexpected SEC ticker mapping schema") from exc
            self._ticker_to_cik = {
                str(row[ticker_index]).upper(): str(row[cik_index]).zfill(10)
                for row in payload.get("data", [])
                if len(row) > max(ticker_index, cik_index)
            }
        return resolve_sec_ticker(self._ticker_to_cik, ticker)

    @classmethod
    def _normalize_recent(
        cls,
        payload: dict[str, Any],
        cik: str,
        cutoff: datetime,
        retrieved_at: datetime | None = None,
    ) -> list[Evidence]:
        recent = payload.get("filings", {}).get("recent", {})
        if not isinstance(recent, dict) or not isinstance(recent.get("form"), list):
            raise ValueError("Unexpected SEC submissions schema")
        evidence: list[Evidence] = []
        for index, form in enumerate(recent.get("form", [])):
            if form not in TRACKED_FORMS:
                continue
            filing_date = cls._parse_datetime(
                cls._at(recent, "acceptanceDateTime", index)
            ) or cls._parse_date(cls._at(recent, "filingDate", index))
            if filing_date is None or filing_date < cutoff:
                continue
            accession = str(cls._at(recent, "accessionNumber", index) or "")
            primary_document = str(cls._at(recent, "primaryDocument", index) or "")
            if not accession or not primary_document:
                continue
            accession_path = accession.replace("-", "")
            raw_document = primary_document.rsplit("/", 1)[-1]
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_path}/{raw_document}"
            )
            base_form = form.removesuffix("/A")
            item_codes = str(cls._at(recent, "items", index) or "").strip()
            normalized_items = set(item_codes.replace(" ", "").split(","))
            adverse_items = normalized_items & BEARISH_8K_ITEMS
            if {"2.01", "3.01", "5.01"} <= normalized_items:
                # A listing termination following a completed change of control is not
                # an exchange-compliance delisting signal.
                adverse_items.discard("3.01")
            adverse_event = bool(adverse_items)
            direction = (
                Direction.BEARISH if base_form == "8-K" and adverse_event else Direction.NEUTRAL
            )
            signal = f"sec_form_{form.lower().replace('-', '_').replace('/', '_')}"
            if base_form == "8-K" and adverse_items:
                signal = BEARISH_ITEM_SIGNALS[sorted(adverse_items)[0]]
            notes = f"SEC {form} filing metadata."
            if item_codes:
                notes = f"SEC {form} filing reports item codes {item_codes}."
            context = cls._event_context(form, normalized_items)
            descriptions = [
                f"Item {code} ({ITEM_CONTEXT[code][1]})"
                for code in sorted(normalized_items)
                if code in ITEM_CONTEXT
            ]
            description = (
                f"SEC {form} reported " + ", ".join(descriptions) + "."
                if descriptions
                else f"A new SEC {form} was observed."
            )
            evidence.append(
                Evidence(
                    family=cls.family,
                    signal=signal,
                    direction=direction,
                    strength=FORM_STRENGTH.get(base_form, 0.6),
                    confidence=0.98,
                    timestamp=filing_date,
                    source_quality=1.0,
                    change=Change(description=description[:240]),
                    context=context,
                    sources=[
                        Source(
                            name="SEC EDGAR",
                            source_id="sec",
                            source_tier="primary_regulator",
                            url=url,
                            canonical_url=url,
                            accession_or_record_id=accession,
                            published_at=filing_date,
                            observed_at=filing_date,
                            retrieved_at=retrieved_at,
                            parser_version=PARSER_VERSION,
                            policy_decision=PolicyDecision.APPROVED,
                        )
                    ],
                    notes=notes,
                    raw_signal={
                        "form": form,
                        "accession_number": accession,
                        "items": item_codes or None,
                    },
                )
            )
            if len(evidence) == 10:
                break
        return evidence

    @staticmethod
    def _event_context(form: str, item_codes: set[str]) -> EvidenceContext:
        base_form = form.removesuffix("/A")
        eligible = set(item_codes)
        if {"2.01", "3.01", "5.01"} <= eligible:
            eligible.discard("3.01")
        primary_code = next((code for code in ITEM_PRIORITY if code in eligible), None)
        if primary_code is not None:
            event_type, label, why, materiality = ITEM_CONTEXT[primary_code]
        else:
            event_type, label, why, materiality = FORM_CONTEXT.get(
                base_form,
                (
                    "sec_filing",
                    f"SEC {base_form}",
                    "The filing updates the issuer's primary regulatory record.",
                    "contextual",
                ),
            )
        return EvidenceContext(
            event_type=event_type,
            event_label=label,
            novelty="amendment" if form.endswith("/A") else "new_event",
            materiality=materiality,
            why_it_matters=why,
            source_record_count=1,
            source_tiers=["primary_regulator"],
        )

    @staticmethod
    def _at(recent: dict[str, Any], key: str, index: int) -> Any:
        values = recent.get(key, [])
        return values[index] if index < len(values) else None

    @staticmethod
    def _parse_date(value: Any) -> datetime | None:
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=UTC)
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        text = str(value or "").strip().replace("Z", "+00:00")
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
