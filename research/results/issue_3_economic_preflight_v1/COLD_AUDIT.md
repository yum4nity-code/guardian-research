# Issue #3 — Economic/execution preflight v1

Date: 2026-09-11. Verdict: **BLOCKED BEFORE ECONOMIC IMPLEMENTATION / NO QUEUE / NO RUN**.

Request: https://github.com/yum4nity-code/guardian-research/issues/3 (open, no comments when read).
Repository inspected: `3ad27cdbe09b19ca3cfae2d617c042a5a0ce6497`. Effective autonomous queue generation: 34 (base 16, append 34). Existing orchestrator PID 7580 was WAITING; no factory/economic engine was active. This audit did not change that queue, start an engine, open protected market files or compute candidate PnL.

## Mandatory cold-audit answers

**If this job PASSes, does it answer the question needed to advance toward a tradable EA? NO at present.** Executable quotes, spread timing/units, the applicable FundedNext account model and commission-side convention are not sufficiently established. A positive number calculated with those unresolved inputs would not establish economic feasibility. No executable validator or frozen runnable policy has been created.

**If a candidate passes this test, have we demonstrated that it merits a heavier trading backtest without 2026? NOT YET.** The second launch audit cannot pass before a complete execution/cost policy, implementation, required tests and smoke test exist. A corrected future feasibility filter can answer this narrower question, but cannot establish independent statistical validation or authorize protected OOS.

## 1. Scientific coherence

- All 500 published R4 survivors remain the reference population; 500 distinct immutable signal signatures verified. The 32 frozen representatives are all members of those 500, used only as optional structural annotations. No other candidate is discarded.
- Source R4 has no candidate_id field. Future IDs must be anchored to published source row plus canonical signal signature, preserving dataset, feature, operator, quantile, cutpoint, direction, horizon and session exactly. `R4F-*` identifies the consolidation CSV only, not the whole population.
- This is a published top-500 cap, not all raw passing rules. The uncapped survivor count is not recorded. Existing selection is not repeated or altered.
- Four datasets are all XAUUSD from one FundedNext server, M1/M5, raw/news-clean. This population does not demonstrate Forex/crypto/multi-asset breadth. Raw and clean variants are not independent markets.
- Same-session complement is a statistical control only. Never subtract its return from traded PnL.
- No re-fitting, rerunning discovery, economic calibration, SL/TP/trailing search or leverage rescue is authorized by this preflight.

## 2. Statistical coherence

- 2025 is reused, so economic filtering is not fresh OOS. R4's 2024 discovery and 2025 HAC/BH/half-year/neighbor selection must remain provenance, not a renewed significance claim.
- Code computes forward returns on the combined 2024/2025 frame before year masks. Some end-2024 outcomes can extend into 2025. Thus strict separation of all discovery outcomes is not established by the year mask alone. This audit has not quantified or rerun those outcomes.
- HAC addresses statistical dependence, not simultaneous executable trades. It does not repair missing quote timing or portfolio position constraints.
- The HAC implementation uses `y*(g/p-(1-g)/(1-p))` centered by its overall mean. This differs from the centered group-mean influence expression `g/p*(y-mu_selected)-(1-g)/(1-p)*(y-mu_complement)` when group membership is estimated/random. Its p-values should not be assumed independently revalidated by this economic gate. No statistical implementation was modified.
- No economic ranking or survivor threshold was selected after inspecting new PnL; none has been calculated. Required decision protocol remains explicitly unfrozen pending costs and execution evidence.

## 3. Data provenance and execution coherence

### Source artifacts

R4 completed PASS at 2026-09-11 03:47:04 UTC, engine commit `63b825bad510150225154c8f539d14e025d8c8d9`, 250000 trials, seed 260912, 90669 unique rules tested, 12097 discoveries, six scanned/four eligible datasets.

Published artifact: `phenomenon-discovery/strategy-factory-r4-conditional-edge/runs/20260911T034654Z_strategy-factory-r4-conditional-edge/strategy_factory_result.json` on `backtest-results`.

