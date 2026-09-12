# Guardian Research — R4/R5 continuity handoff — 2026-09-11

## Purpose

This file is the canonical continuity snapshot for the current Guardian autonomous-research thread. It exists so a new ChatGPT conversation can resume without relying on the old conversation transcript.

## Operator intent and non-negotiable rules

- Final objective: produce multiple genuinely viable EAs, not just statistically interesting phenomena.
- Never deploy to live / real money automatically.
- Protected 2026 OOS must remain sealed unless an explicit preregistered protocol authorizes opening it.
- Scientific FAIL is not infrastructure FAIL. Preserve that distinction in receipts, decisions and reruns.
- Do not restart healthy jobs, do not create duplicate runs, and do not overwrite historical artifacts.
- After infrastructure failure, rerun immutably with the same scientific protocol/seed/trials and only the infrastructure repair revisioned.
- Before any expensive new phase: cold methodology + code audit first, deterministic tests second, micro/canary only if justified, then expensive run only if the preceding gates pass.
- Before launching a phase, explicitly answer: “If this job PASSes, does it actually answer the question required to advance?”
- No Codex for this workflow unless the operator explicitly changes that decision. Preferred control plane is GitHub + the autonomous orchestrator.
- Never claim a job is running merely because it is queued. Require observable evidence: local health/progress/process or published orchestrator evidence.
- Technical style: concise/direct. At first use of an acronym, expand it and give a very short explanation.

## Runtime / repository

- GitHub repo: `yum4nity-code/guardian-research`
- Local deploy checkout: `D:\MT5_Backtests\guardian-autonomous-main`
- Autonomous root: `D:\MT5_Backtests\Research\Autonomous`
- Orchestrator: `D:\MT5_Backtests\Research\Autonomous\runtime\guardian_research_orchestrator_v1_00.py`
- Orchestrator PID observed during this thread: 7580. Treat PID as ephemeral; re-check after restart.
- Poll interval: 60 s.
- Results branch: `backtest-results`

## Queue state — IMPORTANT

GitHub `research/autonomous/RESEARCH_QUEUE_APPEND.json` is now **generation 46**.

R5 preflight r2 and R5 r2 are enabled again at the operator's request.

Commits:
- `094d5ecb3ccf57d525632c5c9cafdc61c4639d0d` — temporary pause request, now superseded.
- `b53e7e3e97c0518037732fbbb5945367151766c2` — restore the R5 queue state per operator request.

Nuance: the current R5 r2 child was already running from generation 44, so generation 46 does not restart it. Existing receipts prevent rerunning completed revisions once the orchestrator loops again.

This queue restoration does **not** authorize a new downstream research phase after R5. First inspect the completed R5 result and perform the cold audit described below before adding/enabling any new job.

## R4 history and closure

### R4 discovery

Job:
`STRATEGY-FACTORY-MULTI-ASSET-RANDOM-R4-CONDITIONAL-EDGE`

Frozen design:
- 250,000 trials
- seed 260912
- 2024 discovery
- 2025 confirmation
- thresholds fit on 2024 only
- conditional directional forward-return uplift vs same-session complement
- HAC / Newey-West confirmation
- Benjamini-Hochberg FDR 5%
- 2025 H1/H2 positive
- adjacent-quantile robustness
- 2026 intended sealed
- survivor cap 500

Result: PASS with 500 capped survivors.

Consolidation later reduced these to 32 structural representatives, but **the original 500 remain the scientific reference population**. The other 468 were not scientifically eliminated.

### Economic feasibility screen

Frozen economic screen used the 500 original survivors and first-available raw M1 execution references with FTMO-style E1 and stress cost profiles.

Result: scientific FAIL, 0/500 passed all economic gates.

Key earlier counts:
- R4 selected mean > 0 in 2024: 500/500
- replay gross > 0 in 2024: 200/500
- E1 net > 0 in 2024: 0/500
- replay gross > 0 in 2025: 180/500
- E1 net > 0 in 2025: 4/500

This led to the causal-capture forensic audit rather than another blind search.

## R4 causal-capture forensic audit — decisive result

Canonical protocol / implementation / queue commits:
- `05b02281a1f2374d2fee7731b3df3f2ff823b936` — preregistration
- `9afd2909c3a8aa52388433cf228f3e909c8cac01` — forensic engine
- `a9bfbe0b1046777c7f41b62912cf87595e37a5f0` — deterministic preflight tests
- `a920c03b32c6a685e7d045dea9f377637fcecc6f` — gated queue

Job:
`R4-CAUSAL-CAPTURE-FORENSIC-AUDIT r1`

