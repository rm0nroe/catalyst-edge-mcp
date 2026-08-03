"""Normalize unsigned MCPB ZIP metadata for reproducible artifact hashes."""

from __future__ import annotations

import argparse
import os
import tempfile
import zipfile
from pathlib import Path

FIXED_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def normalize(bundle: Path) -> None:
    with zipfile.ZipFile(bundle) as archive:
        entries = [
            (item.filename, archive.read(item), item.external_attr)
            for item in archive.infolist()
            if not item.is_dir()
        ]
    entries.sort(key=lambda item: item[0])

    with tempfile.NamedTemporaryFile(dir=bundle.parent, suffix=".mcpb", delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for name, data, external_attr in entries:
                item = zipfile.ZipInfo(name, FIXED_ZIP_TIMESTAMP)
                item.create_system = 3
                item.external_attr = external_attr
                item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, data, compresslevel=9)
        os.replace(temporary, bundle)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    normalize(args.bundle.resolve())


if __name__ == "__main__":
    main()
