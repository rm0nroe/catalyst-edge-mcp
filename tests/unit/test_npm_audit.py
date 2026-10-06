import copy
from datetime import date

import pytest

from scripts.audit_npm import ADVISORY, EXPIRES, VERSIONS, check_audit


def test_npm_audit_exception_is_narrow_and_expires():
    lock = {"packages": {f"node_modules/{k}": {"version": v} for k, v in VERSIONS.items()}}
    report = {
        "auditReportVersion": 2,
        "metadata": {"vulnerabilities": {"total": 2}},
        "vulnerabilities": {
            name: {"name": name, "nodes": [f"node_modules/{name}"], "fixAvailable": False}
            for name in VERSIONS
        },
    }
    report["vulnerabilities"]["@anthropic-ai/mcpb"]["via"] = ["node-forge"]
    report["vulnerabilities"]["node-forge"]["via"] = [
        {"url": ADVISORY, "name": "node-forge", "dependency": "node-forge"}
    ]
    today = date(2026, 10, 6)
    check_audit(report, lock, today)
    check_audit({**report, "vulnerabilities": {}, "metadata": {
        "vulnerabilities": {"total": 0}
    }}, lock, EXPIRES)
    with pytest.raises(ValueError, match="expired"):
        check_audit(report, lock, EXPIRES)

    for name in VERSIONS:
        changed = copy.deepcopy(lock)
        changed["packages"][f"node_modules/{name}"]["version"] = "9.9.9"
        with pytest.raises(ValueError, match="scope changed"):
            check_audit(report, changed, today)

    bad_reports = []
    for key, value in (("url", ADVISORY + "-other"), ("dependency", "other")):
        changed = copy.deepcopy(report)
        changed["vulnerabilities"]["node-forge"]["via"][0][key] = value
        bad_reports.append(changed)
    for name, key, value in (
        ("node-forge", "via", []),
        ("node-forge", "via", ["node-forge"]),
        ("node-forge", "fixAvailable", True),
        ("node-forge", "nodes", ["node_modules/other/node_modules/node-forge"]),
        ("@anthropic-ai/mcpb", "via", ["node-forge", "other"]),
    ):
        changed = copy.deepcopy(report)
        changed["vulnerabilities"][name][key] = value
        bad_reports.append(changed)
    changed = copy.deepcopy(report)
    changed["vulnerabilities"]["undici"] = {"severity": "low"}
    changed["metadata"]["vulnerabilities"]["total"] = 3
    bad_reports.extend([changed, {**report, "error": "registry unavailable"}, {
        **report, "auditReportVersion": 99
    }, {**report, "vulnerabilities": {}}])
    for changed in bad_reports:
        with pytest.raises(ValueError):
            check_audit(changed, lock, today)


@pytest.mark.parametrize("status, output", [
    (2, '{}'), (1, '{}'), (0, 'not json'), (0, '{"error":"registry unavailable"}'),
])
def test_npm_audit_command_fails_closed(monkeypatch, status, output):
    import subprocess

    from scripts.audit_npm import main

    def audit(command, **kwargs):
        assert command == ["npm", "audit", "--json", "--audit-level=low"]
        return subprocess.CompletedProcess(command, status, stdout=output, stderr="")

    monkeypatch.setattr(subprocess, "run", audit)
    with pytest.raises(SystemExit):
        main()