Receipt:
- PASS
- duration ~480.19 s
- result status `PASS_INTERPRETABLE`

Published result:
`phenomenon-discovery/r4-causal-capture-forensic-audit/runs/20260911T141339Z_r4-causal-capture-forensic-audit/r4_causal_capture_forensic_result.json`

Published summary:
`phenomenon-discovery/r4-causal-capture-forensic-audit/runs/20260911T141339Z_r4-causal-capture-forensic-audit/SUMMARY.md`

### Mapping checks

All passed:
- M5 raw -> M1 raw: 141,729 complete buckets, 820 incomplete, **0 OHLC mismatch**
- M5 clean -> M1 raw: 139,844 complete buckets, 820 incomplete, **0 OHLC mismatch**
- M5 clean subset of M5 raw: **0 missing, 0 OHLC mismatch**

Therefore the R4 collapse is not explained by an M5/M1 OHLC mapping bug.

### Exact B -> C decomposition

Definitions:
- B = source-close to future source-close gross return
- ENTRY_DELTA = signal source close to first executable raw M1 open
- EXIT_DELTA = future source close to executable raw M1 exit open
- C = B + ENTRY_DELTA + EXIT_DELTA

2024:
- B positive: 500/500
- C positive: 252/500
- D after overlap positive: 200/500
- E1 net positive: 0/500
- B aggregate gross: +1,119,753.04
- ENTRY_DELTA: -1,113,639.89
- EXIT_DELTA: -5,688.28
- C next-open no-overlap gross: +424.87
- overlap delta: -9,144.85
- E1 costs: 678,136.81
- E1 net: -686,856.79
- **99.49% of the adverse B->C components came from ENTRY_DELTA**

2025:
- B positive: 500/500
- C positive: 194/500
- D after overlap positive: 180/500
- E1 net positive: 4/500
- B aggregate gross: +2,022,868.84
- ENTRY_DELTA: -2,015,815.65
- EXIT_DELTA: -9,893.05
- C next-open no-overlap gross: -2,839.86
- overlap delta: -36,689.60
- E1 costs: 1,026,529.32
- E1 net: -1,066,058.78
- **99.51% of the adverse B->C components came from ENTRY_DELTA**

Conclusion: R4 mostly captured movement already realized between the signal bar close and the first executable entry reference. The problem is not ATR normalization, not primarily overlap, not primarily exit mapping, and not OHLC mapping.

### News-clean execution anomaly

For overlap-constrained news-clean trades:
- total trades: 793,929
- raw-M1 entry reference absent from M1 clean: 460
- raw-M1 exit reference absent from M1 clean: 442
- any absent: 886
- share: ~0.1116%

This is real but too small to explain the R4 failure.

### Additional descriptive result worth preserving

Immediate post-close selected-vs-complement diagnostic showed selected better for all 500 candidates in both years, while aggregate ENTRY_DELTA was massively adverse. If further causal diagnosis is needed, segment ENTRY_DELTA by elapsed gap / session reopen / weekend / timeframe rather than launching another huge random search.

R4 close-to-close family is closed:
- `9fad343b5fa57dd2515767c239ada5037766a44c` — closure record.

## Interaction factory that was stopped

A 120,000-rule two-state interaction search had been started using the old R4-style close-to-close ATR target. It did not answer the causal execution question.

It was frozen and then its already-running local r2 child had to be manually killed because the orchestrator only refreshes GitHub between jobs.

Historical r2 receipt records FAIL due forced termination. Treat that as infrastructure/operator stop, not scientific evidence.

Do not resurrect that interaction result into the decision chain.

## R5 causal next-open family

Purpose: discover signals whose target is causal by construction rather than source-close to future-close.

Initial commits:
- `e958aa89d64bd72e3db5cc2e46fcfbf0f5c8ac48` — R5 factory
- `0d6e8d4b0bcce88e554e52573103ca64d1b86ff1` — initial synthetic preflight
- `2489c5b88a86e27ee3f2a10ff400ea66dc59c373` — preregistration
- `edb667dfb2fac19f032c61601c3ad440bf20d32f` — original queue

Frozen preregistration:
`research/autonomous/R5_CAUSAL_NEXT_OPEN_PREREGISTRATION_2026_09_11.md`

### R5 scientific design

- signal known only after source bar t closes
- entry proxy: next available source-bar open t+1
- exit proxy: open t+h+1
- return = direction * (exit_open - entry_open) / ATR(t)
- cross-year signal/entry/exit purged
- 2024 discovery
- 2025 confirmation
- trials: 150,000
- seed: 260914
- feature families: ret 1/3/6/12/24/48, range/body/wicks, RSI7/14, SMA distance 5/10/20/50/100, ATR regime, hour, day-of-week, volume z-score where present
- tail quantiles: 5/10/20/30% lower/upper
- horizons: 1/3/6/12/24/48
- directions: long/short
- optional session gate probability 35%, start 0-23, width 2/4/6/8 h

