#!/usr/bin/env python3
"""Print Guardian canonical source identity (UTF-8 text normalized to LF)."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def normalized_sha256(path: Path) -> str:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    path = Path(args.path)
    print(f"SOURCE_IDENTITY_SHA256 {normalized_sha256(path)} {path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
