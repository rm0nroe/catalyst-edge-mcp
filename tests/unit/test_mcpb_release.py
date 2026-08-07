import json
import shutil
import struct
import subprocess
import zipfile

import pytest

from scripts.normalize_mcpb import FIXED_ZIP_TIMESTAMP, normalize
from scripts.sign_mcpb import (
    EOCD_COMMENT_LENGTH_OFFSET,
    EOCD_MAGIC,
    SIGNATURE_HEADER,
    _verify_signature,
    sign_bundle,
)
from scripts.verify_mcpb import _prohibited, _validate_bundle, _validate_source
from scripts.verify_release import _prohibited_sdist_path


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


def test_release_rejects_notes():
    assert _prohibited_sdist_path("notes/internal-plan.md")


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


def test_mcpb_signature_is_exact_cms_and_valid_zip_comment(tmp_path):
    assert shutil.which("openssl") is not None
    bundle = tmp_path / "unsigned.mcpb"
    cert = tmp_path / "cert.pem"
    key = tmp_path / "key.pem"
    signed = tmp_path / "signed.mcpb"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("manifest.json", json.dumps({"version": "0.1.1"}))
    normalize(bundle)
    subprocess.run(
        (
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-sha256",
            "-days",
            "1",
            "-subj",
            "/CN=Catalyst Edge MCPB test",
            "-addext",
            "extendedKeyUsage=codeSigning",
            "-keyout",
            str(key),
            "-out",
            str(cert),
        ),
        check=True,
        capture_output=True,
    )

    result = sign_bundle(bundle, signed, cert, key, [])

    content = signed.read_bytes()
    eocd_offset = content.rfind(EOCD_MAGIC)
    comment_length = struct.unpack_from(
        "<H", content, eocd_offset + EOCD_COMMENT_LENGTH_OFFSET
    )[0]
    with zipfile.ZipFile(signed) as archive:
        assert comment_length == len(archive.comment)
        assert archive.comment.startswith(b"MCPB_SIG_V1")
        assert archive.comment.endswith(b"MCPB_SIG_END")
        assert archive.testzip() is None
    assert result["cms_verified"] is True
    assert result["strict_zip_comment_verified"] is True

    block = content[-comment_length:]
    signature_length = struct.unpack_from("<I", block, len(SIGNATURE_HEADER))[0]
    signature_start = len(SIGNATURE_HEADER) + 4
    signature = block[signature_start : signature_start + signature_length]
    tampered = bytearray(content[:-comment_length])
    tampered[0] ^= 1
    with pytest.raises(ValueError, match="CMS Verification failure"):
        _verify_signature(bytes(tampered), signature)