2024 discovery gate:
- conditional selected-vs-session-complement edge > 0.02 ATR
- fast two-sample p < 0.01
- >=100 selected and >=100 baseline observations

2025 confirmation:
- full-year edge > 0.015 ATR
- all four quarters positive
- >=30 selected/baseline each quarter
- HAC lag max(48, 2*h)
- BH-FDR q <= 0.05 across all 2024 discovery candidates
- adjacent same-tail quantile stress must keep > 0.0075 ATR edge

A R5 PASS is only a causal gross-return discovery/confirmation survivor. It is **not** an EA and does not authorize 2026.

### R5 r1 infrastructure failure

Preflight r1 failed before market data:
`ValueError: assignment destination is read-only`

Cause: `causal_return` tried to assign NaN into a read-only NumPy view.

No scientific inference from r1 failure.

### R5 r2 repair

Repair commits:
- `5dad307409e8c0c82d5061f186e9a5066965e364` — writable-array repair wrapper
- `3d27a3800309941a6e1f38a7c83665bd5dba8f7c` — repaired synthetic preflight
- `ca84ba7a9a8c4b306564d23db654d6e9204ff5e2` — queue immutable r2

The repair only changes the return vector to an owned writable array before masking invalid rows.

Preflight r2:
- PASS
- 6 tests
- no market-data access
- receipt finished 2026-09-11 17:08:52 UTC

### CURRENT RUN — R5 r2

Job:
`STRATEGY-FACTORY-R5-CAUSAL-NEXT-OPEN r2`

Started from commit:
`ca84ba7a9a8c4b306564d23db654d6e9204ff5e2`

Last published orchestrator evidence at launch:
- queue generation 44
- status RUNNING
- started around 2026-09-11 17:09 UTC

Local progress file:
`D:\MT5_Backtests\Research\Autonomous\progress\STRATEGY-FACTORY-R5-CAUSAL-NEXT-OPEN-R2.json`

Latest operator-provided progress snapshot at 2026-09-11 19:58:58 UTC:
- completed: **100,000 / 150,000**
- stage: `discovery_2024_causal_next_open`
- datasets: 4
- discovery_candidates: **4,088**

Interpretation:
- 4,088 are discovery candidates, **not confirmed survivors**
- when discovery reaches 150,000/150,000, the same R5 job must still run the 2025 confirmation/HAC/BH-FDR/quarter/neighbor gates
- do **not** shut the PC down merely because discovery reaches 150,000
- wait for progress stage `complete` or a final published receipt/result

Expected local output directory:
`D:\MT5_Backtests\Research\Autonomous\strategy_factory_r5_causal_next_open`

Expected final result:
`strategy_factory_causal_result.json`

Expected final survivors CSV:
`strategy_factory_causal_survivors.csv`

## CRITICAL: R5 result must NOT be accepted automatically

Even if R5 r2 ends PASS with survivors, do not immediately launch another phase and do not call the survivors validated EAs.

A cold audit is mandatory first.

Specific issues to inspect:

1. **Execution-reference semantics**
   - Current `causal_return` uses `df.open.shift(-1)` and `df.open.shift(-(h+1))` inside each source dataset.
   - For news-clean datasets, “next row” can skip removed news bars.
   - This is not identical to the R4 forensic/economic convention of first-available **raw M1** reference after signal availability.
   - Quantify whether this changes candidate selection materially before accepting results.

2. **M5 execution semantics**
   - For M5 source rules, code uses next M5 open rather than explicitly resolving to first raw M1 open after the M5 close.
   - These should normally coincide when the bucket sequence is complete, but the equivalence must be proven on the exact eligible rows, especially around gaps.

3. **Input provenance**
   - R5 inventory recursively scans CSVs under the Phase I-B root and filters by path/name/contents.
   - The forensic/economic screen used exact hash-pinned inputs.
   - Before accepting R5, verify the exact four datasets actually admitted, hashes, row counts, and that no unintended duplicate/alternate dataset participated.

4. **Protected 2026**
   - R5 code rejects loaded rows >=2026 and filename-filters known `2026` / `oos` / `phase_if` paths.
   - Do not rely on a hardcoded `protected_2026_untouched=True` field alone.
   - Verify the actual dataset inventory and provenance before stating 2026 remained untouched.
   - Note: orchestrator receipt metadata may show `protected_2026_untouched:false` because the base queue has `human_approved_2026:true`; this metadata is not sufficient either way.

