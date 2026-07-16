import os
from pathlib import Path

import pytest

from catalyst_edge_mcp.settings import Settings

CONDITIONAL_ENVIRONMENT_VARIABLES = (
    "FMP_API_KEY",
    "FINNHUB_API_KEY",
    "FLOWALGO_API_KEY",
    "CHEDDARFLOW_API_KEY",
)
PROVIDER_ENV = (
    "CATALYST_EDGE_SEC_USER_AGENT",
    *CONDITIONAL_ENVIRONMENT_VARIABLES,
)


@pytest.fixture(autouse=True)
def _isolate_settings_environment(monkeypatch):
    for name in tuple(os.environ):
        if name.startswith("CATALYST_EDGE_") or name in CONDITIONAL_ENVIRONMENT_VARIABLES:
            monkeypatch.delenv(name, raising=False)


def test_launch_configuration_identifies_exact_credential_requirements():
    status = Settings.from_env().launch_configuration()

    assert status["configuration_ready"] is False
    assert status["missing_environment_variables"] == ["CATALYST_EDGE_SEC_USER_AGENT"]
    assert status["invalid_environment_variables"] == []


@pytest.mark.parametrize("conditional_name", CONDITIONAL_ENVIRONMENT_VARIABLES)
def test_launch_configuration_does_not_treat_conditional_key_as_rights(
    monkeypatch, conditional_name
):
    monkeypatch.setenv("CATALYST_EDGE_SEC_USER_AGENT", " Catalyst Edge ops@example.com ")
    monkeypatch.setenv(conditional_name, " fixture-key ")

    settings = Settings.from_env()
    status = settings.launch_configuration()

    assert settings.sec_user_agent == "Catalyst Edge ops@example.com"
    assert status["configuration_ready"] is True
    assert status["missing_environment_variables"] == []
    assert status["invalid_environment_variables"] == []
    assert status["conditional_providers_require_policy_approval"]
    assert conditional_name.removesuffix("_API_KEY").lower() in status[
        "conditional_credentials_present"
    ]
    assert conditional_name.removesuffix("_API_KEY").lower() not in status[
        "configured_providers"
    ]


def test_launch_configuration_rejects_invalid_sec_identity(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_SEC_USER_AGENT", "anonymous-client")
    monkeypatch.setenv("FMP_API_KEY", "fixture-key")

    status = Settings.from_env().launch_configuration()

    assert status["configuration_ready"] is False
    assert status["invalid_environment_variables"] == ["CATALYST_EDGE_SEC_USER_AGENT"]


def test_environment_template_contains_only_empty_credential_slots():
    template = (Path(__file__).parents[1] / ".env.example").read_text()

    for name in PROVIDER_ENV:
        assert f"{name}=\n" in template


def test_evidence_store_path_is_environment_overridable(monkeypatch, tmp_path):
    store_path = tmp_path / "state.sqlite3"
    monkeypatch.setenv("CATALYST_EDGE_EVIDENCE_STORE", str(store_path))

    assert Settings.from_env().evidence_store_path == str(store_path)


def test_registry_path_is_environment_overridable(monkeypatch, tmp_path):
    registry_path = tmp_path / "reviewed.json"
    monkeypatch.setenv("CATALYST_EDGE_REGISTRY_PATH", str(registry_path))

    assert Settings.from_env().registry_path == str(registry_path)


@pytest.mark.parametrize(
    ("name", "value", "message"),
    [
        ("CATALYST_EDGE_TRANSPORT", "websocket", "CATALYST_EDGE_TRANSPORT"),
        ("CATALYST_EDGE_HOST", "0.0.0.0", "CATALYST_EDGE_HOST"),
        ("CATALYST_EDGE_PORT", "not-a-port", "CATALYST_EDGE_PORT must be an integer"),
        ("CATALYST_EDGE_PORT", "0", "CATALYST_EDGE_PORT must be between 1 and 65535"),
        ("CATALYST_EDGE_PORT", "65536", "CATALYST_EDGE_PORT must be between 1 and 65535"),
    ],
)
def test_transport_settings_reject_invalid_environment(monkeypatch, name, value, message):
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=message):
        Settings.from_env()


def test_issuer_feed_toggle_is_explicit(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_ISSUER_FEEDS", "disabled")
    assert Settings.from_env().issuer_feeds_enabled is False

    monkeypatch.setenv("CATALYST_EDGE_ISSUER_FEEDS", "sometimes")
    with pytest.raises(ValueError, match="CATALYST_EDGE_ISSUER_FEEDS"):
        Settings.from_env()


def test_gdelt_toggle_is_explicit(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_GDELT", "disabled")
    assert Settings.from_env().gdelt_enabled is False

    monkeypatch.setenv("CATALYST_EDGE_GDELT", "sometimes")
    with pytest.raises(ValueError, match="CATALYST_EDGE_GDELT"):
        Settings.from_env()


def test_gdelt_lifecycle_settings_are_bounded(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_GDELT_REFRESH_SECONDS", "600")
    monkeypatch.setenv("CATALYST_EDGE_GDELT_LOOKBACK_DAYS", "30")
    monkeypatch.setenv("CATALYST_EDGE_GDELT_MAX_AGE_SECONDS", "1800")

    settings = Settings.from_env()

    assert settings.gdelt_refresh_interval_seconds == 600
    assert settings.gdelt_refresh_lookback_days == 30
    assert settings.gdelt_freshness_max_age_seconds == 1800


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CATALYST_EDGE_GDELT_REFRESH_SECONDS", "59"),
        ("CATALYST_EDGE_GDELT_LOOKBACK_DAYS", "91"),
        ("CATALYST_EDGE_GDELT_MAX_AGE_SECONDS", "not-an-integer"),
    ],
)
def test_gdelt_lifecycle_settings_reject_invalid_values(monkeypatch, name, value):
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError, match=name):
        Settings.from_env()


def test_gdelt_max_age_cannot_be_shorter_than_refresh_interval(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_GDELT_REFRESH_SECONDS", "600")
    monkeypatch.setenv("CATALYST_EDGE_GDELT_MAX_AGE_SECONDS", "300")

    with pytest.raises(ValueError, match="CATALYST_EDGE_GDELT_MAX_AGE_SECONDS"):
        Settings.from_env()


def test_bluesky_toggle_is_explicit(monkeypatch):
    monkeypatch.setenv("CATALYST_EDGE_BLUESKY", "disabled")
    assert Settings.from_env().bluesky_enabled is False

    monkeypatch.setenv("CATALYST_EDGE_BLUESKY", "sometimes")
    with pytest.raises(ValueError, match="CATALYST_EDGE_BLUESKY"):
        Settings.from_env()


def test_sentiment_model_is_explicitly_disabled(monkeypatch):
    monkeypatch.delenv("CATALYST_EDGE_SENTIMENT_MODEL", raising=False)
    settings = Settings.from_env()
    assert settings.sentiment_model == "disabled"
    assert settings.launch_configuration()["sentiment_model_ready"] is False

    monkeypatch.setenv("CATALYST_EDGE_SENTIMENT_MODEL", "vader")
    with pytest.raises(ValueError, match="must remain 'disabled'"):
        Settings.from_env()
