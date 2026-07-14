"""Direct SEC ownership XML and Form 144 evidence adapter."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import httpx
from lxml import etree

from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import (
    AdapterResult,
    Change,
    Direction,
    Evidence,
    PolicyDecision,
    Source,
    SourceStatus,
)
from catalyst_edge_mcp.sec_filings import (
    SEC_GATE,
    SUBMISSIONS_URL,
    TICKER_MAP_URL,
    resolve_sec_ticker,
)

OWNERSHIP_FORMS = frozenset({"3", "3/A", "4", "4/A", "5", "5/A"})
FORM_144 = frozenset({"144", "144/A"})
PARSER_VERSION = "sec-ownership-v1"


def _local_text(node: etree._Element, path: str) -> str | None:
    values = node.xpath(path)
    if isinstance(values, list):
        if not values:
            return None
        value = values[0]
    else:
        if values is None or values == "":
            return None
        value = values
    text = value if isinstance(value, str) else "".join(value.itertext())
    stripped = str(text).strip()
    return stripped or None


def _number(value: str | None) -> float | None:
    try:
        result = float(value) if value is not None else None
    except ValueError:
        return None
    valid = result is not None and result == result and abs(result) != float("inf")
    return result if valid else None


def _first_text(node: etree._Element, *local_names: str) -> str | None:
    for local_name in local_names:
        value = _local_text(node, f"string((.//*[local-name()='{local_name}'])[1])")
        if value is not None:
            return value
    return None


def _flag(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def _parse_datetime(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    for candidate in (normalized, normalized.replace(" ", "T", 1)):
        try:
            parsed = datetime.fromisoformat(candidate)
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
        except ValueError:
            pass
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_xml(content: bytes) -> etree._Element:
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        recover=False,
        huge_tree=False,
        remove_comments=True,
    )
    return etree.fromstring(content, parser=parser)


def parse_ownership_xml(content: bytes) -> dict[str, Any]:
    """Parse fixed Forms 3/4/5 facts without relying on namespace prefixes."""
    root = _parse_xml(content)
    form = _local_text(root, "string((.//*[local-name()='documentType'])[1])")
    issuer_cik = _local_text(root, "string((.//*[local-name()='issuerCik'])[1])")
    owners = []
    for owner in root.xpath(".//*[local-name()='reportingOwner']"):
        owners.append(
            {
                "cik": _local_text(owner, "string((.//*[local-name()='rptOwnerCik'])[1])"),
                "name": _local_text(owner, "string((.//*[local-name()='rptOwnerName'])[1])"),
                "is_director": _flag(
                    _local_text(owner, "string((.//*[local-name()='isDirector'])[1])")
                ),
                "is_officer": _flag(
                    _local_text(owner, "string((.//*[local-name()='isOfficer'])[1])")
                ),
                "is_ten_percent_owner": _flag(
                    _local_text(owner, "string((.//*[local-name()='isTenPercentOwner'])[1])")
                ),
                "officer_title": _local_text(
                    owner, "string((.//*[local-name()='officerTitle'])[1])"
                ),
            }
        )
    footnotes = {
        str(node.get("id") or ""): " ".join("".join(node.itertext()).split())
        for node in root.xpath(".//*[local-name()='footnote']")
    }
    transactions = []
    for derivative, xpath in (
        (False, ".//*[local-name()='nonDerivativeTransaction']"),
        (True, ".//*[local-name()='derivativeTransaction']"),
    ):
        for transaction in root.xpath(xpath):
            footnote_ids = transaction.xpath(".//*[local-name()='footnoteId']/@id")
            referenced_footnotes = " ".join(
                footnotes.get(str(footnote_id), "") for footnote_id in footnote_ids
            ).lower()
            transactions.append(
                {
                    "derivative": derivative,
                    "security_title": _local_text(
                        transaction,
                        "string((.//*[local-name()='securityTitle']/*[local-name()='value'])[1])",
                    ),
                    "transaction_date": _local_text(
                        transaction,
                        "string((.//*[local-name()='transactionDate']/*[local-name()='value'])[1])",
                    ),
                    "code": _local_text(
                        transaction,
                        "string((.//*[local-name()='transactionCode'])[1])",
                    ),
                    "shares": _number(
                        _local_text(
                            transaction,
                            "string((.//*[local-name()='transactionShares']/*[local-name()='value'])[1])",
                        )
                    ),
                    "price": _number(
                        _local_text(
                            transaction,
                            "string((.//*[local-name()='transactionPricePerShare']/*[local-name()='value'])[1])",
                        )
                    ),
                    "acquired_disposed": _local_text(
                        transaction,
                        "string((.//*[local-name()='transactionAcquiredDisposedCode']/*[local-name()='value'])[1])",
                    ),
                    "holdings_after": _number(
                        _local_text(
                            transaction,
                            "string((.//*[local-name()='sharesOwnedFollowingTransaction']/*[local-name()='value'])[1])",
                        )
                    ),
                    "ownership_form": _local_text(
                        transaction,
                        "string((.//*[local-name()='directOrIndirectOwnership']/*[local-name()='value'])[1])",
                    ),
                    "footnote_ids": footnote_ids,
                    "is_10b5_1": (
                        "10b5-1" in referenced_footnotes
                        or _flag(
                            _local_text(
                                transaction,
                                "string((.//*[local-name()='aff10b5One'])[1])",
                            )
                        )
                    ),
                }
            )
    return {
        "form": form,
        "issuer_cik": issuer_cik,
        "owners": owners,
        "transactions": transactions,
        "footnotes": footnotes,
    }


def parse_form_144_xml(content: bytes) -> dict[str, Any]:
    """Parse proposed-sale facts while preserving that Form 144 is not execution."""
    root = _parse_xml(content)
    return {
        "issuer_name": _first_text(root, "issuerName"),
        "issuer_cik": _first_text(root, "issuerCik"),
        "filer_name": _first_text(
            root, "filerName", "nameOfPersonForWhoseAccountTheSecuritiesAreToBeSold"
        ),
        "security_class": _first_text(root, "securitiesClassTitle"),
        "units_to_be_sold": _number(_first_text(root, "unitsToBeSold", "noOfUnitsSold")),
        "aggregate_market_value": _number(_first_text(root, "aggregateMarketValue")),
        "approx_sale_date": _first_text(root, "approxSaleDate"),
        "broker_name": _first_text(root, "brokerName")
        or _local_text(
            root,
            "string((.//*[local-name()='brokerOrMarketmakerDetails']//*[local-name()='name'])[1])",
        ),
    }


class SecInsiderAdapter:
    """Collect direct SEC open-market insider activity and proposed-sale context."""

    family = "insider_trading"
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
            "Accept": "application/json, application/xml, text/xml",
        }
        async with httpx.AsyncClient(headers=headers, timeout=6.0, follow_redirects=True) as client:
            return await self._collect(client, ticker, lookback_days)

    async def _collect(
        self, client: httpx.AsyncClient, ticker: str, lookback_days: int
    ) -> AdapterResult:
        now = self._as_utc(self._clock())
        cik = await self._resolve_cik(client, ticker)
        if cik is None:
            return self._result([], [f"SEC submissions mapping has no CIK for {ticker}."], now)
        payload = await self._get_json(client, SUBMISSIONS_URL.format(cik=cik))
        recent = payload.get("filings", {}).get("recent", {})
        if not isinstance(recent, dict) or not isinstance(recent.get("form"), list):
            raise ValueError("Unexpected SEC submissions schema")
        cutoff = now - timedelta(days=lookback_days)
        records: list[dict[str, Any]] = []
        proposed_sales: list[Evidence] = []
        warnings: list[str] = []
        for index, form in enumerate(recent["form"]):
            if form not in OWNERSHIP_FORMS | FORM_144:
                continue
            filed_at = _parse_datetime(self._at(recent, "acceptanceDateTime", index)) or (
                _parse_datetime(self._at(recent, "filingDate", index))
            )
            if filed_at is None or filed_at < cutoff:
                continue
            accession = str(self._at(recent, "accessionNumber", index) or "")
            document = str(self._at(recent, "primaryDocument", index) or "")
            if not accession or not document:
                warnings.append(f"SEC {form} entry omitted accession or primary document.")
                continue
            url = self._archive_url(cik, accession, document)
            content = await self._get_bytes(client, url)
            sha256 = hashlib.sha256(content).hexdigest()
            source = Source(
                name="SEC EDGAR",
                source_id="sec",
                source_tier="primary_regulator",
                url=url,
                canonical_url=url,
                accession_or_record_id=accession,
                published_at=filed_at,
                observed_at=filed_at,
                retrieved_at=now,
                raw_sha256=sha256,
                parser_version=PARSER_VERSION,
                policy_decision=PolicyDecision.APPROVED,
            )
            if form in FORM_144:
                facts = parse_form_144_xml(content)
                proposed_sales.append(self._form_144_evidence(facts, filed_at, source, accession))
                continue
            facts = parse_ownership_xml(content)
            owner_names = [owner.get("name") for owner in facts["owners"] if owner.get("name")]
            owner = owner_names[0] if owner_names else "unknown reporting owner"
            for transaction in facts["transactions"]:
                transaction_date = _parse_datetime(transaction.get("transaction_date")) or filed_at
                records.append(
                    {
                        **transaction,
                        "owner": owner,
                        "owner_names": owner_names or [owner],
                        "owners": facts["owners"],
                        "footnotes": facts["footnotes"],
                        "timestamp": transaction_date,
                        "source": source,
                        "accession": accession,
                    }
                )
        evidence = self._normalize_transactions(records, proposed_sales, now, lookback_days)
        if not evidence:
            warnings.append(f"No qualifying direct SEC insider activity found for {ticker}.")
        return self._result(evidence, warnings, now)

    @classmethod
    def _normalize_transactions(
        cls,
        records: list[dict[str, Any]],
        proposed_sales: list[Evidence],
        now: datetime,
        lookback_days: int,
    ) -> list[Evidence]:
        half_days = max(1.0, lookback_days / 2)
        current_cutoff = now - timedelta(days=half_days)
        prior_cutoff = now - timedelta(days=lookback_days)
        windows: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for record in records:
            timestamp = record["timestamp"]
            if timestamp < prior_cutoff:
                continue
            code = str(record.get("code") or "").upper()
            shares = record.get("shares")
            price = record.get("price")
            if record.get("derivative") or code not in {"P", "S"}:
                continue
            acquired_disposed = str(record.get("acquired_disposed") or "").upper()
            if (code == "P" and acquired_disposed != "A") or (
                code == "S" and acquired_disposed != "D"
            ):
                continue
            if shares is None or price is None or shares <= 0 or price <= 0:
                continue
            windows["current" if timestamp >= current_cutoff else "prior"].append(record)
        current = windows["current"]
        output = list(proposed_sales)
        if not current:
            return output
        signed_values = [
            record["shares"] * record["price"] * (-1 if record["code"].upper() == "S" else 1)
            for record in current
        ]
        net = float(sum(signed_values))
        direction = (
            Direction.BULLISH if net > 0 else Direction.BEARISH if net < 0 else Direction.NEUTRAL
        )
        kind = "purchase" if net > 0 else "sale" if net < 0 else "mixed"
        direction_code = "P" if kind == "purchase" else "S" if kind == "sale" else ""
        direction_records = [
            record for record in current if record["code"].upper() == direction_code
        ]
        owners = {
            owner
            for record in direction_records
            for owner in record.get("owner_names", [record["owner"]])
        }
        unplanned_owners = {
            owner
            for record in direction_records
            if not record.get("is_10b5_1")
            for owner in record.get("owner_names", [record["owner"]])
        }
        cluster_kind = (
            "strong_cluster" if len(owners) >= 3 else "cluster" if len(owners) >= 2 else "activity"
        )
        confidence = (
            0.88
            if cluster_kind == "strong_cluster"
            else 0.82
            if cluster_kind == "cluster"
            else 0.68
        )
        if direction == Direction.BEARISH:
            confidence = (
                0.72 if len(unplanned_owners) >= 3 else 0.66 if len(unplanned_owners) >= 2 else 0.52
            )
            if any(record.get("is_10b5_1") for record in direction_records):
                confidence = min(confidence, 0.50)
        prior_net = float(
            sum(
                record["shares"] * record["price"] * (-1 if record["code"].upper() == "S" else 1)
                for record in windows["prior"]
                if not record.get("derivative")
                and record.get("shares")
                and record.get("price")
                and str(record.get("code") or "").upper() in {"P", "S"}
            )
        )
        latest = max(record["timestamp"] for record in current)
        sources = list({str(record["source"].url): record["source"] for record in current}.values())
        output.insert(
            0,
            Evidence(
                family="insider_trading",
                signal=f"insider_{kind}_{cluster_kind}",
                direction=direction,
                strength=min(1.0, 0.45 + 0.12 * len(owners)),
                confidence=confidence,
                timestamp=latest,
                source_quality=1.0,
                change=Change(
                    description=(
                        f"Direct SEC open-market insider value was {net:,.0f} across "
                        f"{len(owners)} same-direction reporting owner"
                        f"{'s' if len(owners) != 1 else ''} versus {prior_net:,.0f}."
                    ),
                    current_value=net,
                    baseline_value=prior_net,
                    delta=net - prior_net,
                    unit="USD reported value",
                    comparison_window="current half vs preceding equal window",
                ),
                sources=sources,
                notes=(
                    "Only non-derivative open-market P/S transactions with disclosed shares "
                    "and price are directional; grants, exercises, gifts, taxes, and derivatives "
                    "are excluded."
                ),
                raw_signal=[
                    {
                        key: value
                        for key, value in record.items()
                        if key not in {"source", "timestamp"}
                    }
                    for record in current
                ],
            ),
        )
        return output

    @staticmethod
    def _form_144_evidence(
        facts: dict[str, Any], filed_at: datetime, source: Source, accession: str
    ) -> Evidence:
        units = facts.get("units_to_be_sold")
        sale_date = facts.get("approx_sale_date") or "an unspecified date"
        description = (
            f"A Form 144 reported a proposed sale of {units:,.0f} units around {sale_date}."
            if units is not None
            else f"A Form 144 reported proposed sale intent around {sale_date}."
        )
        return Evidence(
            family="insider_trading",
            signal="insider_proposed_sale_intent",
            direction=Direction.NEUTRAL,
            strength=0.35,
            confidence=0.90,
            timestamp=filed_at,
            source_quality=1.0,
            change=Change(description=description),
            sources=[source],
            notes="Form 144 is proposed sale intent, not evidence of completed execution.",
            raw_signal={**facts, "accession": accession, "completed_execution": False},
        )

    async def _resolve_cik(self, client: httpx.AsyncClient, ticker: str) -> str | None:
        if self._ticker_to_cik is None:
            payload = await self._get_json(client, TICKER_MAP_URL)
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

    async def _get_json(self, client: httpx.AsyncClient, url: str) -> dict[str, Any]:
        async with SEC_GATE.request():
            response = await client.get(url)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected SEC JSON schema")
        return payload

    async def _get_bytes(self, client: httpx.AsyncClient, url: str) -> bytes:
        async with SEC_GATE.request():
            response = await client.get(url)
        response.raise_for_status()
        return response.content

    def _result(
        self, evidence: list[Evidence], warnings: list[str], collected_at: datetime
    ) -> AdapterResult:
        return AdapterResult(
            family=self.family,
            provider=self.provider,
            evidence=evidence,
            warnings=warnings,
            status=SourceStatus.FRESH if evidence else SourceStatus.NO_OBSERVATIONS,
            policy_decision=PolicyDecision.APPROVED,
            collected_at=collected_at,
        )

    @staticmethod
    def _archive_url(cik: str, accession: str, document: str) -> str:
        raw_document = document.rsplit("/", 1)[-1]
        return (
            f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
            f"{accession.replace('-', '')}/{raw_document}"
        )

    @staticmethod
    def _at(recent: dict[str, Any], key: str, index: int) -> Any:
        values = recent.get(key, [])
        return values[index] if isinstance(values, list) and index < len(values) else None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
