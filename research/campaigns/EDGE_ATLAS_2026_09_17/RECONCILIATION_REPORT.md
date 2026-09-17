# Edge Atlas read-only reconciliation report

Observed from inspection commit `e7352b28e89a2f681d3c4b547b12f90fbf4cb67b`.  
Verdict: `READY_FOR_READ_ONLY_CHEAP_FAIL`.

No service was stopped, restarted, signalled or modified. No backtest, worker, MiMo task, metatester, cheap-fail or Edge Atlas strategy was launched. Production, existing histories/results and queues were not changed.

## Declared state versus machine truth

- `manifests/CODEX_SESSION_CHECKPOINT.json` is obsolete. It dates from September 1, names D017 generalization as primary and records MT5/MiMo PIDs that no longer exist.
- `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` is obsolete and suspect. It points to another checkout, combines multiple later campaigns with stale PIDs and declares quarantined 2026-covered activity. It is not an admission authority.
- `CURRENT_QUEUE.json` is obsolete as an execution view. It declares Phenomenon Discovery Phase B `READY`, but no matching process exists. It contains no Edge Atlas campaign.
- `CURRENT_PROJECT_HANDOFF.md` correctly closes R33/R34 and identifies generation 114 as the empty effective autonomous queue. It predates the present data admission.
- Edge Atlas `CHECKPOINT.json` correctly forbids R33/R34/R35, FundedNext XAU and 2026, but its statement that the PC is inaccessible is superseded.

The real machine shows R33, R34 and R35 inactive; no metatester, MiMo, strategy-factory or Edge Atlas worker exists. The Guardian orchestrator is alive but only polling an empty generation-114 queue. Active work is limited to live/infrastructure services: the FundedNext terminal and MetaEditor, multivenue collector, PropFirmGuard, CSV/live synchronizers and orchestrator polling. The D023-named generic CSV synchronizer and an unattributed PowerShell session may be legacy processes; they were preserved. The live collector writes 2026-dated archives, but it is not a research worker and its output is permanently excluded from Edge Atlas.

`git diff origin/main...HEAD -- production/guardian` is empty. Production was not modified. No Edge Atlas job exists in either `CURRENT_QUEUE.json` or the effective autonomous queue.

## Read-only admission gate

The canonical gate is `ADMITTED_DATA_MANIFEST.json`.

### Dukascopy XAUUSD

Admitted source: the indexed public Dukascopy `BID_candles_min_1.bi5` caches, not the R30 annual CSVs. They contain 5,518 unique weekday payloads from 2004-11-08 through 2025-12-31, 80,219,635 bytes, with no missing indexed file, size mismatch, duplicate date, weekend path or 2026 path. The index SHA-256 is `d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566` and contains a SHA-256 for every payload.

To respect the bounded-inspection rule, live verification sampled the first, middle and last payload of every year: 66 files, 95,040 M1 records, zero hash/layout failure, duplicate second, nonmonotonic pair or within-day gap above 60 seconds. Consumers must verify each selected payload hash before use, aggregate only completed prior M1 bars, and reject any timestamp outside the indexed UTC day or at/after 2026.

### Binance BTCUSDT/ETHUSDT spot M5

The admitted slice is exactly 2024-01-01 00:00 UTC through 2025-12-31 23:55 UTC. Each asset has 210,528 rows, exactly the full two-year five-minute grid, with zero duplicate, nonmonotonic row, off-grid timestamp, non-300-second delta or zero-volume row. File hashes are BTC `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8` and ETH `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`.

The larger 2017–2025 files contain 33 older discontinuities and 241 off-grid rows during February 2018; those rows are outside the admitted crypto chronology. The gate must filter the frozen 2024–2025 interval first and then assert the exact grid before feature computation. These are spot OHLCV files only: no open interest, funding, perpetual or derivative field is available or authorized.

## Permanent campaign exclusions

- Bybit price/OI and derivative/funding files whose names and coverage extend to 2026.
- The actively written external-intelligence archive with 2026-dated filenames.
- All FundedNext XAU data.
- R30/artificially continuous Dukascopy annual CSVs and any XAU derivative lacking the admitted payload-index provenance.

## Shortlist revision

EA06, EA07 and EA15 are removed because they require unavailable admissible OI. No threshold or rule was optimized and no result was examined. The three catalogued additions are EA09, EA16 and EA20, mapped before execution to admitted Binance spot M5. The resulting ten are EA01, EA02, EA03, EA04, EA08, EA09, EA11, EA12, EA16 and EA20.

## Next safe action

Implement a small fail-closed loader/preflight for the admitted manifest, add synthetic causality/aggregation tests, and obtain an independent cold review. Only after that review may one bounded read-only cheap-fail be proposed. This report does not authorize executing it.