- Published Git blob SHA256: `af7c94500ab99eed3c984dbab5dfac3dc3180fae86b958a3753378803f62f8c4`.
- Local file SHA256: `7cb29f3251fa0c1f0d37f719286ba4e51a2446aa0d04d0a7cc3bc53e663b3a48`.
- Entire JSON objects equal; bytes equal after CRLF-to-LF normalization. This is not candidate drift. Both byte hashes must be recorded, never silently substituted.
- Canonical JSON SHA256: `0ac1e917508e29276c0c13b2abf8cbb576f078feab5e084120e02a09dfa505cf` (sorted keys, compact separators, UTF-8, ensure_ascii=false).
- Consolidation r1/r2 receipts PASS. R2 local frozen JSON SHA256: `37bb6f2d52ef12e7a17a2fd38d94f53ebd94843c3f47500ef36b4c7c76c57e9b`; published canonical candidate-set hash recorded by the freeze manifest: `f92da89a61f8eb7ad4bc8f8c8e7a6a7efd0bbc32cd83a29d192e870a4261db64`.

### Verified pre-2026 inputs

All four current hashes match the Phase I-B provenance summary before metadata parsing. They derive from read-only HCC recovery, FundedNext-Server 2, `D:\MT5_FundedNext`, HCC years 2024 and 2025; M5 is synthesized from M1. Exact CSV hashes and coverage are in `data_provenance_audit.json`.

| Dataset | Rows | Reference candidates | Last server timestamp |
|---|---:|---:|---|
| M1 raw | 710300 | 59 | 2025-12-31 23:59 |
| M1 news-clean | 703387 | 66 | 2025-12-31 23:59 |
| M5 raw | 142549 | 176 | 2025-12-31 23:55 |
| M5 news-clean | 140664 | 199 | 2025-12-31 23:55 |

All start at server 2024-01-01 00:00, contain only 2024/2025 epochs, and have no duplicate/non-increasing timestamps. These are server-clock encodings: labeling them UTC in pandas does not independently prove a real UTC conversion. Broker timezone/DST and rollover conventions require verification.

Columns: symbol, timeframe, server_time, server_epoch, open, high, low, close, tick_volume, spread, real_volume. **No Bid, Ask or executable tick timestamps.** M1 spread ranges 0..230 points (446 raw zero rows); M5 ranges 0..100 (154 raw zero rows). Zero is not automatically free execution. Unit and recording-time evidence is required before cost conversion.

M5 uses the last constituent M1 spread and the first available M1 open. The integrity report explicitly records 45 M5 boundaries without an exact M1 open. Using that spread at the timestamped M5 open would be unjustified and potentially forward-looking. News-clean removes rows; its next retained bar is not necessarily the next tradable quote, and `h` retained bars are not always `h * timeframe` elapsed minutes. Market/session gaps occur even in raw data. None of these inputs proves a historical executable Ask.

### Inventory and protection failure

R4 `inventory()` recursively traverses broad roots, without sorting or an explicit file allowlist. `max_files=120` counts detected OHLC files, not every scanned CSV; it was not reached (six accepted). `max_rows=900000` selects the tail BEFORE sorting/date filtering; no truncation affected the four inputs, whose row counts are all below that cap.

Historical rejected-file log does not exist. `detect()` catches all exceptions, `inventory()` suppresses stat errors, and the market loader silently skips all exceptions/insufficient year coverage. The complete historical rejected-file list and exceptions cannot be reconstructed reliably from the saved six-file inventory. Re-running broad discovery now would also violate the current no-2026 instruction; it was not done.

The saved inventory explicitly includes `xauusd_m1_2026_jan_aug.csv` and `xauusd_m5_2026_jan_aug.csv`. R4 detection reads CSV rows, and `load_market()` reads the entire file before filtering `<2026`. These two files therefore could not be certified never-read by the hardcoded result flag. They cannot pass the required 2024+2025 coverage gate; insufficient coverage is the code-based expected rejection reason, but historical exceptions were not recorded. No conclusion that their prices affected selection is asserted. **Absence of 2026 market-file reading is not established for R4; the current audit opened neither file.**

Future validator must use only explicit pre-2026 hash-pinned paths, reject forbidden paths BEFORE opening, and never reuse recursive R4 inventory or read-then-filter as its protection. No trade may need a protected successor quote; exclude missing/out-of-range exits before price access. Also exclude 2024 trades crossing the evaluation-period boundary. Record every exclusion rather than replacing missing prices.

### Costs: mandatory STOP

