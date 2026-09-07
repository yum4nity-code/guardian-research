#!/usr/bin/env python3
"""Run only the missing D049/D045 Market Transport V1 development leg."""
from __future__ import annotations

import json
import sys

import market_transport_lab_v1 as lab


def main() -> int:
    try:
        result = lab.run_parent("D045", "development")
    except Exception as exc:
        print(f"D049 RECOVERY ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
