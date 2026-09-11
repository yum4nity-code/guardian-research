# R5 post-result cold audit preregistration — 2026-09-11

## Purpose

R5 causal next-open r2 produced a terminal PASS with 96 gross-return survivors. This result is not accepted automatically. This audit is reject-only and exists to test the semantic and provenance concerns frozen in `handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md` before any downstream economic screen or protected-OOS discussion.

## Frozen evidence under audit

- R5 job: `STRATEGY-FACTORY-R5-CAUSAL-NEXT-OPEN` revision 2.
- R5 source commit: `ca84ba7a9a8c4b306564d23db654d6e9204ff5e2`.
- Published R5 result SHA256: `81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e`.
- R5 terminal count: 96 survivors.
- No protected 2026 data may be opened by this audit.

## Canonical Phase I-B inputs

Only these four already-established 2024/2025 Phase I-B files are admissible:

- `xauusd_m1_2024_2025_raw.csv` — 710300 rows — SHA256 `f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445`
- `xauusd_m1_2024_2025_news_clean.csv` — 703387 rows — SHA256 `b116c61d0be7d73c455f4a4f897efdf0bf77a2b88594ed4b93ebee0d707570ee`
- `xauusd_m5_2024_2025_raw.csv` — 142549 rows — SHA256 `ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66`
- `xauusd_m5_2024_2025_news_clean.csv` — 140664 rows — SHA256 `972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503`

Any hash, row-count, path-family, or protected-date mismatch is an audit FAIL.

## Execution-semantics audit

For every frozen R5 survivor, reconstruct the original signal mask from the source dataset and compare the frozen source-row return convention with a raw-M1 execution-reference replay.

Frozen R5 convention:
- signal known after source bar `t` closes;
- entry = next available source-row open;
- exit = source-row open at `t+h+1`;
- return normalized by ATR at signal bar.

Audit replay convention:
- signal availability = source timestamp + one source timeframe;
- entry = first canonical raw-M1 open at or after signal availability;
- exit = first canonical raw-M1 open at or after the timestamp of the frozen source-row exit target;
- same direction and same ATR denominator as frozen R5;
- signal, entry and exit must stay within the same calendar year, 2024 or 2025.

This specifically quantifies whether news-clean row removal or source-timeframe gaps cause R5's `next row` proxy to differ from the first executable raw-M1 reference.

## Reject-only gates

For each survivor, recompute on the raw-M1 execution replay:

- 2024 selected-vs-session-complement edge and fast Welch p-value;
- 2025 full-year edge;
- 2025 four-quarter edge signs;
- 2025 HAC/Newey-West p-value using the same lag rule `max(48, 2*h)`.

The audit does **not** retune thresholds, features, horizons, direction, session gates, or quantiles.

A survivor is flagged as materially changed if any of the following holds:

1. it no longer satisfies the original non-BH numerical gates under raw-M1 replay: 2024 edge > 0.02 ATR and fast p < 0.01; 2025 edge > 0.015 ATR; all four 2025 quarters positive; HAC p < 0.05;
2. absolute 2024 or 2025 edge drift between frozen source-row and raw-M1 replay exceeds 0.005 ATR;
3. more than 1% of otherwise-evaluable selected observations have a different gross return reference.

The 0.005 ATR / 1% thresholds are diagnostic materiality limits, not optimization parameters.

## Interpretation

- `PASS_INTERPRETABLE`: canonical provenance is exact and no survivor is materially changed. R5 may proceed to a separately preregistered economic/reject-only robustness screen; this still does not authorize protected 2026.
- `FAIL_SEMANTIC_DRIFT`: at least one frozen survivor is materially changed by executable raw-M1 semantics. R5 r2 must not be promoted. The next justified action is a new preregistered R5 scientific revision that uses the raw-M1 execution reference inside discovery and confirmation from the outset so the entire multiple-testing family is recomputed correctly.
- `FAIL_PROVENANCE`: input/result provenance does not match the frozen evidence. Stop and repair infrastructure only; do not reinterpret science.

Because BH-FDR depends on the entire 2024 discovery family, this audit may not 'repair' a materially changed R5 PASS by re-evaluating only the 96 survivors. If semantic drift is material, a full new frozen revision is required.

## Protected data

The audit is restricted to canonical Phase I-B 2024/2025 files. It must reject any input containing a timestamp on or after `2026-01-01T00:00:00Z`. No protected 2026 file may be enumerated, opened, hashed, or inspected.
