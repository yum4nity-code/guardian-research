# Edge Atlas local data admission report

Observed: 2026-09-17 09:58:32 Europe/London  
Branch commit inspected: `e3eaa0d6e29e2e5411bfa14aa2ac832760c3120a`  
Verdict: `BLOCKED_PROCESS_ACTIVE`

No backtest, campaign, worker, MiMo task, cheap-fail or EA01–EA15 strategy was launched. No production file, queue entry, historical result or existing artifact was changed. R33/R34/R35 were not opened or rerun.

## Repository and control plane

The operational checkout is `D:\MT5_Backtests\guardian-autonomous-main`; it was clean and synchronized with `origin/main` at `55ae12e7365cbe501e3271308a6b54776e614f16`. The requested branch existed remotely and matched locally at `e3eaa0d6e29e2e5411bfa14aa2ac832760c3120a`; it is four commits ahead of and zero behind main. Inspection artifacts were isolated in `D:\MT5_Backtests\guardian-edge-atlas-inspection` because the running orchestrator periodically resets/synchronizes the operational checkout.

`CURRENT_QUEUE.json` is stale: it still declares Phenomenon Discovery Phase B READY. The repository checkpoint and `D:\MT5_Backtests\Research\SESSION_CHECKPOINT.json` are stale and their recorded PIDs do not exist. The local checkpoint also references another repository and declared 2026-covered work; it was marked suspect and not used as authority. The real process table and filesystem state take precedence.

## Process gate

The machine is not idle. FundedNext MT5 and MetaEditor are open; no `metatester64.exe` exists. The Guardian orchestrator is polling GitHub with an effective empty autonomous queue, and no research worker child was observed. A multivenue collector is actively writing 2026-dated external-intelligence files. PropFirmGuard, a backtest CSV synchronizer, a live-status synchronizer and one unattributed PowerShell session are also active. Nothing was stopped, restarted or signalled. Exact PID, command, duration, role, log and status evidence is in `PROCESS_STATE.json`.

## Admission decisions

### ADMISSIBLE — raw Dukascopy XAUUSD payload union

The separate original and fastfill `.bi5` caches contain 5,518 indexed daily payloads from 2004-11-08 through 2025-12-31, 80,219,635 bytes, zero duplicate indexed dates and no 2026 path. The immutable master index SHA-256 is `d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566`. This source is admissible only at raw-payload/index level and only through the frozen audited Dukascopy decoder.

### SUSPECT — derived Dukascopy annual M1/M5 CSVs

The six 2023–2025 annual CSVs are UTC and hash-stable, but bounded samples show a fully regular calendar grid with constant-price rows over closures, including New Year. Their apparent absence of gaps is caused by forward filling. They must not be treated as raw causal bars until a missing-session mask and aggregation policy are independently audited. Individual hashes are recorded in `LOCAL_MACHINE_INVENTORY.json`.

### ADMISSIBLE WITH SCOPE LIMIT — Binance BTCUSDT/ETHUSDT spot M5

The two merged price files cover 2017-08-17 through 2025-12-31 UTC. SHA-256: BTC `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`; ETH `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`. Their 202 raw monthly archives contain no 2026 path. Small samples show five-minute cadence and explicit zero-volume bars. They are admissible for price-only work, not as Bybit or OI evidence.

### BLOQUÉ — Bybit price/OI and derivative context

The only located Bybit BTC/ETH M5 price+OI and derivative/funding files explicitly include `2026-01-01` in every filename and manifest path. Under the mission rule they were not opened. They cannot support EA06, EA07, EA08 or EA15. A physically separate, hash-pinned 2024–2025 extract is required.

### BLOQUÉ — live external crypto archive

The archive under `D:\MT5_Backtests\Research\ExternalIntelligence` is actively written and every located JSONL filename encodes 2026. Its contents were not opened and it is excluded from this campaign.

### BLOQUÉ — FundedNext XAU

FundedNext XAU 2024–2025 is explicitly forbidden by this mission and remains causally quarantined. It was not inventoried as proof.

## 2026 detection

`OUI`. Detection is confined to names/declared coverage and the explicitly requested checkpoint comparison. Suspect data files were not read further. No 2026 market row was admitted or used.

## Next safe action

Do not execute Edge Atlas while the active services and stale checkpoints remain unreconciled. First document ownership and intended coexistence of the orchestrator, synchronizers and collector without stopping or restarting them. Then build a read-only admission gate over the raw pre-2026 Dukascopy payload index and price-only Binance archives. Crypto hypotheses requiring OI remain blocked until a separate pre-2026 Bybit/OI extract is created and independently hashed.
