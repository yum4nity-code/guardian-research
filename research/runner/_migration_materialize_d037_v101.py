#!/usr/bin/env python3
"""ONE-SHOT MIGRATION TOOL: materialize D037 v1.01 as a complete repository source.

This script exists only to convert the already-defined historical builder patch
into a committed immutable .mq5 artifact. It must be removed after the generated
source is committed and verified. It is NOT part of the Guardian Research Runner.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "research/strategies/d037/D037_Williams_M15_v1_00.mq5"
DST = ROOT / "research/strategies/d037/D037_Williams_M15_v1_01.mq5"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 occurrence, got {count}")
    return text.replace(old, new)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    raw = SRC.read_text(encoding="utf-8")

    raw = replace_once(raw, '#property version "1.00"', '#property version "1.01"', "property version")
    raw = replace_once(
        raw,
        'string SOURCE_NAME="D037_Williams_M15_v1_00.mq5";',
        'string SOURCE_NAME="D037_Williams_M15_v1_01.mq5";',
        "source name",
    )
    raw = replace_once(raw, 'string SOURCE_VERSION="1.00";', 'string SOURCE_VERSION="1.01";', "source version")
    raw = raw.replace("D037 V100", "D037 V101")
    raw = raw.replace("D037_V100_", "D037_V101_")

    old = '''      if(CopyRates(_Symbol,PERIOD_M15,0,2,r)>=1)
      {
         MqlRates last=r[0];
         if(last.time!=g_last_processed_bar)
         {
            ProcessClosedBar(last);
            g_last_processed_bar=last.time;
         }
         if(g_fatal_status=="" && g_in_trade)
            WriteTrade(last.time,ClosePx(g_long,last),"TEST_END");
      }
'''
    new = '''      if(CopyRates(_Symbol,PERIOD_M15,0,3,r)>=2)
      {
         // Only the last CLOSED M15 bar is eligible here. r[0] is the current/forming bar.
         MqlRates last_closed=r[1];
         if(last_closed.time!=g_last_processed_bar)
         {
            ProcessClosedBar(last_closed);
            g_last_processed_bar=last_closed.time;
         }
         if(g_fatal_status=="" && g_in_trade)
            WriteTrade(last_closed.time,ClosePx(g_long,last_closed),"TEST_END");
      }
'''
    raw = replace_once(raw, old, new, "OnDeinit closed-bar patch")

    forbidden = {
        "old source name": "D037_Williams_M15_v1_00.mq5",
        "old CSV prefix": "D037_V100_",
        "unsafe OnDeinit forming bar": "MqlRates last=r[0];",
    }
    for label, needle in forbidden.items():
        if needle in raw:
            raise SystemExit(f"{label} remains after migration: {needle}")

    required = [
        '#property version "1.01"',
        'string SOURCE_NAME="D037_Williams_M15_v1_01.mq5";',
        'string SOURCE_VERSION="1.01";',
        "MqlRates last_closed=r[1];",
        "D037_V101_",
        "D037 V101",
    ]
    for needle in required:
        if needle not in raw:
            raise SystemExit(f"required v1.01 marker missing: {needle}")

    DST.write_text(raw, encoding="utf-8", newline="\n")
    print(f"MATERIALIZED {DST.relative_to(ROOT)}")
    print(f"SHA256 {sha256(DST)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
