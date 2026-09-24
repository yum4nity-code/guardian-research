# EA01 XAU FTMO transport v1_00 — INVALID RUN

Date: 2026-09-24
Artifact: GUARDIAN_EA01_XAU_FTMO_TRANSPORT_20260924-053553.zip
Status: **INVALID_INFRA / DO NOT INTERPRET EDGE OUTCOME**

## What executed correctly

The runner completed and produced:
- EA01_ALIGNMENT_SCAN.csv
- EA01_FTMO_EXECUTION_LEDGER.csv
- EA01_FTMO_TRANSPORT_RESULT.json
- RUN.log

Canonical source gates passed:
- source_signals = 944
- deterministic non-overlap N = 654
- protected 2026 accessed = false
- retuning = false
- FTMO identity guard passed
- XAUUSD contract size read as 100

The pandas timezone warning in RUN.log is non-fatal and did not terminate the run.

## Fatal scientific / implementation error

v1_00 selected **one constant clock offset (+3h) for the entire 2023-2025 sample**.

FTMO MetaTrader platform time is GMT+2 with DST; FTMO explicitly changes platform time to GMT+3 during the DST period and back to GMT+2 afterward. Therefore a single +3h mapping across January-February and November-December is wrong.

The artifact itself exposes the bug.

With the chosen +3h mapping, median absolute source-vs-FTMO entry-price difference by calendar month is approximately:
- Jan: 10.18 bp
- Feb: 12.35 bp
- Mar: 0.56 bp
- Apr: 0.42 bp
- May: 0.47 bp
- Jun: 0.45 bp
- Jul: 0.41 bp
- Aug: 0.42 bp
- Sep: 0.40 bp
- Oct: 0.40 bp
- Nov: 8.15 bp
- Dec: 13.59 bp

Return correlation is near 1 in most correctly aligned summer months but collapses in winter months. This is a clock-alignment failure, not market evidence.

Official FTMO evidence independently confirms the platform offset changes. Examples:
- 2025-03-09: GMT+2 -> GMT+3
- 2025-11-03: GMT+3 -> GMT+2

## Consequence

The reported v1_00 classification:
**ECONOMICALLY_REJECTED_FTMO**

is **VOID / NOT A VALID SCIENTIFIC VERDICT**.

Do not use:
- mean net -0.070338R
- PF 0.90955
- yearly means
- bootstrap
- trim diagnostics

as evidence for or against EA01, because part of the sample was evaluated one hour away from the frozen signal times.

EA01-XR-RSI-LONG-V1 therefore returns to:
**UNRESOLVED_FTMO_EXECUTION_TRANSPORT**

No candidate rescue is implied. The candidate simply has not yet received a valid FTMO transport test.

## Root cause

The preregistration and v1_00 analyzer incorrectly froze:
- integer offset scan -4h..+4h;
- one globally selected offset.

The design should instead have frozen the documented FTMO DST calendar or an equivalent causal timestamp mapping before execution.

## Decision

- Mark v1_00 INVALID.
- Do not patch or reinterpret its PnL.
- Do not call this an EA01 failure.
- Protected 2026 remains untouched.
