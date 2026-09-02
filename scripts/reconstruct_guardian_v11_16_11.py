#!/usr/bin/env python3
from pathlib import Path
import base64
import hashlib
import sys

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "production" / "guardian" / "_source_archive" / "v11_16_11"
TARGET = ROOT / "production" / "guardian" / "Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5"
EXPECTED_SHA256 = "d30ff21378331f972bea947a4c6c826b6f4a2547e58878947551199b9d01c495"

parts = sorted(ARCHIVE.glob("Guardian_v11_16_11.b64.part*"))
if not parts:
    raise SystemExit("No source archive parts found")

encoded = "".join(p.read_text(encoding="ascii").strip() for p in parts)
raw = base64.b64decode(encoded, validate=True)
sha = hashlib.sha256(raw).hexdigest()
if sha != EXPECTED_SHA256:
    raise SystemExit(f"SHA256 mismatch: got {sha}, expected {EXPECTED_SHA256}")

TARGET.write_bytes(raw)
print(f"Reconstructed {TARGET.relative_to(ROOT)} ({len(raw)} bytes), SHA256={sha}")
