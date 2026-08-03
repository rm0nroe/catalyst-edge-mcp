import json
import zipfile

import pytest

from scripts.normalize_mcpb import FIXED_ZIP_TIMESTAMP, normalize
from scripts.verify_mcpb import _prohibited, _validate_bundle, _validate_source


def test_mcpb_source_contract():
    source = _validate_source(__import__("pathlib").Path(__file__).parents[2])
    assert source["tools"] == ["catalyst_edge_score", "catalyst_edge_claim_sources"]


@pytest.mark.parametrize(
    "name",
    (
        ".env",
        ".env.local",
        "dist/output.mcpb",
        "state.sqlite3",
        "state.sqlite3-wal",
        "tests/fixture.json",
        "credentials.json",
    ),
)
def test_mcpb_rejects_prohibited_members(name):
    assert _prohibited(name)


def test_mcpb_rejects_unexpected_root(tmp_path):
    bundle = tmp_path / "bad.mcpb"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"version": "0.1.1"}))
        archive.writestr("customer-data.json", "{}")
    with pytest.raises(ValueError, match="inventory differs"):
        _validate_bundle(bundle)


def test_mcpb_normalization_is_reproducible(tmp_path):
    hashes = []
    for index in range(2):
        bundle = tmp_path / f"bundle-{index}.mcpb"
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("z.txt", "last")
            archive.writestr("a.txt", "first")
        normalize(bundle)
        hashes.append(__import__("hashlib").sha256(bundle.read_bytes()).hexdigest())
        with zipfile.ZipFile(bundle) as archive:
            assert [item.filename for item in archive.infolist()] == ["a.txt", "z.txt"]
            assert {item.date_time for item in archive.infolist()} == {FIXED_ZIP_TIMESTAMP}
    assert hashes[0] == hashes[1]
