#!/usr/bin/env python3
"""EA01 bounded cheap-fail runner. Fail-closed; no 2026 and no production access."""
from __future__ import annotations
import argparse, json

ID = "EDGE-ATLAS-2026-09-17-EA01-CHEAPFAIL-V0"

def admit(manifest):
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    if doc.get("status") not in {"ADMITTED", "READY"}:
        raise RuntimeError("manifest is not admitted")
    files = doc.get("files", [])
    if not files:
        raise RuntimeError("manifest has no files")
    for row in files:
        if "2026" in json.dumps(row, sort_keys=True):
            raise RuntimeError("2026 detected in admitted source")
        if row.get("asset") != "XAUUSD":
            raise RuntimeError("EA01 accepts XAUUSD only")
    return doc

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True, type=__import__("pathlib").Path)
    ap.add_argument("--output", required=True, type=__import__("pathlib").Path)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    admit(args.manifest)
    if not args.execute:
        print(json.dumps({"status":"PREFLIGHT_ONLY", "id":ID}))
        return 0
    raise RuntimeError("No approved Edge Atlas execution adapter is installed")

if __name__ == "__main__":
    raise SystemExit(main())
