#!/usr/bin/env python3
from __future__ import annotations

"""Infrastructure-only wrapper for frozen R5 pre-OOS economic robustness v1_00.

Scientific logic remains entirely in r5_pre_oos_economic_robustness_v1_00.
The sole change is bounded retry/backoff around atomic JSON replacement, because
this Windows workstation has already produced transient PermissionError/WinError 5
on os.replace during long autonomous jobs.
"""

import json
import os
import time
from pathlib import Path

import r5_pre_oos_economic_robustness_v1_00 as base


def atomic_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    delays = (0.05, 0.10, 0.20, 0.20, 0.20)
    last = None
    for attempt in range(len(delays) + 1):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:
            last = exc
            if attempt >= len(delays):
                raise PermissionError(f'atomic replace failed after {attempt + 1} attempts: {path}') from exc
            time.sleep(delays[attempt])
    raise last  # pragma: no cover


base.atomic_json = atomic_json

# Re-export frozen scientific functions/constants for deterministic equivalence tests.
PROTECTED = base.PROTECTED
EXPECTED_R5_SHA256 = base.EXPECTED_R5_SHA256
EXPECTED_AUDIT_SHA256 = base.EXPECTED_AUDIT_SHA256
EXPECTED = base.EXPECTED
PROFILES = base.PROFILES
PERIODS = base.PERIODS
cost = base.cost
replay = base.replay
in_period = base.in_period
stats = base.stats
decide = base.decide


def main() -> int:
    return base.main()


if __name__ == '__main__':
    raise SystemExit(main())
