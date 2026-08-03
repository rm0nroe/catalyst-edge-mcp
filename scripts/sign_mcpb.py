"""Create a strict-ZIP-compatible detached CMS signature for an MCPB bundle."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

SIGNATURE_HEADER = b"MCPB_SIG_V1"
SIGNATURE_FOOTER = b"MCPB_SIG_END"
EOCD_MAGIC = b"PK\x05\x06"
EOCD_MIN_SIZE = 22
EOCD_COMMENT_LENGTH_OFFSET = 20
MAX_ZIP_COMMENT = 65_535


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run(*args: str) -> bytes:
    result = subprocess.run(args, check=False, capture_output=True)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"command failed ({args[0]}): {detail}")
    return result.stdout


def _find_unsigned_eocd(bundle: bytes) -> int:
    offset = bundle.rfind(EOCD_MAGIC)
    if offset < 0 or offset + EOCD_MIN_SIZE != len(bundle):
        raise ValueError("input must be an unsigned ZIP with no trailing bytes")
    if struct.unpack_from("<H", bundle, offset + EOCD_COMMENT_LENGTH_OFFSET)[0] != 0:
        raise ValueError("input ZIP must not already contain a comment or MCPB signature")
    return offset


def _with_comment_length(bundle: bytes, eocd_offset: int, length: int) -> bytes:
    if not 0 < length <= MAX_ZIP_COMMENT:
        raise ValueError(f"signature block exceeds ZIP comment limit: {length}")
    patched = bytearray(bundle)
    struct.pack_into("<H", patched, eocd_offset + EOCD_COMMENT_LENGTH_OFFSET, length)
    return bytes(patched)


def _signature_block(signature: bytes) -> bytes:
    return b"".join(
        (
            SIGNATURE_HEADER,
            struct.pack("<I", len(signature)),
            signature,
            SIGNATURE_FOOTER,
        )
    )


def _cms_sign(content: bytes, cert: Path, key: Path, intermediates: list[Path]) -> bytes:
    with tempfile.TemporaryDirectory(prefix="catalyst-edge-mcpb-sign-") as directory:
        root = Path(directory)
        content_path = root / "content.mcpb"
        signature_path = root / "signature.der"
        content_path.write_bytes(content)
        command = [
            "openssl",
            "cms",
            "-sign",
            "-binary",
            "-md",
            "sha256",
            "-in",
            str(content_path),
            "-signer",
            str(cert),
            "-inkey",
            str(key),
            "-outform",
            "DER",
            "-out",
            str(signature_path),
            "-nosmimecap",
        ]
        if intermediates:
            chain_path = root / "intermediates.pem"
            chain_path.write_bytes(b"\n".join(path.read_bytes() for path in intermediates))
            command.extend(("-certfile", str(chain_path)))
        _run(*command)
        return signature_path.read_bytes()


def _verify_signature(content: bytes, signature: bytes) -> None:
    with tempfile.TemporaryDirectory(prefix="catalyst-edge-mcpb-verify-") as directory:
        root = Path(directory)
        content_path = root / "content.mcpb"
        signature_path = root / "signature.der"
        output_path = root / "verified.mcpb"
        content_path.write_bytes(content)
        signature_path.write_bytes(signature)
        _run(
            "openssl",
            "cms",
            "-verify",
            "-binary",
            "-inform",
            "DER",
            "-in",
            str(signature_path),
            "-content",
            str(content_path),
            "-noverify",
            "-out",
            str(output_path),
        )
        if output_path.read_bytes() != content:
            raise ValueError("CMS verification did not recover the exact signed bytes")


def sign_bundle(
    bundle: Path,
    output: Path,
    cert: Path,
    key: Path,
    intermediates: list[Path],
) -> dict[str, object]:
    if shutil.which("openssl") is None:
        raise ValueError("openssl is required for MCPB signing")
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")
    for path in (bundle, cert, key, *intermediates):
        if not path.is_file():
            raise ValueError(f"required file does not exist: {path}")

    original = bundle.read_bytes()
    eocd_offset = _find_unsigned_eocd(original)
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        if archive.testzip() is not None:
            raise ValueError("input ZIP contains a corrupt member")

    # Bootstrap the block size, then sign bytes whose EOCD already declares that size.
    signature = _cms_sign(original, cert, key, intermediates)
    block_length = len(_signature_block(signature))
    for _ in range(4):
        signed_content = _with_comment_length(original, eocd_offset, block_length)
        signature = _cms_sign(signed_content, cert, key, intermediates)
        next_length = len(_signature_block(signature))
        if next_length == block_length:
            break
        block_length = next_length
    else:
        raise ValueError("CMS signature block length did not stabilize")

    block = _signature_block(signature)
    final = signed_content + block
    _verify_signature(signed_content, signature)
    with zipfile.ZipFile(io.BytesIO(final)) as archive:
        if archive.comment != block or archive.testzip() is not None:
            raise ValueError("signed MCPB is not a valid ZIP comment")

    cert_fingerprint = _run(
        "openssl", "x509", "-in", str(cert), "-noout", "-fingerprint", "-sha256"
    ).decode("utf-8", errors="strict").strip()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        handle.write(final)
    return {
        "unsigned_path": str(bundle.resolve()),
        "unsigned_sha256": _sha256(original),
        "signed_path": str(output.resolve()),
        "signed_sha256": _sha256(final),
        "signature_block_bytes": len(block),
        "certificate_fingerprint": cert_fingerprint,
        "cms_verified": True,
        "strict_zip_comment_verified": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cert", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--intermediate", type=Path, action="append", default=[])
    args = parser.parse_args()
    try:
        print(
            json.dumps(
                sign_bundle(
                    args.bundle.resolve(),
                    args.output.resolve(),
                    args.cert.resolve(),
                    args.key.resolve(),
                    [path.resolve() for path in args.intermediate],
                ),
                indent=2,
            )
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"MCPB signing failed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
