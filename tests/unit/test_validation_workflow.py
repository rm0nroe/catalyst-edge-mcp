import re
from pathlib import Path

import yaml

WORKFLOW = Path(__file__).parents[2] / ".github/workflows/validation.yml"


def test_validation_workflow_contract():
    payload = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    assert payload["permissions"] == {"contents": "read"}
    assert set(payload["on"]) == {"pull_request", "push"}
    assert payload["on"]["push"]["tags"] == ["v*"]
    assert payload["jobs"]["test"]["strategy"]["matrix"]["python-version"] == [
        "3.10",
        "3.14",
    ]

    steps = [
        step
        for job in payload["jobs"].values()
        for step in job["steps"]
    ]
    actions = [step["uses"] for step in steps if "uses" in step]
    assert actions
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in actions)

    commands = "\n".join(step.get("run", "") for step in steps)
    for required in (
        "uv lock --check",
        "ruff check .",
        "pytest -q",
        "uv build --no-sources",
        "scripts/verify_release.py artifact",
        "npm ci --ignore-scripts",
        "npm audit --audit-level=low",
        "npm run mcpb:validate",
        "npm run mcpb:pack",
        "scripts/verify_mcpb.py",
        'GITHUB_REF_TYPE" == "tag',
        "catalyst-edge-mcp-$version-SHA256SUMS.txt",
    ):
        assert required in commands

    serialized = WORKFLOW.read_text(encoding="utf-8").casefold()
    artifact_command = serialized.split("scripts/verify_release.py artifact", 1)[1]
    artifact_command = artifact_command.split("\n          {", 1)[0]
    assert "--offline" not in artifact_command
    for prohibited in (
        "actions/upload-artifact",
        "gh release",
        "pypa/gh-action-pypi-publish",
        "${{ secrets.",
        "permissions:\n  contents: write",
    ):
        assert prohibited not in serialized
