"""Fail closed on Catalyst Edge MCPB source and bundle drift."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path, PurePosixPath

from scripts.normalize_mcpb import FIXED_ZIP_TIMESTAMP

PACKAGE = "catalyst-edge-mcp"
PACKAGE_VERSION = "0.1.4"
MCPB_CLI_VERSION = "2.1.2"
MCPB_CLI_INTEGRITY = (
    "sha512-goRbBC8ySo7SWb7tRzr+tL6FxDc4JPTRCdgfD2omba7freofvjq5rom1lBnYHZHo6Mizs1j"
    "AHJeN53aZbDoy8A=="
)
EXPECTED_TOOLS = ["catalyst_edge_score", "catalyst_edge_claim_sources"]
EXPECTED_ENV = {
    "CATALYST_EDGE_SEC_USER_AGENT": "${user_config.sec_user_agent}",
    "CATALYST_EDGE_EVIDENCE_STORE": "${user_config.evidence_store}",
    "CATALYST_EDGE_TRANSPORT": "stdio",
    "CATALYST_EDGE_ISSUER_FEEDS": "disabled",
    "CATALYST_EDGE_GDELT": "enabled",
    "CATALYST_EDGE_BLUESKY": "disabled",
    "CATALYST_EDGE_OPTIONS_PROVIDER": "none",
    "CATALYST_EDGE_SENTIMENT_MODEL": "disabled",
}
REQUIRED_MEMBERS = {
    "LICENSE",
    "README.md",
    "catalyst_edge_mcp/data/reviewed_registries.json",
    "catalyst_edge_mcp/server.py",
    "icon.png",
    "manifest.json",
    "pyproject.toml",
    "server.json",
    "uv.lock",
}
ALLOWED_ROOTS = {
    ".mcpbignore",
    "LICENSE",
    "README.md",
    "catalyst_edge_mcp",
    "icon.png",
    "manifest.json",
    "pyproject.toml",
    "server.json",
    "uv.lock",
}
PROHIBITED_PARTS = {
    ".git",
    ".github",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "docs",
    "node_modules",
    "scripts",
    "tests",
    "thoughts",
}
PROHIBITED_SUFFIXES = (".db", ".log", ".pyc", ".pyo", ".sqlite", ".sqlite3", "-shm", "-wal")


def _json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _declared_version(pyproject: Path) -> str:
    match = re.search(r'^version = "([^"]+)"$', pyproject.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError("pyproject.toml has no project version")
    return match.group(1)


def _validate_source(repo: Path) -> dict[str, object]:
    manifest = _json(repo / "manifest.json")
    server_registry = _json(repo / "server.json")
    package = _json(repo / "package.json")
    lock = _json(repo / "package-lock.json")

    versions = {
        _declared_version(repo / "pyproject.toml"),
        manifest.get("version"),
        server_registry.get("version"),
        package.get("version"),
    }
    if versions != {PACKAGE_VERSION}:
        raise ValueError(f"package version drift: {sorted(str(value) for value in versions)}")
    if manifest.get("manifest_version") != "0.4":
        raise ValueError("MCPB UV manifest_version must be 0.4")
    server = manifest.get("server")
    if not isinstance(server, dict) or server.get("type") != "uv":
        raise ValueError("manifest server must use the uv runtime")
    if server.get("entry_point") != "catalyst_edge_mcp/server.py":
        raise ValueError("manifest entry point differs")
    config = server.get("mcp_config")
    if not isinstance(config, dict) or config.get("env") != EXPECTED_ENV:
        raise ValueError("manifest environment is not the fail-closed public default")
    tools = manifest.get("tools")
    tool_names = (
        [tool.get("name") for tool in tools if isinstance(tool, dict)]
        if isinstance(tools, list)
        else []
    )
    if tool_names != EXPECTED_TOOLS:
        raise ValueError("manifest must declare exactly the two public tools")
    if manifest.get("tools_generated") is not False:
        raise ValueError("manifest must prohibit generated tools")
    if manifest.get("icon") != "icon.png":
        raise ValueError("manifest must declare the bundled icon")
    if "default" in manifest["user_config"]["evidence_store"]:
        raise ValueError("evidence_store must use the server default when left blank")
    privacy_policies = manifest.get("privacy_policies")
    if not isinstance(privacy_policies, list) or not privacy_policies or not all(
        isinstance(url, str) and url.startswith("https://") for url in privacy_policies
    ):
        raise ValueError("manifest privacy policies must be HTTPS URLs")
    user_config = manifest.get("user_config")
    if not isinstance(user_config, dict):
        raise ValueError("manifest user_config is missing")
    sec_identity = user_config.get("sec_user_agent")
    if not isinstance(sec_identity, dict) or sec_identity.get("required") is not True:
        raise ValueError("SEC monitored identity must be required")
    if sec_identity.get("sensitive") is not False:
        raise ValueError("SEC monitored identity must not be misrepresented as a secret")
    dev_dependencies = package.get("devDependencies")
    if (
        not isinstance(dev_dependencies, dict)
        or dev_dependencies.get("@anthropic-ai/mcpb") != MCPB_CLI_VERSION
    ):
        raise ValueError("package.json does not pin the MCPB CLI")
    lock_package = lock.get("packages", {}).get("node_modules/@anthropic-ai/mcpb", {})
    if (
        lock_package.get("version") != MCPB_CLI_VERSION
        or lock_package.get("integrity") != MCPB_CLI_INTEGRITY
    ):
        raise ValueError("package-lock.json MCPB CLI version or integrity differs")
    scripts = package.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("mcpb:sign") != (
        "uv run --frozen python scripts/sign_mcpb.py"
    ):
        raise ValueError("package.json does not use the reviewed MCPB compatibility signer")

    return {
        "package_version": PACKAGE_VERSION,
        "manifest_version": manifest["manifest_version"],
        "mcpb_cli_version": MCPB_CLI_VERSION,
        "mcpb_cli_integrity": MCPB_CLI_INTEGRITY,
        "signer": "scripts/sign_mcpb.py",
        "tools": EXPECTED_TOOLS,
    }


def _prohibited(name: str) -> bool:
    path = PurePosixPath(name)
    folded_parts = {part.casefold() for part in path.parts}
    basename = path.name.casefold()
    return (
        bool(PROHIBITED_PARTS.intersection(folded_parts))
        or basename == ".env"
        or basename.startswith((".env.", "credential", "secret"))
        or basename.endswith(PROHIBITED_SUFFIXES)
    )


def _validate_bundle(bundle: Path) -> dict[str, object]:
    with zipfile.ZipFile(bundle) as archive:
        items = [item for item in archive.infolist() if not item.is_dir()]
        members = [item.filename.rstrip("/") for item in items]
        manifest = json.loads(archive.read("manifest.json"))
    unsafe = sorted(
        name for name in members if name.startswith("/") or ".." in PurePosixPath(name).parts
    )
    missing = sorted(REQUIRED_MEMBERS.difference(members))
    unexpected_roots = sorted({PurePosixPath(name).parts[0] for name in members} - ALLOWED_ROOTS)
    prohibited = sorted(name for name in members if _prohibited(name))
    timestamps = {item.date_time for item in items}
    if unsafe or missing or unexpected_roots or prohibited or timestamps != {FIXED_ZIP_TIMESTAMP}:
        raise ValueError(
            "MCPB inventory differs: "
            f"unsafe={unsafe}, missing={missing}, unexpected_roots={unexpected_roots}, "
            f"prohibited={prohibited}, timestamps={sorted(timestamps)}"
        )
    if members != sorted(members):
        raise ValueError("MCPB members are not in deterministic order")
    if manifest.get("version") != PACKAGE_VERSION:
        raise ValueError("bundled manifest version differs")
    return {
        "path": str(bundle.resolve()),
        "sha256": _sha256(bundle),
        "member_count": len(members),
        "members": sorted(members),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--record", type=Path)
    args = parser.parse_args()
    try:
        result = {"source": _validate_source(args.repo_root.resolve())}
        if args.bundle is not None:
            result["bundle"] = _validate_bundle(args.bundle.resolve())
        if args.record is not None:
            args.record.parent.mkdir(parents=True, exist_ok=True)
            args.record.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"MCPB verification failed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
