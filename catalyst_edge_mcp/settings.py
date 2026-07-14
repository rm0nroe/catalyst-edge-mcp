"""Explicit environment-backed production configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from catalyst_edge_mcp.capability_gates import options_provider_ready


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@dataclass(frozen=True, slots=True)
class Settings:
    sec_user_agent: str | None = None
    fmp_api_key: str | None = None
    finnhub_api_key: str | None = None
    flowalgo_api_key: str | None = None
    cheddarflow_api_key: str | None = None
    options_provider: str = "none"
    sentiment_model: str = "disabled"
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    issuer_feeds_enabled: bool = True
    gdelt_enabled: bool = True
    bluesky_enabled: bool = True
    evidence_store_path: str = str(
        Path.home() / ".local" / "state" / "catalyst-edge-mcp" / "evidence.sqlite3"
    )

    def launch_configuration(self) -> dict[str, object]:
        """Return a secret-free credential preflight for the live acceptance gate."""
        missing: list[str] = []
        invalid: list[str] = []
        if not self.sec_user_agent:
            missing.append("CATALYST_EDGE_SEC_USER_AGENT")
        elif "@" not in self.sec_user_agent:
            invalid.append("CATALYST_EDGE_SEC_USER_AGENT")

        conditional = {
            "fmp": bool(self.fmp_api_key),
            "finnhub": bool(self.finnhub_api_key),
            "flowalgo": bool(self.flowalgo_api_key),
            "cheddarflow": bool(self.cheddarflow_api_key),
        }

        configured = ["issuer_feed"] if self.issuer_feeds_enabled else []
        if self.gdelt_enabled:
            configured.append("gdelt")
        if self.bluesky_enabled:
            configured.append("bluesky")
        if self.sec_user_agent and "@" in self.sec_user_agent:
            configured.append("sec")
        conditional_present = [provider for provider, present in conditional.items() if present]
        return {
            "configuration_ready": not missing and not invalid,
            "configured_providers": configured,
            "conditional_credentials_present": conditional_present,
            "conditional_providers_require_policy_approval": conditional_present,
            "missing_environment_variables": missing,
            "invalid_environment_variables": invalid,
            "options_provider": self.options_provider,
            "options_entitlement_ready": options_provider_ready(self.options_provider),
            "sentiment_model": self.sentiment_model,
            "sentiment_model_ready": False,
        }

    @classmethod
    def from_env(cls) -> Settings:
        transport = os.getenv("CATALYST_EDGE_TRANSPORT", "stdio").strip()
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("CATALYST_EDGE_TRANSPORT must be 'stdio' or 'streamable-http'")
        options_provider = os.getenv("CATALYST_EDGE_OPTIONS_PROVIDER", "none").strip().lower()
        if options_provider not in {"none", "auto", "flowalgo", "cheddarflow", "yfinance"}:
            raise ValueError(
                "CATALYST_EDGE_OPTIONS_PROVIDER must be none, auto, flowalgo, "
                "cheddarflow, or yfinance"
            )
        sentiment_model = os.getenv("CATALYST_EDGE_SENTIMENT_MODEL", "disabled").strip().lower()
        if sentiment_model != "disabled":
            raise ValueError(
                "CATALYST_EDGE_SENTIMENT_MODEL must remain 'disabled' until a reviewed "
                "candidate passes every production gate"
            )
        port_text = os.getenv("CATALYST_EDGE_PORT", "8000").strip()
        try:
            port = int(port_text)
        except ValueError as exc:
            raise ValueError("CATALYST_EDGE_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("CATALYST_EDGE_PORT must be between 1 and 65535")
        host = os.getenv("CATALYST_EDGE_HOST", "127.0.0.1").strip()
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("CATALYST_EDGE_HOST must be a loopback address")
        issuer_feeds = os.getenv("CATALYST_EDGE_ISSUER_FEEDS", "enabled").strip().lower()
        if issuer_feeds not in {"enabled", "disabled"}:
            raise ValueError("CATALYST_EDGE_ISSUER_FEEDS must be 'enabled' or 'disabled'")
        gdelt = os.getenv("CATALYST_EDGE_GDELT", "enabled").strip().lower()
        if gdelt not in {"enabled", "disabled"}:
            raise ValueError("CATALYST_EDGE_GDELT must be 'enabled' or 'disabled'")
        bluesky = os.getenv("CATALYST_EDGE_BLUESKY", "enabled").strip().lower()
        if bluesky not in {"enabled", "disabled"}:
            raise ValueError("CATALYST_EDGE_BLUESKY must be 'enabled' or 'disabled'")
        return cls(
            sec_user_agent=_optional_env("CATALYST_EDGE_SEC_USER_AGENT"),
            fmp_api_key=_optional_env("FMP_API_KEY"),
            finnhub_api_key=_optional_env("FINNHUB_API_KEY"),
            flowalgo_api_key=_optional_env("FLOWALGO_API_KEY"),
            cheddarflow_api_key=_optional_env("CHEDDARFLOW_API_KEY"),
            options_provider=options_provider,
            sentiment_model=sentiment_model,
            transport=transport,
            host=host,
            port=port,
            issuer_feeds_enabled=issuer_feeds == "enabled",
            gdelt_enabled=gdelt == "enabled",
            bluesky_enabled=bluesky == "enabled",
            evidence_store_path=(
                _optional_env("CATALYST_EDGE_EVIDENCE_STORE")
                or str(
                    Path.home()
                    / ".local"
                    / "state"
                    / "catalyst-edge-mcp"
                    / "evidence.sqlite3"
                )
            ),
        )
