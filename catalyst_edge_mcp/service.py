"""Concurrent collection, quality evaluation, scoring, and compact response composition."""

from __future__ import annotations

import asyncio
import hashlib
import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta

import httpx

from catalyst_edge_mcp.adapters import CatalystSignalAdapter
from catalyst_edge_mcp.compat import UTC
from catalyst_edge_mcp.models import (
    AdapterResult,
    CatalystEdgeResponse,
    DataQuality,
    Evidence,
    FamilyStatus,
    PolicyDecision,
    ReasonCode,
    ReasonScope,
    ScopedReason,
    SourceStatus,
    ToolInput,
)
from catalyst_edge_mcp.reason_records import ordered_reasons, scoped_reason
from catalyst_edge_mcp.redaction import bounded_raw
from catalyst_edge_mcp.scorer import CANONICAL_FAMILIES, CatalystScorer, DeterministicScorer
from catalyst_edge_mcp.source_policy import SOURCE_POLICIES, source_attributions
from catalyst_edge_mcp.summary import build_summary, next_checks

Clock = Callable[[], datetime]
MAX_EVIDENCE_PER_FAMILY = 3
MAX_EVIDENCE_TOTAL = 15
MAX_WARNINGS = 20
MAX_REASON_RECORDS = 600
EXPECTED_PROVIDERS = {
    "filings_news": "SEC, reviewed issuer feeds, or discovery metadata",
    "insider_trading": "direct SEC ownership filings",
    "options_flow": "a licensed transaction-plus-quote provider",
    "technical": "a user-supplied/licensed OHLC provider",
    "social": "a reviewed partial-attention collector",
}

DEFAULT_MISSING_STATUS = {
    "options_flow": SourceStatus.LICENSED_FEED_REQUIRED,
    "technical": SourceStatus.LICENSED_FEED_REQUIRED,
}
STATUS_PRIORITY = {
    SourceStatus.PERMISSION_REQUIRED: 9,
    SourceStatus.LICENSED_FEED_REQUIRED: 8,
    SourceStatus.RATE_LIMITED: 7,
    SourceStatus.TIMEOUT: 6,
    SourceStatus.SCHEMA_ERROR: 5,
    SourceStatus.STALE: 4,
    SourceStatus.NO_OBSERVATIONS: 3,
    SourceStatus.UNSUPPORTED: 3,
    SourceStatus.UNAVAILABLE: 2,
    SourceStatus.FRESH: 1,
}


