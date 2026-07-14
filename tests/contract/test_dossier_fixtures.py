import json
from pathlib import Path


def test_REQUIRED_DOSSIER_FIXTURES_MAP_TO_EXECUTABLE_TESTS():
    root = Path(__file__).parents[2]
    fixture_dir = root / "tests" / "fixtures" / "dossiers"
    expected = {
        "baseline.json",
        "bearish_filing_news.json",
        "degraded_yfinance.json",
        "invalid_input.json",
        "low_confidence.json",
        "missing_insider.json",
        "mixed_attribution.json",
        "no_data.json",
        "redaction.json",
        "risk_modes.json",
        "source_raw.json",
        "stale_options.json",
        "strong_bullish.json",
        "timeout_exception.json",
        "unconfigured.json",
        "weak_social.json",
    }
    assert {path.name for path in fixture_dir.glob("*.json")} == expected

    test_source = "\n".join(path.read_text() for path in (root / "tests").rglob("test_*.py"))
    for path in fixture_dir.glob("*.json"):
        fixture = json.loads(path.read_text())
        assert fixture["scenario"]
        verifications = fixture.get("verifications", [fixture.get("verification")])
        assert all(verification and verification in test_source for verification in verifications)
