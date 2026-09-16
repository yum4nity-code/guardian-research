# R34 v1.00 — independent cold review

## Scope

Independent static review and synthetic-test execution only. No FundedNext or Dukascopy market dataset was read or executed.

Reviewed:

- `R34_SIGNAL_EXECUTION_FEED_FACTORIAL_PREREGISTRATION_2026_09_16.md`
- `r34_signal_execution_feed_factorial_v1_00.py`
- `test_r34_signal_execution_feed_factorial_v1_00.py`

## First-pass findings and disposition

1. **HIGH — corrected:** Dukascopy server-year construction originally omitted the tail of prior UTC year. It now loads UTC `y-1` and `y`, converts with the R33 clock, sorts/deduplicates, and selects server year `y`. A boundary sentinel test covers the Dec-31 to Jan-1 carry.
2. **HIGH — corrected:** outputs originally could be partially published. All artifacts are now written to a sibling staging directory and the completed directory is renamed into place; existing output/staging paths fail closed.
3. **MEDIUM — corrected:** the R30 manifest is pinned by SHA256 and all effective FN/Dukascopy input hashes and paths are recorded in result provenance.
4. **MEDIUM — corrected:** the existing statistics engine can return `PF=null` when no gross loss exists. The preregistered classification now uses bounded PF and explicitly maps that limiting case to `1.0`; a synthetic regression test covers it.
5. **MEDIUM — corrected:** signal-pair output now contains explicit `FN_ONLY` and `DUKA_ONLY` rows with the available feed diagnostics.

## Second-pass verdict

No blocking issue remains. The frozen R6B-347 definition, 2024–2025-only scope, 2026 guard, factorial axis separation, deterministic exact/±5/±10 matching, diagnostic deltas, classification, provenance and transactional publication are coherent.

Direct synthetic R34 test: **PASS**. Diff whitespace/error check: **PASS**. Existing R33, R6 and top2 replay regression suites: **PASS**.

Minor residual coverage note: transactional publication and unmatched-row export were checked statically rather than through a synthetic end-to-end invocation of `main`. This does not block the proposed real run, which remains unexecuted.

