# R34 independent artifact audit — midnight concentration
Date: 2026-09-16 (Europe/Paris)
STATUT: ACTION_REQUISE — source-data causality unresolved; no alpha promotion.

## Pinned evidence
- main: 68e9435c37c1340588e32e96ca392e3d56de262e
- results: b101e6c1a8b15cf40b7ccef960eeef54c5519caf
- run: phenomenon-discovery/r34-signal-execution-feed-factorial/runs/20260916T205131Z_r34-signal-execution-feed-factorial/
- Reproducible read-only audit: research/autonomous/audit_r34_published_artifacts_v1_00.py
- Machine-readable measurements: research/autonomous/R34_PUBLISHED_ARTIFACT_AUDIT_2026_09_16.json

## Verified
All nine published artifacts reconcile with status.json source SHA256 and byte counts after explicit LF-to-CRLF reconstruction. Git blobs are LF; the status records Windows CRLF bytes. This is not exact byte equality of the Git blobs to the source digests. No artifact was changed.

Ledger row counts, raw-signal accounting and E1/STRESS net and PF recompute correctly for all eight year/cell combinations. Signal thresholds satisfy the exported frozen formula. Exact/±10-minute absence is independently reproduced.

| Year | FN signals / midnight | Duka signals / midnight | Duka executed / overlap ignored | FN executed / overlap ignored |
|---|---:|---:|---:|---:|
| 2024 | 95 / 95 | 563 / 0 | 163 / 400 | 95 / 0 |
| 2025 | 107 / 107 | 732 / 0 | 168 / 564 | 107 / 0 |

All 202 FN signals are at 00:00 server-coordinate, one per distinct date. Duka signals are at 01:00–07:55. The nearest FN-to-Duka gap is at least 60 minutes; medians are 255 and 210 minutes. Thus 563−95 is NOT a count of discarded paired events. Neither population is an established subset of the other.

FN-signal/FN-execution entry delays from signal-bar timestamp are 60–61 minutes in 2024 and 60–62 in 2025, median 60. FN-signal/Duka-execution delays have median 5 and maximum 180 minutes in both years. The first-available-open replay changes timing as well as prices when execution feed changes. R34 therefore does not isolate a pure execution-price effect.

Median high-minus-close at signal: FN 4.77 / 6.93 versus Duka 0.23 / 0.46. This is descriptive only, not a formal rejection threshold.

## Code evidence and hypothesis
At the pinned main commit, phase_ib_hcc_recovery_v1_01.py:
- decode_record accepts plausible OHLC + minute-divisible timestamp and labels every accepted record M1;
- parse_hcc scans byte offsets for adjacent 60-byte records, accepts timestamp steps from 0 through 14 days, and retains the first record for each timestamp;
- it does not establish each recovered block's true timeframe from structural metadata.
v1.02 reuses this parser and changes only the M5 aggregation precheck.
R34 load_fn reuses load_market: sorts and deduplicates timestamps, but does not prove M1 granularity or when an OHLC record became available.

Hypothesis: a higher-timeframe/day-summary block could be mislabeled as M1 at midnight, contaminating derived M5 and possibly placing future daily OHLC into the signal. This is a demonstrated admission weakness in the code, NOT a demonstrated description of the actual HCC bytes. Source records and independent native export must establish or refute it. Session gaps, clock labeling and true broker bars remain alternatives.

If a same-day final close enters a midnight signal, cross-feed replay cannot remove the leakage: it carries the contaminated signal timestamp into either execution feed. Consequently the large FN PF is not evidence against this hypothesis.

## Impact / decision
Preserve R34's numerical SIGNAL_FEED_DOMINANT classification as an immutable diagnostic of these inputs. Suspend causal-filter/real-edge interpretation and all promotion relying on the suspect FN signal source until the availability/record-type audit passes. No new claim that every earlier result is invalid: inventory dependent studies after source diagnosis.

## ACTION_CODEX: frozen source-construction diagnostic
This plan is frozen AFTER observing R34 artifacts but BEFORE inspecting source HCC records for this diagnosis. It is exploratory infrastructure diagnosis, not independent alpha validation.

1. Inspect actual local process/output state before any action. Preserve queue generation 114 (zero jobs), all R33/R34 files, their hashes and all source HCC/CSV bytes. Use a fresh separate diagnostic directory; never overwrite or rerun R33/R34.
2. Admit only exact pinned 2024/2025 FN M1/M5 inputs from R34 input_provenance and exact 2024.hcc / 2025.hcc from the existing Phase I-B source manifest. Validate its source hashes before reading. No broad file glob, downloader, MT5 historical synchronization or protected 2026 access. If evidence cannot be accessed without protected data, stop BLOCKED.
3. Export source M1/M5 records for every one of the 202 FN signal timestamps, plus previous/next records. Report complete per-year hour histograms, cadence, duplicates/conflicting records, gaps and OHLC range distributions. Retain unfiltered controls, not only breakout days.
4. Trace midnight records to original HCC byte offsets, block starts, neighboring records, duplicate alternatives and accepted/rejected records. Establish the block timeframe from available structure or an independent native 2024/2025 export. Do not select an alternative parser just because its PnL improves.
5. Independently compare each suspect midnight record with same-day and previous-day OHLC aggregated ONLY from separately verified intraday records. Compare O/H/L/C separately, exact values plus source precision; do not choose a fit tolerance from profitability. Same-source M5-vs-M1 agreement alone is insufficient because both may inherit the same bad record.
6. Reconcile server clock, session closure/reopen and true available_at of the contributing OHLC. Determine whether all high/low/close information existed before the recorded execution. Export affirmative provenance or UNRESOLVED for each case.
7. Required outputs: input hashes, source trace CSV, per-year coverage/cadence JSON, OHLC comparison CSV, availability verdict, dependent-study inventory and report. Outcomes: CONFIRMED_RECORD_TYPE_CONTAMINATION, CONFIRMED_OTHER_SOURCE_OR_CLOCK_DEFECT, SOURCE_VALIDATED_FOR_INSPECTED_SCOPE, or UNRESOLVED. Do not equate 'no exact daily match' with source validation.
8. Synthetic tests and cold review before any new diagnostic engine/source parsing. Any correction/reconstruction gets a separate version and separate output only after evidence; no repair or retuning of frozen R6B-347 in this step. No fresh PnL/backtest in this source audit.

## Limits and current execution
This session accessed GitHub and a Linux analysis workspace, not the Windows PC. The HCC/full OHLC sources were not available here. Artifact audit completed; root cause and source diagnostic remain pending local execution. No worker, orchestrator, market replay, protected data or production action was launched. The audit script was run on published outputs, then reread; its counts and accounting were cross-checked against direct CSV observations. No independent-agent review is claimed.
Human active time: NOT QUANTIFIED.
