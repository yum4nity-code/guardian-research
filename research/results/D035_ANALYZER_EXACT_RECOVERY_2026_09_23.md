# D035 analyzer provenance recovery — 2026-09-23

Status: EXACT HISTORICAL ARTIFACT RECOVERED / NO SCIENTIFIC RULE CHANGE

The D035-C1 fresh 2026-H1 runner initially stopped before any market-data access because the repository path
`research/analysis/D035_Binance_Deleveraging_LeadLag_v1_01.py`
contained only a continuity marker, while the original full analyzer had been delivered as a ChatGPT artifact on 2026-09-05.

The original user-owned artifact was recovered:
- pack: `D035_Binance_FundedNext_LeadLag_PATCH_v1_02.zip`
- contained analyzer: `D035_Binance_Deleveraging_LeadLag_v1_01.py`
- recovered source SHA-256: `35e7579b25abebcdd32829168598f58cea4c835c30b0e02d9cdee882e4327168`
- Python compile: PASS during recovery
- v1.00 historical source SHA-256 independently matched the recorded value:
  `fa22fa6a7fe735436b381ef2ec7a58f7aed8e71d526e2b679073a6981dfad133`

For lossless repository preservation the exact v1.01 source is stored gzip+base64 at:
`research/analysis/D035_Binance_Deleveraging_LeadLag_v1_01.py.gz.b64`.

The C1 PowerShell runner now:
1. decodes the archived source;
2. verifies the v1.01 SHA-256 exactly;
3. syntax-compiles it;
4. only then checks the authorized BTCUSD/XLMUSD CFD exports and proceeds.

The initial failed C1 invocation did not open or compute the 2026-H1 result.

Also corrected the user-facing exporter instruction back to the frozen historical D035 protocol:
MT5 Strategy Tester M1 / **1 minute OHLC**, not Every tick.

No D035 threshold, event rule, horizon, direction, target or temporal window changed.
