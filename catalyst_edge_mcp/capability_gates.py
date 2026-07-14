"""Reviewed fail-closed gates for conditional sentiment and options capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GateState(str, Enum):
    """A review result; only ``passed`` can satisfy a required production gate."""

    PASSED = "passed"
    FAILED = "failed"
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class GateCheck:
    name: str
    state: GateState
    note: str


@dataclass(frozen=True, slots=True)
class CapabilityAudit:
    """Immutable evidence-backed capability review."""

    candidate_id: str
    category: str
    revision: str
    checks: tuple[GateCheck, ...]
    evidence_urls: tuple[str, ...]

    def state_for(self, name: str) -> GateState:
        try:
            return next(check.state for check in self.checks if check.name == name)
        except StopIteration as exc:
            raise ValueError(f"audit {self.candidate_id} is missing required gate {name}") from exc

    def blockers(self, required_gates: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(name for name in required_gates if self.state_for(name) != GateState.PASSED)

    def production_ready(self, required_gates: tuple[str, ...]) -> bool:
        return not self.blockers(required_gates)


SENTIMENT_REQUIRED_GATES = (
    "commercial_use_rights",
    "model_or_lexicon_rights",
    "input_data_rights",
    "python_310_compatibility",
    "deterministic_preprocessing",
    "labeled_quality_benchmark",
    "rounded_output",
    "fixed_thresholds",
)

OPTIONS_REQUIRED_GATES = (
    "transaction_records",
    "contemporaneous_quotes",
    "non_display_automation_rights",
    "retention_and_storage_rights",
    "derived_output_rights",
    "documented_api",
    "deployed_account_plan_binding",
)


def _check(name: str, state: GateState, note: str) -> GateCheck:
    return GateCheck(name=name, state=state, note=note)


SENTIMENT_CANDIDATES: dict[str, CapabilityAudit] = {
    "finnhub_social_sentiment": CapabilityAudit(
        candidate_id="finnhub_social_sentiment",
        category="sentiment",
        revision="endpoint review 2026-07-13",
        checks=(
            _check(
                "commercial_use_rights",
                GateState.FAILED,
                "Current plan is personal-use unless Finnhub supplies written commercial approval.",
            ),
            _check(
                "model_or_lexicon_rights",
                GateState.MISSING,
                "Provider model and lexicon rights are not documented for this deployment.",
            ),
            _check(
                "input_data_rights",
                GateState.FAILED,
                "Social sentiment data is not commercially cleared for this deployment.",
            ),
            _check(
                "python_310_compatibility",
                GateState.PASSED,
                "The bounded HTTP adapter runs on the supported Python runtime.",
            ),
            _check(
                "deterministic_preprocessing",
                GateState.MISSING,
                "The vendor preprocessing pipeline is opaque.",
            ),
            _check(
                "labeled_quality_benchmark",
                GateState.MISSING,
                "No Catalyst ticker-scoped labeled benchmark has been run.",
            ),
            _check(
                "rounded_output",
                GateState.MISSING,
                "No approved model-output rounding contract exists.",
            ),
            _check(
                "fixed_thresholds",
                GateState.PASSED,
                "The disabled adapter uses a fixed plus/minus 0.05 delta threshold.",
            ),
        ),
        evidence_urls=(
            "https://finnhub.io/register",
            "https://api.finnhub.io/pricing",
        ),
    ),
    "textblob_0_20": CapabilityAudit(
        candidate_id="textblob_0_20",
        category="sentiment",
        revision="TextBlob 0.20.0 review 2026-07-13",
        checks=(
            _check("commercial_use_rights", GateState.PASSED, "TextBlob code is MIT licensed."),
            _check(
                "model_or_lexicon_rights",
                GateState.MISSING,
                "Vendored language assets and notices need a deployment artifact inventory.",
            ),
            _check(
                "input_data_rights",
                GateState.MISSING,
                "No production social-text source with retention and inference rights is approved.",
            ),
            _check(
                "python_310_compatibility",
                GateState.PASSED,
                "The current package declares Python 3.10 and newer.",
            ),
            _check(
                "deterministic_preprocessing",
                GateState.MISSING,
                "Ticker, URL, cashtag, emoji, language, and truncation rules are not fixed.",
            ),
            _check(
                "labeled_quality_benchmark",
                GateState.MISSING,
                "No Catalyst finance/social benchmark has been run.",
            ),
            _check("rounded_output", GateState.MISSING, "No output precision is approved."),
            _check("fixed_thresholds", GateState.MISSING, "No thresholds are approved."),
        ),
        evidence_urls=(
            "https://github.com/sloria/TextBlob/blob/dev/LICENSE",
            "https://github.com/sloria/TextBlob/blob/dev/pyproject.toml",
        ),
    ),
    "vader_sentiment_3_3": CapabilityAudit(
        candidate_id="vader_sentiment_3_3",
        category="sentiment",
        revision="VADER repository review 2026-07-13",
        checks=(
            _check("commercial_use_rights", GateState.PASSED, "VADER is MIT licensed."),
            _check(
                "model_or_lexicon_rights",
                GateState.PASSED,
                "The repository distributes the engine and lexicon under MIT.",
            ),
            _check(
                "input_data_rights",
                GateState.MISSING,
                "No production social-text source with retention and inference rights is approved.",
            ),
            _check(
                "python_310_compatibility",
                GateState.MISSING,
                "Published metadata predates an explicit Python 3.10+ compatibility matrix.",
            ),
            _check(
                "deterministic_preprocessing",
                GateState.MISSING,
                "Catalyst-specific normalization and language rules are not fixed.",
            ),
            _check(
                "labeled_quality_benchmark",
                GateState.MISSING,
                "The upstream social benchmark is not a Catalyst ticker-scoped acceptance run.",
            ),
            _check("rounded_output", GateState.MISSING, "No output precision is approved."),
            _check(
                "fixed_thresholds",
                GateState.PASSED,
                "The upstream documented compound thresholds are plus/minus 0.05.",
            ),
        ),
        evidence_urls=(
            "https://github.com/cjhutto/vaderSentiment",
            "https://github.com/cjhutto/vaderSentiment/blob/master/LICENSE.txt",
        ),
    ),
    "distilbert_sst2": CapabilityAudit(
        candidate_id="distilbert_sst2",
        category="sentiment",
        revision="distilbert SST-2 model-card review 2026-07-13",
        checks=(
            _check(
                "commercial_use_rights", GateState.PASSED, "The model card declares Apache-2.0."
            ),
            _check(
                "model_or_lexicon_rights", GateState.PASSED, "The model card declares Apache-2.0."
            ),
            _check(
                "input_data_rights",
                GateState.MISSING,
                "No production social-text source with inference rights is approved.",
            ),
            _check(
                "python_310_compatibility",
                GateState.MISSING,
                "No pinned Transformers, Torch, and Python matrix has been executed here.",
            ),
            _check(
                "deterministic_preprocessing",
                GateState.MISSING,
                "Tokenizer revision, sequence policy, and text normalization are not pinned.",
            ),
            _check(
                "labeled_quality_benchmark",
                GateState.FAILED,
                "SST-2 is generic sentence sentiment, not the required ticker-scoped "
                "finance benchmark.",
            ),
            _check("rounded_output", GateState.MISSING, "No output precision is approved."),
            _check("fixed_thresholds", GateState.MISSING, "No thresholds are approved."),
        ),
        evidence_urls=(
            "https://huggingface.co/distilbert/distilbert-base-uncased-finetuned-sst-2-english",
        ),
    ),
    "prosus_finbert": CapabilityAudit(
        candidate_id="prosus_finbert",
        category="sentiment",
        revision="ProsusAI FinBERT model-card review 2026-07-13",
        checks=(
            _check(
                "commercial_use_rights",
                GateState.MISSING,
                "The code repository is Apache-2.0 but the hosted weight card has no license tag.",
            ),
            _check(
                "model_or_lexicon_rights",
                GateState.MISSING,
                "The exact hosted weight artifact needs an explicit license decision.",
            ),
            _check(
                "input_data_rights",
                GateState.MISSING,
                "No production social-text source with inference rights is approved.",
            ),
            _check(
                "python_310_compatibility",
                GateState.MISSING,
                "No pinned Transformers, Torch, and Python matrix has been executed here.",
            ),
            _check(
                "deterministic_preprocessing",
                GateState.MISSING,
                "Tokenizer revision, sequence policy, and text normalization are not pinned.",
            ),
            _check(
                "labeled_quality_benchmark",
                GateState.MISSING,
                "Financial PhraseBank training does not replace a Catalyst social-text benchmark.",
            ),
            _check("rounded_output", GateState.MISSING, "No output precision is approved."),
            _check("fixed_thresholds", GateState.MISSING, "No thresholds are approved."),
        ),
        evidence_urls=(
            "https://github.com/ProsusAI/finBERT/blob/master/LICENSE",
            "https://huggingface.co/ProsusAI/finbert",
        ),
    ),
}


OPTIONS_ENTITLEMENTS: dict[str, CapabilityAudit] = {
    "flowalgo": CapabilityAudit(
        candidate_id="flowalgo",
        category="options_flow",
        revision="public terms review 2026-07-13",
        checks=(
            _check(
                "transaction_records",
                GateState.PASSED,
                "The product exposes order-flow records.",
            ),
            _check(
                "contemporaneous_quotes",
                GateState.MISSING,
                "No licensed API field contract for trade-time bid and ask is recorded.",
            ),
            _check(
                "non_display_automation_rights",
                GateState.FAILED,
                "Public terms prohibit automated extraction absent a separate agreement.",
            ),
            _check(
                "retention_and_storage_rights",
                GateState.MISSING,
                "No written storage entitlement is recorded.",
            ),
            _check(
                "derived_output_rights",
                GateState.FAILED,
                "Public terms prohibit redistribution and commercial reuse.",
            ),
            _check("documented_api", GateState.MISSING, "No approved API contract is recorded."),
            _check(
                "deployed_account_plan_binding",
                GateState.MISSING,
                "No written enterprise entitlement is bound to the deployed account.",
            ),
        ),
        evidence_urls=(
            "https://help.flowalgo.com/en/articles/3365195-terms-of-service-and-refund-policy",
        ),
    ),
    "cheddarflow": CapabilityAudit(
        candidate_id="cheddarflow",
        category="options_flow",
        revision="public terms review 2026-07-13",
        checks=(
            _check(
                "transaction_records",
                GateState.PASSED,
                "The product exposes order-flow records.",
            ),
            _check(
                "contemporaneous_quotes",
                GateState.PASSED,
                "The product page describes direct bid and ask context.",
            ),
            _check(
                "non_display_automation_rights",
                GateState.FAILED,
                "Public terms treat scraping as a breach absent a separate agreement.",
            ),
            _check(
                "retention_and_storage_rights",
                GateState.MISSING,
                "Personal research export does not establish service-side storage rights.",
            ),
            _check(
                "derived_output_rights",
                GateState.FAILED,
                "Public terms prohibit reproducing, distributing, or reselling data.",
            ),
            _check("documented_api", GateState.MISSING, "No approved API contract is recorded."),
            _check(
                "deployed_account_plan_binding",
                GateState.MISSING,
                "No written enterprise entitlement is bound to the deployed account.",
            ),
        ),
        evidence_urls=(
            "https://www.cheddarflow.com/refund-policy/",
            "https://www.cheddarflow.com/features/unusual-options-flow-scanner/",
        ),
    ),
    "opra_vendor": CapabilityAudit(
        candidate_id="opra_vendor",
        category="options_flow",
        revision="unselected provider 2026-07-13",
        checks=tuple(
            _check(name, GateState.MISSING, "No provider, contract, or deployed plan is selected.")
            for name in OPTIONS_REQUIRED_GATES
        ),
        evidence_urls=(),
    ),
    "yfinance": CapabilityAudit(
        candidate_id="yfinance",
        category="options_flow",
        revision="private diagnostic boundary 2026-07-13",
        checks=(
            _check(
                "transaction_records",
                GateState.FAILED,
                "A chain snapshot is not transaction-level options flow.",
            ),
            _check(
                "contemporaneous_quotes",
                GateState.FAILED,
                "The diagnostic snapshot is not an auditable trade-plus-quote feed.",
            ),
            _check(
                "non_display_automation_rights",
                GateState.FAILED,
                "The upstream data is not commercially cleared for production automation.",
            ),
            _check(
                "retention_and_storage_rights",
                GateState.FAILED,
                "No production storage entitlement is recorded.",
            ),
            _check(
                "derived_output_rights",
                GateState.FAILED,
                "No production derived-output entitlement is recorded.",
            ),
            _check(
                "documented_api",
                GateState.FAILED,
                "The library is a private diagnostic wrapper, not a licensed vendor API.",
            ),
            _check(
                "deployed_account_plan_binding",
                GateState.FAILED,
                "No eligible deployed vendor account exists.",
            ),
        ),
        evidence_urls=("https://github.com/ranaroussi/yfinance",),
    ),
}


def sentiment_candidate_ready(candidate_id: str) -> bool:
    return SENTIMENT_CANDIDATES[candidate_id].production_ready(SENTIMENT_REQUIRED_GATES)


def options_provider_ready(provider: str) -> bool:
    audit = OPTIONS_ENTITLEMENTS.get(provider)
    return bool(audit and audit.production_ready(OPTIONS_REQUIRED_GATES))