5. **Multiple testing / confirmation implementation**
   - Check that BH-FDR is applied across the correct family of 2024 discovery candidates entering 2025 confirmation.
   - Verify HAC implementation and quarter masks.
   - Verify adjacent-quantile stress truly uses thresholds fitted only on 2024.

6. **No costs yet**
   - R5 is gross-return discovery/confirmation only.
   - Any survivors still need realistic execution/cost feasibility and reject-only robustness before protected OOS.

If the cold audit finds a scientific-semantic problem, freeze R5 result, repair only through a new preregistered revision, and do not reinterpret the flawed result.

## Resume procedure in a new conversation

1. Read this file first.
2. Read `CURRENT_PROJECT_HANDOFF.md`, but this dated file supersedes older stale top sections on R4/R5 state.
3. Inspect GitHub main queue generation. It should be >=46 with R5 preflight r2 and R5 r2 enabled, unless a later explicit operator instruction changed it.
4. Check local R5 progress:
   `Get-Content "D:\MT5_Backtests\Research\Autonomous\progress\STRATEGY-FACTORY-R5-CAUSAL-NEXT-OPEN-R2.json" -Raw`
5. Check local orchestrator health:
   `Get-Content "D:\MT5_Backtests\Research\Autonomous\orchestrator_health.json" -Raw`
6. Check `backtest-results` for a final R5 r2 receipt/publication.
7. If R5 still runs normally: do not interfere.
8. If R5 is complete: verify final receipt/result and perform the cold audit above **before** enabling any new queue work.
9. If R5 failed: classify scientific vs infrastructure failure before deciding anything.
10. Once current R5 is done, verify the final receipt/result. The operator intends to leave the PC running overnight and shut it down tomorrow; no extra shutdown-time pause is required.

## What not to do on resume

- Do not use Codex.
- Do not launch a new 150k/250k search immediately.
- Do not open protected 2026.
- Do not treat 4,088 discovery candidates as survivors.
- Do not treat a R5 PASS as an EA.
- Do not add or enable any **new downstream research job** before the R5 cold audit, even though the existing R5 r2 queue entries are enabled.
- Do not resurrect the stopped interaction factory.
- Do not overwrite or delete historical failed receipts.

## Immediate next decision point

Wait for R5 r2 completion.

Then:
- final status FAIL -> analyze why, preserving scientific vs infrastructure distinction;
- final status PASS with survivors -> cold-audit semantics/provenance/statistics before any economic screen;
- after a clean audit only -> decide the smallest next reject-only validation step.



## 2026-09-12 resume update — R5 audit accepted, economic gate next

Published R5 post-result cold audit r3 is terminal `PASS_INTERPRETABLE`:
- 96 frozen survivors;
- exact R5 result SHA256 matched;
- all four canonical Phase I-B 2024/2025 hashes matched;
- material semantic changes: 0;
- provenance failures: 0;
- protected 2026 opened: false.

Interpretation: R5 may advance only to a separately preregistered reject-only economic robustness screen on 2024/2025. This is still pre-OOS and does not authorize protected 2026.

The next frozen protocol is:
`research/autonomous/R5_PRE_OOS_ECONOMIC_ROBUSTNESS_PREREGISTRATION_2026_09_12.md`

Question: do any of the 96 frozen R5 survivors remain economically credible under first-available canonical raw-M1 execution references, chronological one-position replay, and the inherited E1/STRESS cost gates?

Generation 50 was prepared for this screen but had not executed before the PC shutdown. Before resume, the code was cold-audited and the known Windows `os.replace` PermissionError failure mode was proactively hardened without changing scientific logic:
- wrapper: `research/autonomous/r5_pre_oos_economic_robustness_v1_01.py`
- deterministic infrastructure test: `research/autonomous/test_r5_pre_oos_economic_robustness_v1_01.py`
- queue generation: **51**
- preflight: `R5-PRE-OOS-ECONOMIC-ROBUSTNESS-PREFLIGHT r2`
- main: `R5-PRE-OOS-ECONOMIC-ROBUSTNESS r2`

Scientific logic remains frozen:
- exact 96 R5 survivors;
- exact R5 and cold-audit hashes;
- exact four Phase I-B hashes;
- first raw-M1 execution reference;
- one position at a time per candidate;
- E1/STRESS inherited costs;
- inherited reject-only trade-count/net/stress/ex-best gates;
- protected 2026 forbidden.

On resume, let the orchestrator fetch generation 51. If local health/progress proves the economic r2 job is running, do not duplicate or restart it.
