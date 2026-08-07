"""Verify local release artifacts, timed onboarding, and reversible installs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

PACKAGE = "catalyst-edge-mcp"
EXPECTED_TOOLS = ["catalyst_edge_score", "catalyst_edge_claim_sources"]
REQUIRED_ENTRYPOINTS = {"catalyst-edge-mcp", "catalyst-edge-score", "catalyst-edge-smoke"}
REQUIRED_SDIST_PATHS = {
    "LICENSE",
    "README.md",
    "catalyst_edge_mcp/data/reviewed_registries.json",
    "server.json",
}
PROHIBITED_PARTS = {
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "notes",
    "notes",
}
PROHIBITED_SUFFIXES = (".db", ".pyc", ".pyo", ".sqlite", ".sqlite3", "-shm", "-wal")
SECRET_ENV_NAMES = {
    "FMP_API_KEY",
    "FINNHUB_API_KEY",
    "FLOWALGO_API_KEY",
    "CHEDDARFLOW_API_KEY",
}
HTTP_START_ATTEMPTS = 3
HTTP_START_TIMEOUT_SECONDS = 30
EXPECTED_GATES = {
    "R0": "met_locally",
    "R1": "partial",
    "R2": "partial",
    "R3": "partial",
    "R4": "partial",
    "R5": "partial",
    "R6": "met_locally",
    "R7": "open_delivery_blocking",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        command,
        check=True,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.stdout.strip()


def _venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_server(venv: Path) -> Path:
    return venv / ("Scripts/catalyst-edge-mcp.exe" if os.name == "nt" else "bin/catalyst-edge-mcp")


def _inspect_sdist(path: Path) -> dict[str, object]:
    with tarfile.open(path, "r:gz") as archive:
        members = archive.getmembers()
    names = [member.name for member in members]
    unsafe = [
        member.name
        for member in members
        if member.name.startswith("/")
        or ".." in Path(member.name).parts
        or not (member.isfile() or member.isdir())
    ]
    if unsafe:
        raise ValueError(f"unsafe sdist members: {unsafe}")

    relative_names = ["/".join(Path(name).parts[1:]) for name in names]
    missing = sorted(REQUIRED_SDIST_PATHS.difference(relative_names))
    prohibited = sorted(name for name in relative_names if _prohibited_sdist_path(name))
    if missing or prohibited:
        raise ValueError(f"sdist missing={missing}, prohibited={prohibited}")
    return {
        "member_count": len(names),
        "required_paths": sorted(REQUIRED_SDIST_PATHS),
        "prohibited_paths": prohibited,
    }


def _prohibited_sdist_path(name: str) -> bool:
    path = Path(name)
    folded_parts = {part.casefold() for part in path.parts}
    basename = path.name.casefold()
    prohibited_env = basename == ".env" or (
        basename.startswith(".env.") and basename != ".env.example"
    )
    return (
        bool(PROHIBITED_PARTS.intersection(folded_parts))
        or prohibited_env
        or basename.endswith(PROHIBITED_SUFFIXES)
        or basename.startswith(("credential", "secret"))
    )


def _entrypoints(python: Path) -> tuple[str, list[str]]:
    program = (
        "import json; from importlib.metadata import distribution; "
        f"d=distribution({PACKAGE!r}); "
        "print(json.dumps({'version': d.version, "
        "'entrypoints': sorted(e.name for e in d.entry_points if e.group == 'console_scripts')}))"
    )
    payload = json.loads(_run([str(python), "-c", program]))
    names = payload["entrypoints"]
    missing = sorted(REQUIRED_ENTRYPOINTS.difference(names))
    if missing:
        raise ValueError(f"installed artifact is missing entry points: {missing}")
    return payload["version"], names


def _base_offline_env(store: Path) -> dict[str, str]:
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("CATALYST_EDGE_") and name not in SECRET_ENV_NAMES
    }
    environment.update(
        {
            "CATALYST_EDGE_TRANSPORT": "stdio",
            "CATALYST_EDGE_ISSUER_FEEDS": "disabled",
            "CATALYST_EDGE_GDELT": "disabled",
            "CATALYST_EDGE_BLUESKY": "disabled",
            "CATALYST_EDGE_OPTIONS_PROVIDER": "none",
            "CATALYST_EDGE_SENTIMENT_MODEL": "disabled",
            "CATALYST_EDGE_EVIDENCE_STORE": str(store),
        }
    )
    return environment


def _load_config(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not all(
        isinstance(name, str) and isinstance(value, str) for name, value in payload.items()
    ):
        raise ValueError("configuration must be a JSON object of string values")
    invalid = sorted(name for name in payload if not name.startswith("CATALYST_EDGE_"))
    secret_like = sorted(
        name
        for name in payload
        if any(token in name.upper() for token in ("KEY", "SECRET", "TOKEN"))
    )
    if invalid or secret_like:
        raise ValueError(f"configuration invalid={invalid}, secret_like={secret_like}")
    return payload


def _validate_no_data(result) -> dict[str, object]:
    if getattr(result, "isError", None) is not False:
        raise ValueError("installed no-data call returned an MCP error")
    payload = getattr(result, "structuredContent", None)
    if set(payload or {}) == {"result"}:
        payload = payload["result"]
    if not isinstance(payload, dict):
        raise ValueError("installed no-data call returned no structured response")
    required = {
        "ticker",
        "as_of",
        "lookback_days",
        "edge",
        "summary",
        "evidence",
        "attributions",
        "data_quality",
        "next_checks",
    }
    if set(payload) != required:
        raise ValueError(f"installed response keys differ: {sorted(payload)}")
    edge = payload["edge"]
    data_quality = payload["data_quality"]
    evidence = payload["evidence"]
    if not isinstance(edge, dict) or not isinstance(data_quality, dict):
        raise ValueError("installed response has malformed nested structures")
    if not isinstance(evidence, list):
        raise ValueError("installed response evidence must be a list")
    if payload["ticker"] != "NVDA" or payload["lookback_days"] != 14:
        raise ValueError("installed response does not match the requested no-data case")
    if edge.get("scoring_method") != "deterministic_v1":
        raise ValueError("installed response uses an unexpected scoring method")
    if edge.get("model_status") != "not_trained":
        raise ValueError("installed response uses an unexpected model status")
    if data_quality.get("coverage") != "none" or evidence or payload["attributions"]:
        raise ValueError("offline installed response is not the typed no-data case")
    return payload


def _validate_tools(tools: list[str]) -> list[str]:
    if tools != EXPECTED_TOOLS:
        raise ValueError(f"installed tool discovery differs: {tools}")
    return tools


async def _probe_session(session: ClientSession) -> tuple[list[str], dict[str, object]]:
    listed_tools = (await session.list_tools()).tools
    tools = _validate_tools([tool.name for tool in listed_tools])
    score_tool = next(tool for tool in listed_tools if tool.name == "catalyst_edge_score")
    response = _validate_no_data(
        await session.call_tool("catalyst_edge_score", {"ticker": "NVDA"})
    )
    try:
        Draft202012Validator(score_tool.outputSchema).validate(response)
    except JsonSchemaValidationError as exc:
        raise ValueError(f"installed response failed its MCP output schema: {exc.message}") from exc
    return tools, response


async def _probe(server: Path, environment: dict[str, str]) -> dict[str, object]:
    parameters = StdioServerParameters(command=str(server), env=environment)
    async with (
        stdio_client(parameters) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        tools, response = await _probe_session(session)
        discovered_at = time.monotonic()
    return {
        "tools": tools,
        "discovered_at_monotonic": discovered_at,
        "response": {
            "ticker": response["ticker"],
            "coverage": response["data_quality"]["coverage"],
            "scoring_method": response["edge"]["scoring_method"],
            "model_status": response["edge"]["model_status"],
        },
    }


def _ephemeral_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _terminate_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _captured_stderr(stderr_file) -> str:
    stderr_file.seek(0)
    return stderr_file.read().decode(errors="replace")


def _wait_for_http_server(process: subprocess.Popen, port: int, stderr_file) -> str | None:
    deadline = time.monotonic() + HTTP_START_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return _captured_stderr(stderr_file)
        try:
            httpx.get(f"http://127.0.0.1:{port}/mcp", timeout=0.2)
            return None
        except httpx.TransportError:
            time.sleep(0.05)
    _terminate_process(process)
    return f"readiness timeout after {HTTP_START_TIMEOUT_SECONDS}s\n{_captured_stderr(stderr_file)}"


async def _probe_http(server: Path, environment: dict[str, str]) -> dict[str, object]:
    last_error = ""
    for attempt in range(HTTP_START_ATTEMPTS):
        port = _ephemeral_port()
        http_environment = dict(environment)
        http_environment.update(
            {
                "CATALYST_EDGE_TRANSPORT": "streamable-http",
                "CATALYST_EDGE_HOST": "127.0.0.1",
                "CATALYST_EDGE_PORT": str(port),
            }
        )
        with tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen(
                [str(server)],
                env=http_environment,
                stdout=subprocess.DEVNULL,
                stderr=stderr_file,
            )
            try:
                startup_error = _wait_for_http_server(process, port, stderr_file)
                if startup_error is not None:
                    last_error = startup_error
                    collision = "address already in use" in startup_error.lower()
                    if collision and attempt + 1 < HTTP_START_ATTEMPTS:
                        continue
                    raise ValueError(f"installed HTTP server did not start: {startup_error}")
                async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as streams:
                    read_stream, write_stream, _ = streams
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        tools, response = await _probe_session(session)
                return {
                    "tools": tools,
                    "response": {
                        "ticker": response["ticker"],
                        "coverage": response["data_quality"]["coverage"],
                        "scoring_method": response["edge"]["scoring_method"],
                        "model_status": response["edge"]["model_status"],
                    },
                }
            finally:
                _terminate_process(process)
    raise ValueError(f"installed HTTP server could not bind: {last_error}")


def _install(
    artifact: Path,
    *,
    python_request: str,
    venv: Path,
    offline: bool,
) -> tuple[Path, str, list[str]]:
    _run(["uv", "venv", "--python", python_request, str(venv)])
    python = _venv_python(venv)
    command = ["uv", "pip", "install", "--python", str(python)]
    if offline:
        command.append("--offline")
    command.append(str(artifact.resolve()))
    _run(command)
    version, entrypoints = _entrypoints(python)
    return python, version, entrypoints


def _write_manifest(path: Path, artifacts: list[Path]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{_sha256(artifact)}  {artifact.name}" for artifact in artifacts]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _validate_versions(wheel_version: str, sdist_version: str) -> str:
    if wheel_version != sdist_version:
        raise ValueError(f"wheel/sdist version mismatch: {wheel_version} != {sdist_version}")
    return wheel_version


def _artifact_command(args: argparse.Namespace) -> int:
    wheel = args.wheel.resolve()
    sdist = args.sdist.resolve()
    for artifact in (wheel, sdist):
        if not artifact.is_file():
            raise ValueError(f"artifact not found: {artifact}")

    started_at = _utc_now()
    timer_start = time.monotonic()
    sdist_inventory = _inspect_sdist(sdist)
    hashes = {artifact.name: _sha256(artifact) for artifact in (wheel, sdist)}
    with tempfile.TemporaryDirectory(prefix="catalyst-edge-artifact-") as temp:
        temp_path = Path(temp)
        wheel_venv = temp_path / "wheel-venv"
        _, wheel_version, wheel_entrypoints = _install(
            wheel,
            python_request=args.python,
            venv=wheel_venv,
            offline=args.offline,
        )
        wheel_probe = asyncio.run(
            _probe(
                _venv_server(wheel_venv),
                _base_offline_env(temp_path / "wheel-evidence.sqlite3"),
            )
        )
        wheel_http_probe = asyncio.run(
            _probe_http(
                _venv_server(wheel_venv),
                _base_offline_env(temp_path / "wheel-http-evidence.sqlite3"),
            )
        )
        onboarding_seconds = wheel_probe.pop("discovered_at_monotonic") - timer_start

        sdist_venv = temp_path / "sdist-venv"
        _, sdist_version, sdist_entrypoints = _install(
            sdist,
            python_request=args.python,
            venv=sdist_venv,
            offline=args.offline,
        )
        sdist_probe = asyncio.run(
            _probe(
                _venv_server(sdist_venv),
                _base_offline_env(temp_path / "sdist-evidence.sqlite3"),
            )
        )
        sdist_probe.pop("discovered_at_monotonic")

    package_version = _validate_versions(wheel_version, sdist_version)
    _write_manifest(args.manifest, [wheel, sdist])
    record = {
        "schema_version": 1,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "python_request": args.python,
        "uv_version": _run(["uv", "--version"]),
        "package_version": package_version,
        "hashes": hashes,
        "manifest": str(args.manifest.resolve()),
        "sdist_inventory": sdist_inventory,
        "wheel": {
            "entrypoints": wheel_entrypoints,
            "probe": wheel_probe,
            "http_probe": wheel_http_probe,
        },
        "sdist": {"entrypoints": sdist_entrypoints, "probe": sdist_probe},
        "onboarding": {
            "start_boundary": "artifacts, Python, uv, and MCP SDK client available",
            "stop_boundary": "installed wheel returned exact two-tool discovery",
            "first_attempt": True,
            "elapsed_seconds": round(onboarding_seconds, 3),
            "target_seconds": 300,
            "passed": onboarding_seconds <= 300,
            "manual_corrections": [],
        },
    }
    args.record.parent.mkdir(parents=True, exist_ok=True)
    args.record.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


def _initialize_evidence_store(python: Path, store: Path) -> None:
    program = (
        "from catalyst_edge_mcp.evidence_store import EvidenceStore; "
        f"store=EvidenceStore({str(store)!r}); store.close()"
    )
    _run([str(python), "-c", program])
    with sqlite3.connect(store) as connection:
        connection.execute(
            "CREATE TABLE rollback_proof (id INTEGER PRIMARY KEY, marker TEXT NOT NULL)"
        )
        connection.execute("INSERT INTO rollback_proof(marker) VALUES (?)", ("preserve-me",))


def _installed_version(python: Path) -> str:
    program = (
        "from importlib.metadata import version; "
        f"print(version({PACKAGE!r}))"
    )
    return _run([str(python), "-c", program])


def _replace_install(artifact: Path, python: Path, *, offline: bool) -> str:
    command = ["uv", "pip", "install", "--python", str(python), "--reinstall"]
    if offline:
        command.append("--offline")
    command.append(str(artifact.resolve()))
    _run(command)
    return _installed_version(python)


def _rollback_command(args: argparse.Namespace) -> int:
    prior_wheel = args.prior_wheel.resolve()
    candidate_wheel = args.candidate_wheel.resolve()
    prior_config = _load_config(args.prior_config)
    candidate_config = _load_config(args.candidate_config)
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise ValueError("rollback output directory must be absent or empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    retained_prior_config = args.output_dir / "prior-config.json"
    retained_candidate_config = args.output_dir / "candidate-config.json"
    shutil.copy2(args.prior_config, retained_prior_config)
    shutil.copy2(args.candidate_config, retained_candidate_config)
    store = args.output_dir / "evidence.sqlite3"
    backup = args.output_dir / "evidence.sqlite3.backup"

    started_at = _utc_now()
    with tempfile.TemporaryDirectory(prefix="catalyst-edge-rollback-") as temp:
        venv = Path(temp) / "venv"
        python, prior_version, prior_entrypoints = _install(
            prior_wheel,
            python_request=args.python,
            venv=venv,
            offline=args.offline,
        )
        _initialize_evidence_store(python, store)
        shutil.copy2(store, backup)
        backup_hash = _sha256(backup)

        prior_env = _base_offline_env(store)
        prior_env.update(prior_config)
        initial_probe = asyncio.run(_probe(_venv_server(venv), prior_env))
        initial_probe.pop("discovered_at_monotonic")

        candidate_version = _replace_install(candidate_wheel, python, offline=args.offline)
        candidate_env = _base_offline_env(store)
        candidate_env.update(candidate_config)
        candidate_probe = asyncio.run(_probe(_venv_server(venv), candidate_env))
        candidate_probe.pop("discovered_at_monotonic")
        after_candidate_hash = _sha256(store)

        restored_version = _replace_install(prior_wheel, python, offline=args.offline)
        restored_probe = asyncio.run(_probe(_venv_server(venv), prior_env))
        restored_probe.pop("discovered_at_monotonic")

    final_hash = _sha256(store)
    if restored_version != prior_version:
        raise ValueError(f"rollback restored {restored_version}, expected {prior_version}")
    if backup_hash != after_candidate_hash or backup_hash != final_hash:
        raise ValueError("evidence store changed during forward install or rollback")
    with sqlite3.connect(store) as connection:
        marker = connection.execute("SELECT marker FROM rollback_proof").fetchone()
    if marker != ("preserve-me",):
        raise ValueError("rollback evidence marker was not preserved")

    record = {
        "schema_version": 1,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "python_request": args.python,
        "uv_version": _run(["uv", "--version"]),
        "prior": {
            "version": prior_version,
            "wheel": prior_wheel.name,
            "wheel_sha256": _sha256(prior_wheel),
            "config_sha256": _sha256(retained_prior_config),
            "entrypoints": prior_entrypoints,
            "probe": initial_probe,
        },
        "candidate": {
            "version": candidate_version,
            "wheel": candidate_wheel.name,
            "wheel_sha256": _sha256(candidate_wheel),
            "config_sha256": _sha256(retained_candidate_config),
            "probe": candidate_probe,
        },
        "rollback": {
            "restored_version": restored_version,
            "probe": restored_probe,
            "evidence_store_backup_sha256": backup_hash,
            "evidence_store_after_candidate_sha256": after_candidate_hash,
            "evidence_store_after_rollback_sha256": final_hash,
            "evidence_marker": marker[0],
            "passed": True,
        },
    }
    record_path = args.output_dir / "rollback-verification.json"
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0


def _json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON record must be an object: {path}")
    return payload


def _record_path(repo_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("evidence path must be a non-empty string")
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _require_hash(path: Path, expected: object) -> None:
    if not path.is_file():
        raise ValueError(f"evidence file is missing: {path}")
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"invalid recorded SHA-256 for {path}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"stale evidence hash for {path}: {actual} != {expected}")


def _declared_version(path: Path, package_name: str | None = None) -> str:
    text = path.read_text(encoding="utf-8")
    if package_name is None:
        match = re.search(r'^version = "([^"]+)"$', text, re.MULTILINE)
    else:
        match = re.search(
            rf'\[\[package\]\]\s+name = "{re.escape(package_name)}"\s+version = "([^"]+)"',
            text,
        )
    if match is None:
        raise ValueError(f"package version not found in {path}")
    return match.group(1)


def _validate_probe_record(probe: object) -> None:
    if not isinstance(probe, dict):
        raise ValueError("installed-artifact probe record is malformed")
    _validate_tools(probe.get("tools"))
    expected_response = {
        "ticker": "NVDA",
        "coverage": "none",
        "scoring_method": "deterministic_v1",
        "model_status": "not_trained",
    }
    if probe.get("response") != expected_response:
        raise ValueError("installed-artifact probe record is not the typed no-data case")


def _collected_test_count(python_request: str) -> int:
    output = _run(
        [
            "uv",
            "run",
            "--frozen",
            "--extra",
            "dev",
            "--python",
            python_request,
            "pytest",
            "--collect-only",
            "-q",
        ]
    )
    counts = [int(match.group(1)) for match in re.finditer(r":\s+(\d+)$", output, re.MULTILINE)]
    if not counts:
        raise ValueError(f"could not parse collected test count for Python {python_request}")
    return sum(counts)


def _audit_command(args: argparse.Namespace) -> int:
    repo_root = args.repo_root.resolve()
    record = _json_object(args.record.resolve())
    if record.get("schema_version") != 1:
        raise ValueError("unsupported evidence-audit schema version")
    package_version = record.get("package_version")
    pyproject_version = _declared_version(repo_root / "pyproject.toml")
    lock_version = _declared_version(repo_root / "uv.lock", PACKAGE)
    if package_version != pyproject_version or package_version != lock_version:
        raise ValueError(
            "package version mismatch: "
            f"record={package_version}, pyproject={pyproject_version}, lock={lock_version}"
        )

    source_hashes = record.get("source_hashes")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise ValueError("evidence audit requires source_hashes")
    for relative, expected in source_hashes.items():
        if (
            not isinstance(relative, str)
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError(f"invalid source hash path: {relative}")
        _require_hash(repo_root / relative, expected)

    artifact_reference = record.get("artifact_record")
    if not isinstance(artifact_reference, dict):
        raise ValueError("evidence audit requires artifact_record")
    artifact_record_path = _record_path(repo_root, artifact_reference.get("path"))
    _require_hash(artifact_record_path, artifact_reference.get("sha256"))
    artifact_record = _json_object(artifact_record_path)
    if artifact_record.get("package_version") != package_version:
        raise ValueError("artifact record package version differs")
    hashes = artifact_record.get("hashes")
    if not isinstance(hashes, dict) or len(hashes) != 2:
        raise ValueError("artifact record must contain exactly wheel and sdist hashes")
    for filename, expected in hashes.items():
        if not isinstance(filename, str) or Path(filename).name != filename:
            raise ValueError(f"invalid artifact filename: {filename}")
        _require_hash(artifact_record_path.parent / filename, expected)

    manifest_reference = record.get("manifest")
    if not isinstance(manifest_reference, dict):
        raise ValueError("evidence audit requires manifest")
    manifest_path = _record_path(repo_root, manifest_reference.get("path"))
    _require_hash(manifest_path, manifest_reference.get("sha256"))
    expected_manifest = "".join(f"{digest}  {name}\n" for name, digest in hashes.items())
    if manifest_path.read_text(encoding="utf-8") != expected_manifest:
        raise ValueError("artifact manifest content differs from artifact record")

    inventory = artifact_record.get("sdist_inventory")
    if not isinstance(inventory, dict) or inventory.get("required_paths") != sorted(
        REQUIRED_SDIST_PATHS
    ):
        raise ValueError("artifact record lacks the required sdist inventory")
    if inventory.get("prohibited_paths") != []:
        raise ValueError("artifact record contains prohibited sdist paths")
    wheel = artifact_record.get("wheel")
    sdist = artifact_record.get("sdist")
    if not isinstance(wheel, dict) or not isinstance(sdist, dict):
        raise ValueError("artifact record lacks wheel/sdist proof")
    wheel_entrypoints = wheel.get("entrypoints", [])
    sdist_entrypoints = sdist.get("entrypoints", [])
    if not isinstance(wheel_entrypoints, list) or not isinstance(sdist_entrypoints, list):
        raise ValueError("artifact record entry points are malformed")
    if not REQUIRED_ENTRYPOINTS.issubset(
        wheel_entrypoints
    ) or not REQUIRED_ENTRYPOINTS.issubset(sdist_entrypoints):
        raise ValueError("artifact record lacks required entry points")
    _validate_probe_record(wheel.get("probe"))
    _validate_probe_record(wheel.get("http_probe"))
    _validate_probe_record(sdist.get("probe"))
    onboarding = artifact_record.get("onboarding")
    if not isinstance(onboarding, dict) or onboarding.get("passed") is not True:
        raise ValueError("onboarding proof did not pass")
    if onboarding.get("first_attempt") is not True or onboarding.get("manual_corrections") != []:
        raise ValueError("onboarding proof is not an uncorrected first attempt")
    elapsed = onboarding.get("elapsed_seconds")
    target = onboarding.get("target_seconds")
    if (
        not isinstance(elapsed, (int, float))
        or not isinstance(target, (int, float))
        or elapsed > target
    ):
        raise ValueError("onboarding timing is missing or over target")

    rollback_reference = record.get("rollback_record")
    demo_reference = record.get("demo_manifest")
    if not isinstance(rollback_reference, dict) or not isinstance(demo_reference, dict):
        raise ValueError("evidence audit requires rollback and demo records")
    rollback_path = _record_path(repo_root, rollback_reference.get("path"))
    demo_path = _record_path(repo_root, demo_reference.get("path"))
    _require_hash(rollback_path, rollback_reference.get("sha256"))
    _require_hash(demo_path, demo_reference.get("sha256"))
    rollback = _json_object(rollback_path)
    rollback_result = rollback.get("rollback")
    if not isinstance(rollback_result, dict) or rollback_result.get("passed") is not True:
        raise ValueError("rollback proof did not pass")
    store_hashes = {
        rollback_result.get("evidence_store_backup_sha256"),
        rollback_result.get("evidence_store_after_candidate_sha256"),
        rollback_result.get("evidence_store_after_rollback_sha256"),
    }
    if len(store_hashes) != 1 or None in store_hashes:
        raise ValueError("rollback evidence-store hashes differ")
    if rollback_result.get("evidence_marker") != "preserve-me":
        raise ValueError("rollback evidence marker is missing")
    demo = _json_object(demo_path)
    if (
        demo.get("package_version") != package_version
        or demo.get("one_call_per_ticker") is not True
    ):
        raise ValueError("demo proof package or call boundary differs")
    if demo.get("tickers") != ["AAPL", "NVDA", "TSLA", "RKLB", "BRK.B"]:
        raise ValueError("demo proof ticker set differs")
    acceptance = demo.get("acceptance")
    if not isinstance(acceptance, dict) or not acceptance or not all(
        value is True for value in acceptance.values()
    ):
        raise ValueError("demo proof acceptance checks did not all pass")
    dossier_files = demo.get("dossier_files")
    if not isinstance(dossier_files, dict) or set(dossier_files) != set(demo["tickers"]):
        raise ValueError("demo dossier inventory differs")
    for filename in dossier_files.values():
        if not isinstance(filename, str) or not (demo_path.parent / filename).is_file():
            raise ValueError(f"demo dossier is missing: {filename}")

    test_counts = record.get("test_counts")
    if not isinstance(test_counts, dict) or set(test_counts) != {"3.10", "3.14"}:
        raise ValueError("evidence audit requires Python 3.10 and 3.14 test counts")
    for python_request, expected in test_counts.items():
        actual = _collected_test_count(python_request)
        if actual != expected:
            raise ValueError(
                f"stale test count for Python {python_request}: {actual} != {expected}"
            )
    if record.get("gates") != EXPECTED_GATES:
        raise ValueError("R0-R7 gate statuses differ from the fail-closed local boundary")

    result = {
        "status": "passed",
        "package_version": package_version,
        "source_hash_count": len(source_hashes),
        "artifact_hashes": hashes,
        "test_counts": test_counts,
        "gates": EXPECTED_GATES,
    }
    print(json.dumps(result, indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    artifact = subparsers.add_parser("artifact", help="verify wheel, sdist, and onboarding")
    artifact.add_argument("--wheel", type=Path, required=True)
    artifact.add_argument("--sdist", type=Path, required=True)
    artifact.add_argument("--python", required=True)
    artifact.add_argument("--manifest", type=Path, required=True)
    artifact.add_argument("--record", type=Path, required=True)
    artifact.add_argument("--offline", action="store_true")
    artifact.set_defaults(run=_artifact_command)

    rollback = subparsers.add_parser("rollback", help="prove forward install and rollback")
    rollback.add_argument("--prior-wheel", type=Path, required=True)
    rollback.add_argument("--candidate-wheel", type=Path, required=True)
    rollback.add_argument("--prior-config", type=Path, required=True)
    rollback.add_argument("--candidate-config", type=Path, required=True)
    rollback.add_argument("--python", required=True)
    rollback.add_argument("--output-dir", type=Path, required=True)
    rollback.add_argument("--offline", action="store_true")
    rollback.set_defaults(run=_rollback_command)

    audit = subparsers.add_parser("audit", help="fail closed on stale local RC evidence")
    audit.add_argument("--record", type=Path, required=True)
    audit.add_argument("--repo-root", type=Path, default=Path.cwd())
    audit.set_defaults(run=_audit_command)
    return parser


def main() -> None:
    args = _parser().parse_args()
    try:
        raise SystemExit(args.run(args))
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"release verification failed: {exc}", file=os.sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