Official pages were checked on 2026-09-11. These are cost documentation, not protected market history.

- [FundedNext general rules](https://fundednext.com/general-rules/cfds/symbols-and-conditions): commission is described as per side. Metals: 0.0016% for Stellar 1-Step/2-Step/Instant, 0.0018% for Lite.
- [FundedNext Stellar Instant fee article](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account): 0.0016% at the opening price, charged only at opening; explicitly no closing commission, effective 12 January 2026. This directly conflicts with the general per-side statement for Instant.
- [FundedNext general commission article](https://help.fundednext.com/en/articles/10701368-what-are-the-commission-charges-for-stellar-challenges-and-fundednext-accounts): metals formula uses lots × contract size × opening price × 0.0016%, effective 12 January 2026. It does not reconcile the closing-side treatment across models.
- The relevant FundedNext account product/phase is not positively identified by the server name. Do not silently choose Instant, Lite or Stellar 2-Step, and do not choose the cheaper interpretation. Required evidence: exact account model and authoritative reconciliation of rate, entry/exit basis and charging sides. Impact: potentially doubled commission and different net-feasibility conclusions.
- [FTMO symbols](https://ftmo.com/en/symbols/) initially failed in text browsing; direct HTTP and its public [specification endpoint](https://ftmo.com/wp-json/ftmo/symbols) worked. XAU/USD contract size 100, USD profit currency, digits 2, displayed commission 0.0014 percent. The [25 September 2025 announcement](https://ftmo.com/au/blog/trading-updates/trading-update-25-sep-2025/) states metals 0.0007% per side effective 29 September 2025, consistent with the displayed aggregate rate. This does not establish the target account's tick size/value or FundedNext model.

Do not turn digits=2 into an unverified tick-size assumption. Do not use current quote-derived commission dollars as a fixed historical charge. Commission on a verified per-side notional convention uses each actual side's execution price separately. Spread and slippage remain separate. No numerical spread fallback/slippage assumptions or three runnable cost profiles were invented. Rollover/weekend exposure requires verified swap treatment or a preregistered exclusion; zero swap cannot be silently assumed.

## 4. Infrastructure/software coherence

- R4 result and consolidation PASS receipts are execution outcomes, not cost/execution validation. The orchestrator's `protected_2026_untouched=false` is derived from global `human_approved_2026=true`, while engine output hardcodes true. Neither is a per-file access audit.
- Consolidation `atomic_json()` still has bare `os.replace`. Do not copy it. New writes must retry only PermissionError, have a bounded delay/attempt budget and propagate all other errors, with explicit infrastructure ERROR.
- Add time-based heartbeats to every long stage, including feature loading, candidate simulation, aggregation and final output. Report actual candidate/trade progress and elapsed time. Distinguish scientific FAIL from data BLOCKED and infrastructure ERROR; exit-code zero alone must not imply scientific PASS.
- No new queue entry or automatic protected-OOS dependency was added. Existing unrelated queue state remains unchanged. A future immutable job needs source-hash validation, R4 receipt dependency, distinct output/progress/receipt paths and process duplicate checks before activation.

## Safe continuation and launch checklist

1. Obtain exact FundedNext model and authoritative commission-side clarification; verify target symbol contract/tick/point units for both profiles.
2. Establish a defensible pre-2026 execution feed. Keep R4 signals on their original datasets, but do not equate clean/synthetic bar opens with observed executable Bid/Ask. Freeze timing/horizon and gaps/rollover handling before new performance.
3. Freeze deterministic per-candidate position handling, sizing, cost profiles, eliminators and ranking. The planned individual feasibility test must not silently merge all 500 into one portfolio; portfolio allocation is a different question.
4. Implement only after those blockers are resolved. Required tests: no protected file/row access, lookahead, determinism, entry/exit, end-2025, overlap, simultaneous/contradictory events, spread, commission sides, separate slippage, notional/contract units, long/short PnL, drawdown, hashes, simulated PermissionError, invalid/rejected files, complete 500 population, secondary-only 32, no automatic OOS.
5. Synthetic smoke first; then preregistered small data smoke without calibration. All gates must pass before queue activation. None of these economic tests/smokes is claimed PASS here.

No safe execution ETA can be assigned until costs/feed are resolved. No request was sent to broker support and no issue comment was posted.