class CatalystService:
    """Collect isolated providers and produce a deterministic, schema-valid dossier."""

    def __init__(
        self,
        adapters: Sequence[CatalystSignalAdapter] = (),
        *,
        scorer: CatalystScorer | None = None,
        adapter_timeout_seconds: float = 8.0,
        clock: Clock | None = None,
        expected_families: frozenset[str] = CANONICAL_FAMILIES,
    ) -> None:
        self.adapters = tuple(adapters)
        self.scorer = scorer or DeterministicScorer()
        self.adapter_timeout_seconds = adapter_timeout_seconds
        self.clock = clock or (lambda: datetime.now(UTC))
        self.expected_families = expected_families

    async def evaluate(self, request: ToolInput) -> CatalystEdgeResponse:
        as_of = self._as_utc(self.clock())
        cutoff = as_of - timedelta(days=request.lookback_days)
        active_adapters = tuple(
            adapter
            for adapter in self.adapters
            if not callable(supports := getattr(adapter, "supports", None))
            or supports(request.ticker)
        )
        results = await asyncio.gather(
            *(self._collect(adapter, request) for adapter in active_adapters)
        )

        evidence: list[Evidence] = []
        used_source_ids: set[str] = set()
        warnings: list[str] = []
        stale: set[str] = set()
        providers_by_family: dict[str, set[str]] = defaultdict(set)
        failures_by_family: set[str] = set()
        statuses_by_family: dict[str, list[SourceStatus]] = defaultdict(list)
        reason_records: list[ScopedReason] = []

        for family, provider, result, error, error_status in results:
            providers_by_family[family].add(provider)
            if error:
                failures_by_family.add(family)
                effective_error_status = error_status or SourceStatus.UNAVAILABLE
                statuses_by_family[family].append(effective_error_status)
                warnings.append(error)
                reason_records.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNAVAILABLE,
                        ReasonScope.SOURCE,
                        provider,
                        source_id=provider,
                        family=family,
                        observed_at=as_of,
                        detail=effective_error_status.value,
                    )
                )
                continue
            if result is None:
                failures_by_family.add(family)
                continue
            policy_decision = result.policy_decision
            reason_records.extend(result.reason_records)
            if policy_decision is None and result.provider in SOURCE_POLICIES:
                policy_decision = SOURCE_POLICIES[result.provider].decision
            if policy_decision == PolicyDecision.PERMISSION_REQUIRED:
                statuses_by_family[family].append(SourceStatus.PERMISSION_REQUIRED)
                warnings.append(f"{family} provider {result.provider} requires permission.")
                reason_records.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNSUPPORTED,
                        ReasonScope.SOURCE,
                        result.provider,
                        source_id=result.provider,
                        family=family,
                        observed_at=result.collected_at or as_of,
                        detail="permission_required",
                    )
                )
                continue
            if policy_decision == PolicyDecision.LICENSED_FEED_REQUIRED:
                statuses_by_family[family].append(SourceStatus.LICENSED_FEED_REQUIRED)
                warnings.append(f"{family} provider {result.provider} requires a licensed feed.")
                reason_records.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNSUPPORTED,
                        ReasonScope.SOURCE,
                        result.provider,
                        source_id=result.provider,
                        family=family,
                        observed_at=result.collected_at or as_of,
                        detail="licensed_feed_required",
                    )
                )
                continue
            if policy_decision == PolicyDecision.DEVELOPMENT_PRIVATE_ONLY:
                status = (
                    SourceStatus.LICENSED_FEED_REQUIRED
                    if family == "options_flow"
                    else SourceStatus.UNAVAILABLE
                )
                statuses_by_family[family].append(status)
                warnings.append(
                    f"{family} provider {result.provider} is private diagnostic only; "
                    "no production evidence or coverage credit was granted."
                )
                reason_records.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNSUPPORTED,
                        ReasonScope.SOURCE,
                        result.provider,
                        source_id=result.provider,
                        family=family,
                        observed_at=result.collected_at or as_of,
                        detail="development_private_only",
                    )
                )
                continue
            inferred_status = result.status or (
                SourceStatus.FRESH if result.evidence else SourceStatus.NO_OBSERVATIONS
            )
            statuses_by_family[family].append(inferred_status)
            if not result.evidence:
                no_evidence_reason = (
                    ReasonCode.OBSERVED_NONE
                    if inferred_status == SourceStatus.NO_OBSERVATIONS
                    else ReasonCode.SOURCE_UNSUPPORTED
                    if inferred_status == SourceStatus.UNSUPPORTED
                    else ReasonCode.SOURCE_UNAVAILABLE
                )
                reason_records.append(
                    scoped_reason(
                        no_evidence_reason,
                        ReasonScope.SOURCE,
                        result.provider,
                        source_id=result.provider,
                        family=family,
                        observed_at=result.collected_at or as_of,
                        detail=inferred_status.value,
                    )
                )
            warnings.extend(self._sanitize_warning(warning) for warning in result.warnings)
            if result.degraded:
                warnings.append(f"{family} used degraded provider {result.provider}.")
            for original in result.evidence:
                item = original.model_copy(deep=True)
                item.timestamp = self._as_utc(item.timestamp)
                item.raw_signal = (
                    bounded_raw(item.raw_signal) if item.raw_signal is not None else None
                )
                if item.timestamp < cutoff:
                    stale.add(family)
                    statuses_by_family[family].append(SourceStatus.STALE)
                    reason_records.append(
                        scoped_reason(
                            ReasonCode.SOURCE_UNAVAILABLE,
                            ReasonScope.CANDIDATE,
                            self._evidence_scope_id(item),
                            source_id=(item.sources[0].source_id if item.sources else None),
                            family=family,
                            observed_at=item.timestamp,
                            detail="outside_lookback",
                        )
                    )
                    continue
                evidence.append(item)
                used_source_ids.add(result.provider)

        evidence = self._deduplicate(evidence)
        for item in evidence:
            scope_id = self._evidence_scope_id(item)
            if item.context and item.context.materiality == "discovery_only":
                reason_records.append(
                    scoped_reason(
                        ReasonCode.DISCOVERY_ONLY,
                        ReasonScope.CANDIDATE,
                        scope_id,
                        source_id=(item.sources[0].source_id if item.sources else None),
                        family=item.family,
                        observed_at=item.timestamp,
                    )
                )
            if item.context and item.context.materiality == "not_material":
                reason_records.append(
                    scoped_reason(
                        ReasonCode.EVALUATED_NOT_MATERIAL,
                        ReasonScope.CANDIDATE,
                        scope_id,
                        source_id=(item.sources[0].source_id if item.sources else None),
                        family=item.family,
                        observed_at=item.timestamp,
                    )
                )
        observed_canonical = {item.family for item in evidence} & set(self.expected_families)
        missing = set(self.expected_families) - observed_canonical
        configured_families = {adapter.family for adapter in self.adapters}
        if not self.adapters:
            warnings.append("No live evidence adapters are configured.")
        for family in sorted(missing):
            if family not in configured_families:
                expected_provider = EXPECTED_PROVIDERS.get(family, "a configured provider")
                warnings.append(
                    f"{family} is unconfigured; expected {expected_provider} "
                    "and has no fresh evidence."
                )
                reason_records.append(
                    scoped_reason(
                        ReasonCode.SOURCE_UNSUPPORTED,
                        ReasonScope.FAMILY,
                        family,
                        family=family,
                        observed_at=as_of,
                        detail="unconfigured",
                    )
                )
            elif family not in failures_by_family:
                providers = ", ".join(sorted(providers_by_family[family])) or "configured provider"
                warnings.append(f"{family} has no fresh evidence from {providers}.")
        for family in sorted(stale):
            warnings.append(f"{family} contained evidence older than the lookback window.")

        scored = self.scorer.score(
            evidence,
            as_of=as_of,
            lookback_days=request.lookback_days,
            expected_families=self.expected_families,
        )
        for family in sorted({item.family for item in scored.evidence if item.confidence < 0.50}):
            warnings.append(f"{family} contains evidence with confidence below 0.50.")
        if scored.edge.confidence < 0.50:
            warnings.append("Overall confidence is below 0.50.")
        caveats = [
            "Deterministic v1 scoring is not backtested.",
            "This dossier does not provide an investment recommendation.",
        ]

        compact = self._compact(scored.evidence)
        attributions = source_attributions(used_source_ids)
        summary = build_summary(compact, missing, request.risk_mode)
        checks = next_checks(compact, request.risk_mode, request.lookback_days)
        output = self._apply_options(compact, request)
        coverage = (
            "none"
            if not observed_canonical
            else "complete"
            if observed_canonical == set(self.expected_families)
            else "partial"
        )
        family_statuses = []
        for family in sorted(self.expected_families):
            if family in observed_canonical:
                status = SourceStatus.FRESH
                available = True
                reason = "fresh_evidence"
                observed_at = max(item.timestamp for item in evidence if item.family == family)
                coverage_ratio = 1.0
            else:
                candidates = statuses_by_family[family]
                status = (
                    max(candidates, key=STATUS_PRIORITY.__getitem__)
                    if candidates
                    else (DEFAULT_MISSING_STATUS.get(family, SourceStatus.NO_OBSERVATIONS))
                )
                available = False
                reason = (
                    "licensed_transaction_feed_required"
                    if family == "options_flow" and status == SourceStatus.LICENSED_FEED_REQUIRED
                    else "licensed_ohlc_feed_required"
                    if family == "technical" and status == SourceStatus.LICENSED_FEED_REQUIRED
                    else status.value
                )
                observed_at = None
                coverage_ratio = 0.0
            family_statuses.append(
                FamilyStatus(
                    family=family,
                    available=available,
                    status=status,
                    reason=reason,
                    observed_at=observed_at,
                    coverage_ratio=coverage_ratio,
                )
            )
        ordered_reason_records = ordered_reasons(reason_records)
        response = CatalystEdgeResponse(
            ticker=request.ticker,
            as_of=as_of,
            lookback_days=request.lookback_days,
            edge=scored.edge,
            summary=summary,
            evidence=output,
            attributions=attributions,
            data_quality=DataQuality(
                coverage=coverage,
                missing_families=sorted(missing),
                stale_families=sorted(stale),
                warnings=(list(dict.fromkeys(warnings))[: MAX_WARNINGS - len(caveats)] + caveats),
                family_statuses=family_statuses,
                reason_records=ordered_reason_records[:MAX_REASON_RECORDS],
                reason_record_count=len(ordered_reason_records),
                reason_records_truncated=(
                    len(ordered_reason_records) > MAX_REASON_RECORDS
                ),
            ),
            next_checks=checks,
        )
        return response

    @staticmethod
    def _evidence_scope_id(item: Evidence) -> str:
        if item.context and item.context.claim_id:
            return item.context.claim_id
        source_record = (
            item.sources[0].accession_or_record_id
            if item.sources and item.sources[0].accession_or_record_id
            else ""
        )
        payload = "\x1f".join(
            (item.family, item.signal, item.timestamp.isoformat(), source_record)
        )
        return f"candidate_{hashlib.sha256(payload.encode()).hexdigest()}"

    async def _collect(
        self, adapter: CatalystSignalAdapter, request: ToolInput
    ) -> tuple[str, str, AdapterResult | None, str | None, SourceStatus | None]:
        family = adapter.family
        provider = getattr(adapter, "provider", adapter.__class__.__name__)
        try:
            result = await asyncio.wait_for(
                adapter.collect(request.ticker, request.lookback_days),
                timeout=self.adapter_timeout_seconds,
            )
            if result.family != family:
                return (
                    family,
                    provider,
                    None,
                    f"{provider} returned a mismatched family.",
                    SourceStatus.SCHEMA_ERROR,
                )
            if result.provider == "unknown":
                result.provider = provider
            return family, provider, result, None, None
        except (TimeoutError, asyncio.TimeoutError):
            return (
                family,
                provider,
                None,
                f"{family} provider {provider} timed out.",
                SourceStatus.TIMEOUT,
            )
        except httpx.TimeoutException:
            return (
                family,
                provider,
                None,
                f"{family} provider {provider} timed out.",
                SourceStatus.TIMEOUT,
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code == 429:
                status = SourceStatus.RATE_LIMITED
                message = f"{family} provider {provider} was rate limited."
            elif status_code in {401, 403}:
                status = SourceStatus.PERMISSION_REQUIRED
                message = f"{family} provider {provider} requires permission."
            else:
                status = SourceStatus.UNAVAILABLE
                message = f"{family} provider {provider} failed: HTTPStatusError."
            return family, provider, None, message, status
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            schema_error = isinstance(exc, (KeyError, TypeError, ValueError)) or type(
                exc
            ).__name__ in {"JSONDecodeError", "XMLSyntaxError"}
            return (
                family,
                provider,
                None,
                (
                    f"{family} provider {provider} failed: {type(exc).__name__}"
                    + (" (schema_error)." if schema_error else ".")
                ),
                SourceStatus.SCHEMA_ERROR if schema_error else SourceStatus.UNAVAILABLE,
            )

    @staticmethod
    def _deduplicate(evidence: list[Evidence]) -> list[Evidence]:
        output: list[Evidence] = []
        seen: set[tuple[str, str, datetime, str]] = set()
        for item in evidence:
            url = str(item.sources[0].url) if item.sources and item.sources[0].url else ""
            key = (item.family, item.signal, item.timestamp, url.rstrip("/"))
            if key not in seen:
                seen.add(key)
                output.append(item)
        return output

    @staticmethod
    def _compact(evidence: list[Evidence]) -> list[Evidence]:
        by_family: dict[str, list[Evidence]] = defaultdict(list)
        for item in evidence:
            by_family[item.family].append(item)
        selected: list[Evidence] = []
        for items in by_family.values():
            ranked = sorted(
                items,
                key=lambda item: (-abs(item.contribution), -item.timestamp.timestamp()),
            )
            family_selection = ranked[:MAX_EVIDENCE_PER_FAMILY]
            directions = {item.direction for item in ranked if item.direction.value != "neutral"}
            selected_directions = {
                item.direction for item in family_selection if item.direction.value != "neutral"
            }
            if len(directions) > 1 and len(selected_directions) == 1:
                opposite = next(
                    item
                    for item in ranked
                    if item.direction not in selected_directions
                    and item.direction.value != "neutral"
                )
                family_selection[-1] = opposite
            selected.extend(family_selection)
        ranked = sorted(
            selected,
            key=lambda item: (-abs(item.contribution), -item.timestamp.timestamp()),
        )
        compact = ranked[:MAX_EVIDENCE_TOTAL]
        available_directions = {
            item.direction for item in ranked if item.direction.value != "neutral"
        }
        compact_directions = {
            item.direction for item in compact if item.direction.value != "neutral"
        }
        if len(available_directions) > 1 and len(compact_directions) == 1:
            contradiction = next(
                item
                for item in ranked[MAX_EVIDENCE_TOTAL:]
                if item.direction not in compact_directions and item.direction.value != "neutral"
            )
            compact[-1] = contradiction
        return compact

    @staticmethod
    def _apply_options(evidence: list[Evidence], request: ToolInput) -> list[Evidence]:
        output: list[Evidence] = []
        for original in evidence:
            item = original.model_copy(deep=True)
            item.sources = item.sources[:3] if request.include_sources else []
            if not request.include_raw_signals:
                item.raw_signal = None
            output.append(item)
        return output

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

    @staticmethod
    def _sanitize_warning(value: object) -> str:
        text = "".join(character for character in str(value) if character.isprintable())
        text = re.sub(
            r"(?i)\b(api[_-]?key|token|authorization|password|cookie)\s*[=:]\s*\S+",
            r"\1=[redacted]",
            text,
        )
        return text[:240]
