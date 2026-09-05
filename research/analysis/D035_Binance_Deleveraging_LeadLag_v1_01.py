#!/usr/bin/env python3
"""Repository continuity marker for the D035 v1.01 analyzer patch.

The user-facing full analyzer is distributed in the D035 v1.02 patch pack.
This repository path was accidentally created as a placeholder during the live
repair session; do not execute it as the analyzer. The exact source diff that
turns v1.00 into v1.01 is stored beside it as:

    D035_Binance_Deleveraging_LeadLag_v1_00_to_v1_01.patch

Scientific note: v1.01 changes only pandas datetime representation before the
OI/kline merge_asof (ms/us -> ns). No strategy rule, threshold, horizon, gate,
cooldown, target selection, or holdout boundary changes.
"""

raise SystemExit(
    "D035 repository continuity marker only. Apply the adjacent v1.00->v1.01 patch "
    "or use the user-facing D035 v1.02 patch pack; do not execute this marker."
)
