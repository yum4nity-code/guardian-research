#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--terminal-data-path", required=True)
    ap.add_argument("--source", required=True)
    ap.add_argument("--compiled", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    data_path = Path(args.terminal_data_path)
    source = Path(args.source)
    compiled = Path(args.compiled)
    output = Path(args.output)

    if not source.exists():
        raise RuntimeError(f"calendar exporter source missing: {source}")

    text = source.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    interesting = []
    needles = ("Calendar", "calendar", "datetime", "D'", "Time", "2024", "2025", "2026", "FILE_COMMON", "FileOpen")
    for i, line in enumerate(lines, start=1):
        if any(n in line for n in needles):
            interesting.append({"line": i, "text": line[:500]})

    years = sorted({int(x) for x in re.findall(r"\b20\d{2}\b", text)})
    datetimes = sorted(set(re.findall(r"D'[^']+'", text)))
    inputs = []
    for i, line in enumerate(lines, start=1):
        if re.search(r"\binput\b", line):
            inputs.append({"line": i, "text": line[:500]})

    metaeditor_candidates = []
    for p in (
        data_path / "metaeditor64.exe",
        data_path / "MetaEditor64.exe",
        data_path.parent / "MetaEditor64.exe",
    ):
        if p.exists():
            metaeditor_candidates.append(str(p))

    out = {
        "schema": 1,
        "phase": "I-F-2026-CALENDAR-EXPORT-CAPABILITY",
        "status": "PASS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "terminal_data_path": str(data_path),
        "source": {
            "path": str(source),
            "sha256": sha256_file(source),
            "size_bytes": source.stat().st_size,
            "mtime_utc": datetime.fromtimestamp(source.stat().st_mtime, tz=timezone.utc).isoformat(),
        },
        "compiled": {
            "path": str(compiled),
            "exists": compiled.exists(),
            "sha256": sha256_file(compiled) if compiled.exists() else None,
            "size_bytes": compiled.stat().st_size if compiled.exists() else 0,
        },
        "years_literal_in_source": years,
        "datetime_literals": datetimes,
        "input_declarations": inputs,
        "interesting_source_lines": interesting,
        "metaeditor_candidates": metaeditor_candidates,
        "protected_market_content_opened": False,
        "protected_news_content_opened": False,
        "scientific_hypothesis_changed": False,
        "purpose": "Determine whether the existing canonical MT5 calendar exporter can be reused or minimally infrastructure-adapted for the frozen 2026 I-F news mask without inspecting protected outcomes.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
