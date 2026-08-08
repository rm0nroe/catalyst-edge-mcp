"""Build or byte-replay a provider-neutral dataset bundle."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from catalyst_edge_mcp.replay.contracts import build_dataset, canonical_json, normalize_spec


def write_bundle(spec_path: Path, root: Path) -> dict[str, object]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    version, payload, manifest = build_dataset(spec)
    bundle = root / version
    bundle.mkdir(parents=True, exist_ok=False)
    _atomic_write(bundle / "spec.json", canonical_json(normalize_spec(spec)))
    _atomic_write(bundle / "dataset.jsonl", payload)
    _atomic_write(bundle / "manifest.json", canonical_json(manifest))
    return manifest


def replay_bundle(version: str, root: Path) -> dict[str, object]:
    bundle = root / version
    spec = json.loads((bundle / "spec.json").read_text(encoding="utf-8"))
    expected = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    actual_version, payload, actual = build_dataset(spec)
    if actual_version != version or actual != expected:
        raise ValueError("replay manifest does not match the frozen bundle")
    if payload != (bundle / "dataset.jsonl").read_bytes():
        raise ValueError("replay bytes do not match the frozen bundle")
    return actual


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-version")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--root", type=Path, default=Path("replay-data"))
    args = parser.parse_args()
    if args.replay:
        if not args.dataset_version or args.spec:
            parser.error("--replay requires --dataset-version and forbids --spec")
        result = replay_bundle(args.dataset_version, args.root)
    else:
        if not args.spec or args.dataset_version:
            parser.error("a new build requires --spec and forbids --dataset-version")
        result = write_bundle(args.spec, args.root)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
