"""Primary-source SEC submissions evidence adapter."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import httpx

from catalyst_edge_mcp.adapters.base import ProviderGate
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
SEC_GATE = ProviderGate(concurrency=2, requests_per_second=2)
PARSER_VERSION = "sec-events-v1"


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
    ) -> list[str]:
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
        return links[:20]

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
            evidence.append(
                Evidence(
                    family=cls.family,
                    signal=signal,
                    direction=direction,
                    strength=FORM_STRENGTH.get(base_form, 0.6),
                    confidence=0.98,
                    timestamp=filing_date,
                    source_quality=1.0,
                    change=Change(
                        description=(
                            f"A new SEC {form} was observed"
                            + (f" with item codes {item_codes}." if item_codes else ".")
                        )
                    ),
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
