import re
from pathlib import Path


def test_TDD_TRACEABILITY_IDENTIFIERS_ARE_DISCOVERABLE():
    root = Path(__file__).parents[2]
    required = set(re.findall(r"`((?:UT|CT|PT|FX)_[A-Z0-9_*]+)`", (root / "TDD.md").read_text()))
    test_source = "\n".join(path.read_text() for path in (root / "tests").rglob("test_*.py"))
    discovered = set(re.findall(r"test_((?:UT|CT|PT|FX)_[A-Z0-9_]+)", test_source))

    missing = []
    for marker in sorted(required):
        pattern = "^" + re.escape(marker).replace(r"\*", ".+")
        if not any(re.match(pattern, test_name) for test_name in discovered):
            missing.append(marker)
    assert missing == []
