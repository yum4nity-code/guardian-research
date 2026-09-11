# Second cold audit — actual validator v1_00 / final protocol v2

Date: 2026-09-11. Review by the implementing agent, not an independent reviewer.
Scope: actual Python source, pure feature module, fixed policy, tests and final
smoke. Code identity is pinned in PRE_REGISTRATION.json; synthetic test evidence
in TEST_REPORT.json and reduced real-data functional evidence in SMOKE_REPORT.json.

## Mandatory question and verdict

“Si un candidat PASS ce screen, avons-nous suffisamment démontré que son edge
mérite un backtest réaliste plus coûteux, sans prétendre qu’il est déjà rentable
ou validé ?”

**OUI — PASS for this limited feasibility decision.** This is survival of specified
friction hurdles on reused 2024/2025 observations. It is not new statistical OOS,
real historical fills, account profitability, execution compliance or a combined
portfolio. The frozen gates are implemented without additional elimination rules.

## Actual code/dataflow findings

- All 500 source signatures are ingested, checked unique and mapped to stable IDs.
  The 32 signatures only set a boolean annotation; real smoke ingestion confirms
  500 source records before selecting the eight preregistered test IDs.
- Pure R4 feature/rule function ASTs equal the historical definitions. Altering
  future prices leaves earlier features/signals unchanged. Original session gates
  remain; no 08–20, weekday or same-day admission filter in the full replay.
- Availability is bar timestamp plus timeframe. First-available raw M1 entry has
  no extra minute. Chronological source closes decrement a horizon counter; no
  future clean source timestamp is inspected to choose entry or precompute exit.
  Pending/open state suppresses overlap until the actual scheduled exit. End-of-
  history unresolved positions suppress following signals and are excluded,
  never forcibly priced or resolved from another file.
- Year/half crossings continue through the replay, excluded only from the crossed
  evaluation slices. Annual totals may include trades absent from either half;
  that is intentional and not an aggregation bug. Midnight/weekend permitted.
- Long/short modeled-price identities independently reconcile to gross less the
  three cost components. Full spread is halved per side. Commission uses each
  modeled-side notional. Fixed one-ounce sizing, no FundedNext computation.
- Exact gates: annual counts 100/100, 2025 half counts 40/40; E1 positive in four
  required periods; stress positive annually only; stress 2025 ex-best positive.
  No PF/DD/win-rate cutoff or count/ranking limit. Fail reasons are explicit.
- Per-trade accounting, causal/overlap/boundary invariants run before output.
  Malformed/hash/path errors abort with a separate failure artifact; no skipped
  dataset, except-continue, silent truncation or fallback source exists.
- Atomic JSON catches only PermissionError from replace, with bounded attempts
  and an explicit chained terminal error. Heartbeat is a separate five-second
  writer; failures propagate. Existing run output/progress are rejected.

## No-read-2026 contract

Reviewed every data input: four literal market paths and hashes compiled in code,
the identical explicit manifest, fixed R4/frozen JSON pins, and seven fixed support
paths. Unexpected support-manifest paths are rejected before reading, so the
support mechanism cannot introduce an arbitrary market input. No scan/glob/roots,
export, MT5, network, publisher or subprocess path exists in the validator.

The native Windows reader checks membership before metadata/open, rejects reparse
points, denies write/delete sharing, verifies final handle path before reading,
then checks SHA256 before parsing those same bytes. Pandas receives BytesIO only.
Installed audit-fence tests exercise actual Python/pandas/NumPy readers against
synthetic forbidden names without opening any protected file. Final smoke records
exactly four verified CSV inputs and zero denied accesses. Unknown/malformed input
cannot yield scientific PASS. This does not assert an OS sandbox against hostile
native libraries: installed runtime is trusted and loaded before the fence. No
runtime path in the audited validator delegates arbitrary native data reads.

## Corrections before final smoke (no methodology calibration)

1. Initial sandbox synthetic runs could not use Windows temporary files; the same
   tests passed with normal Windows permissions. These were environment errors.
2. Smoke attempt 01 stopped when the fence denied a lazy NumPy dependency import.
   Dependencies are now loaded before the fence; an actual installed-fence test
   exercises parsing/features without late reads. Failed attempt is retained.
3. Smoke attempt 02 functioned, but code review rejected direct future horizon
   indexing as insufficiently literal compliance with causal bar counting. It was
   replaced by chronological counter replay, retested, and smoke 03 passed. No
   threshold, cost, signal, session, horizon or population was calibrated.
4. Smoke 04 reverified the exact commit-bound bytes after removing one trailing
   blank line in the pure feature module. This formatting-only change altered
   its byte hash, so the seal and reduced smoke evidence were refreshed.

Final smoke: eight predefined IDs, first five available weekdays of each half for
signal admission, full original source for warmup/horizon. 1,148 ledger rows checked;
no economic ranking/selection inspected. All eight outputs are SMOKE_NOT_FOR_SELECTION.
Complete final test/smoke reports, rather than prior attempts, determine readiness.

## Remaining limitations, not hidden overrides

Raw opens are reference proxies, not verified Bid/Ask. Spreads/slippage are frozen
assumptions. Financing has no supplied model and is unmodeled; net is explicitly
spread/slippage/commission net, with overnight/weekend exposure reported. These
limitations require the more expensive realistic backtest, not a profit claim.
Observed adverse marks do not reconstruct missing quotes, within-bar favorable
high-water marks or exact tick floating drawdown; realized drawdown is reported
separately. News-mask causality is the owner's accepted provenance premise; the
screen does not reread calendar events or retroactively certify their publication.

Historical R4 may have opened two protected files; their contribution is not
established. The four screen datasets are certified pre-2026. Preserve R4 and
consolidation. Separate recertification remains mandatory before protected OOS.
FundedNext ambiguity stays open/disabled. No automatic OOS dependency is permitted.

Disposition: eligible for the owner's already-authorized commit/push and one
immutable queue job, only with the final passing reports and unchanged code seal.
