import io
import json
import tarfile
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from scripts.verify_release import (
    _entrypoints,
    _inspect_sdist,
    _load_config,
    _validate_no_data,
    _validate_tools,
    _validate_versions,
)


class _Result:
    isError = False
    structuredContent: ClassVar[dict[str, object]] = {
        "ticker": "NVDA",
        "as_of": "2026-08-02T00:00:00Z",
        "lookback_days": 14,
        "edge": {"scoring_method": "deterministic_v1", "model_status": "not_trained"},
        "summary": {},
        "evidence": [],
        "data_quality": {"coverage": "none"},
        "next_checks": [],
    }


REQUIRED_MEMBERS = (
    "package/LICENSE",
    "package/README.md",
    "package/catalyst_edge_mcp/data/reviewed_registries.json",
)


def _write_sdist(path, *extra_names, symlink=None):
    with tarfile.open(path, "w:gz") as archive:
        for name in (*REQUIRED_MEMBERS, *extra_names):
            info = tarfile.TarInfo(name)
            info.size = 0
            archive.addfile(info, io.BytesIO())
        if symlink is not None:
            info = tarfile.TarInfo(symlink)
            info.type = tarfile.SYMTYPE
            info.linkname = "package/README.md"
            archive.addfile(info)


def test_release_verifier_accepts_typed_no_data_response():
    payload = _validate_no_data(_Result())
    assert payload["edge"]["model_status"] == "not_trained"


def test_release_verifier_rejects_secret_configuration(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"CATALYST_EDGE_API_KEY": "not-allowed"}))
    with pytest.raises(ValueError, match="secret_like"):
        _load_config(path)


@pytest.mark.parametrize(
    "content",
    (
        "not-json",
        "[]",
        '{"CATALYST_EDGE_PORT": 8000}',
        '{"CATALYST_EDGE_api_key": "not-allowed"}',
    ),
)
def test_release_verifier_rejects_malformed_or_secret_like_configuration(tmp_path, content):
    path = tmp_path / "config.json"
    path.write_text(content)
    with pytest.raises(ValueError):
        _load_config(path)


def test_release_verifier_checks_sdist_inventory(tmp_path):
    path = tmp_path / "package.tar.gz"
    _write_sdist(path)

    inventory = _inspect_sdist(path)
    assert inventory["member_count"] == 3


@pytest.mark.parametrize("name", ("package/../escape", "/absolute"))
def test_release_verifier_rejects_unsafe_sdist_member(tmp_path, name):
    path = tmp_path / "package.tar.gz"
    _write_sdist(path, name)
    with pytest.raises(ValueError, match="unsafe sdist members"):
        _inspect_sdist(path)


def test_release_verifier_rejects_sdist_symlink(tmp_path):
    path = tmp_path / "package.tar.gz"
    _write_sdist(path, symlink="package/link")
    with pytest.raises(ValueError, match="unsafe sdist members"):
        _inspect_sdist(path)


@pytest.mark.parametrize(
    "name",
    (
        ".env",
        ".env.local",
        "state.sqlite",
        "state.sqlite3-wal",
        "state.sqlite3-shm",
        "__pycache__/module.pyc",
        ".pytest_cache/state",
        "credentials.json",
        "secret.txt",
    ),
)
def test_release_verifier_rejects_prohibited_sdist_member(tmp_path, name):
    path = tmp_path / "package.tar.gz"
    _write_sdist(path, f"package/{name}")
    with pytest.raises(ValueError, match="prohibited"):
        _inspect_sdist(path)


@pytest.mark.parametrize(
    "result",
    (
        SimpleNamespace(isError=True, structuredContent=None),
        SimpleNamespace(isError=False, structuredContent=None),
        SimpleNamespace(isError=False, structuredContent={"result": []}),
        SimpleNamespace(
            isError=False,
            structuredContent={**_Result.structuredContent, "edge": []},
        ),
        SimpleNamespace(
            isError=False,
            structuredContent={
                **_Result.structuredContent,
                "data_quality": {"coverage": "partial"},
            },
        ),
        SimpleNamespace(
            isError=False,
            structuredContent={**_Result.structuredContent, "evidence": {}},
        ),
    ),
)
def test_release_verifier_rejects_non_structured_or_non_no_data_response(result):
    with pytest.raises(ValueError):
        _validate_no_data(result)


def test_release_verifier_rejects_missing_entrypoint(monkeypatch):
    payload = {"version": "0.1.1", "entrypoints": ["catalyst-edge-mcp"]}
    monkeypatch.setattr("scripts.verify_release._run", lambda command: json.dumps(payload))
    with pytest.raises(ValueError, match="missing entry points"):
        _entrypoints(Path("/unused/python"))


def test_release_verifier_rejects_missing_tool():
    with pytest.raises(ValueError, match="tool discovery differs"):
        _validate_tools(["catalyst_edge_score"])


def test_release_verifier_rejects_artifact_version_mismatch():
    with pytest.raises(ValueError, match="wheel/sdist version mismatch"):
        _validate_versions("0.1.1", "0.1.0")
