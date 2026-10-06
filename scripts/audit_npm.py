"""Run npm audit with one temporary, version-bound build-tool exception."""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

ADVISORY = "https://github.com/advisories/GHSA-86w9-cpqp-85rv"
EXPIRES = date(2026, 11, 6)
VERSIONS = {"@anthropic-ai/mcpb": "2.1.2", "node-forge": "1.4.0"}


def check_audit(report: dict, lock: dict, today: date) -> None:
    """Reject unknown reports/findings; see docs/validation/npm-audit-exception.md."""
    if report.get("error") or report.get("auditReportVersion") != 2:
        raise ValueError("npm audit failed or returned an unsupported report")
    findings = report["vulnerabilities"]
    if not isinstance(findings, dict) or report["metadata"]["vulnerabilities"]["total"] != len(
        findings
    ):
        raise ValueError("inconsistent npm audit findings")
    if not findings:
        return
    if today >= EXPIRES:
        raise ValueError(f"npm audit exception expired on {EXPIRES}")
    # ponytail: exact two-package exception; remove when upstream ships a fix.
    if set(findings) != set(VERSIONS):
        raise ValueError("npm audit contains findings outside the reviewed exception")
    for name, version in VERSIONS.items():
        node = f"node_modules/{name}"
        finding = findings[name]
        if (
            lock["packages"][node]["version"] != version
            or finding["nodes"] != [node]
            or finding["name"] != name
            or finding["fixAvailable"] is not False
        ):
            raise ValueError(f"npm audit exception scope changed: {name}")
    via = findings["node-forge"]["via"]
    if (
        not isinstance(via, list)
        or len(via) != 1
        or not isinstance(via[0], dict)
        or via[0].get("url") != ADVISORY
        or via[0].get("name") != "node-forge"
        or via[0].get("dependency") != "node-forge"
        or findings["@anthropic-ai/mcpb"]["via"] != ["node-forge"]
    ):
        raise ValueError("npm audit contains an unreviewed advisory or dependency path")
    print(f"Temporary exception: {ADVISORY}; expires {EXPIRES}; build tooling only")


def main() -> None:
    result = subprocess.run(
        ["npm", "audit", "--json", "--audit-level=low"],
        capture_output=True, text=True, check=False,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=__import__("sys").stderr)
    try:
        if result.returncode not in (0, 1):
            raise ValueError(f"npm audit exited {result.returncode}")
        report = json.loads(result.stdout)
        if result.returncode == 1 and not report.get("vulnerabilities"):
            raise ValueError("npm audit failed without vulnerability findings")
        check_audit(report, json.loads(Path("package-lock.json").read_text()), date.today())
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise SystemExit(f"npm audit gate failed: {exc}") from exc


if __name__ == "__main__":
    main()
