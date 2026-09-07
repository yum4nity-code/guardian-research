# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D051 CLOSED UNCONFIRMED / NEXT SCIENCE: MANAGEMENT-AS-ALPHA NULL TEST CANDIDATE**

## Read this first on a new chat

This is the freshest human-readable handoff.

Then read:
1. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
2. `reports/research/D051_NR7_INDEX_CLUSTER_CONFIRMATION_CLOSEOUT_20260907.md`
3. `reports/research/D041_D032_M2_POST2024_MANAGEMENT_VALIDATION_CLOSEOUT_20260907.md`
4. `reports/research/MARKET_TRANSPORT_LAB_V1_CLOSEOUT_20260907.md`
5. `GUARDIAN_MASTER_MANDATE.md`
6. `GUARDIAN_STATE.json`

Important: generated state views may still contain stale active-experiment fields. This handoff plus immutable `backtest-results` evidence are fresher until state is reconciled.

## Canonical operator UX

- Assistant prepares GitHub, preregistration, source identity, runner/state changes and interpretation.
- Give one short PowerShell block whenever local MT5 execution is needed.
- Runner publishes evidence automatically to `backtest-results`.
- User normally replies only **`fini`**.
- On `fini`, retrieve GitHub evidence directly; do not ask the user to paste logs/JSON if transport worked.
- If transport fails but valid local evidence exists, repair publication rather than rerunning MT5.
- Keep MT5 sequential.

## Hard boundaries

- Guardian Core v12.01 is the frozen compile-validated production baseline; do not modify during research unless explicitly asked.
- Do not merge to `main` unless explicitly requested/reviewed.
- Never `git reset --hard` or destructive-clean unrelated work.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are historical/untrusted; never fallback.
- No post-hoc rescue, no retuning after opened results, no relabeling seen data as OOS.

## Market Transport Lab V1 — CLOSED

Frozen 12-market universe: AUDUSD, USDCAD, USDCHF, EURJPY, GBPJPY, AUDJPY, SPX500, NDX100, GER30, US30, XAGUSD, XPTUSD.

- D047 NR7: n903, mean -0.0266508R, PF0.9314, 6/12 positive -> `TRANSPORT_NO_BROAD_PASS`.
- D048 Inside Day: n805, mean -0.0400952R, PF0.8872, 3/12 positive -> `TRANSPORT_NO_BROAD_PASS`.
- D049 Donchian: formal `ENGINEERING_INCOMPLETE` because XPTUSD repeatedly ended `FINAL_INVALID_REFERENCE`; 11 valid-market diagnostic n276, mean -0.0198714R, PF0.9558, total -5.4845R, 5/11 positive, 2025 negative. Operationally closed, no XPTUSD retry justified.
- D050 NR4 comparator: n1567, mean -0.0499294R, PF0.8615, 4/12 positive -> `COMPARATOR_NO_BROAD_PASS`.

D047 discovery only: SPX500+NDX100+GER30+US30 were all positive in 2024-2025, combined n299, +31.66879718R, +0.10591571R/trade. This generated D051.

## D051 NR7 equity-index cluster — CLOSED UNCONFIRMED

Preregistered 2026-H1 confirmation, same unchanged D038/D047 NR7 semantics on SPX500, NDX100, GER30, US30.

Result:
- n61; SPX50014, NDX10010, GER3017, US3020
- mean **-0.0429737R/trade**
- PF **0.878433**
- total **-2.621396R**
- positive symbols **2/4**
- SPX500 -3.37655R
- NDX100 +2.38774R
- GER30 -4.10664R
- US30 +2.47404R
- integrity 0; all Trade Path checks passed
- verdict **D051_UNCONFIRMED_CLOSE**

Authoritative event:
`backtests/d051/live/events/confirmation/d051-confirm-score/20260907T135932Z`

Closeout:
`reports/research/D051_NR7_INDEX_CLUSTER_CONFIRMATION_CLOSEOUT_20260907.md`

The reserved Jul-Aug 2026 holdout remains unopened under the preregistered `LOCKED_UNLESS_CONFIRM_PASS` rule and must not be used to rescue D051.

## Management evidence already learned

Do not assume management is a universal rescue mechanism.

D041 / D032-M2 tested a sophisticated management candidate against a simple +24h reference on a previously confirmed entry edge. Candidate mean stayed positive, but paired candidate-minus-reference delta was **-0.3380537662R/trade**, total delta -26.03014R, positive-delta symbols 0/3, and the 95% month-block bootstrap interval was entirely negative. Verdict: **REJECT_MANAGEMENT**.

Earlier management benchmarks across D038/D039/D040/D045 also found no universal promotion: most TP/BE/partial variants degraded baseline. `BE_AFTER_2R` was only a tiny exploratory improvement and not robust enough for promotion.

## Next scientific question — proposed, not yet executed

The user explicitly raised the belief: **“a good management can save almost any signal.”**

This is worth testing directly rather than arguing about it. Preferred next experiment is a separate **management-as-alpha null-entry lab**:
- deliberately uninformed/placebo entries, deterministic and reproducible;
- broad multi-market sample;
- one frozen family of management rules evaluated in DEV;
- candidate-selection rule fixed before results;
- only one selected management allowed into a truly untouched holdout;
- require both positive absolute expectancy after costs and paired improvement over a simple reference;
- if management cannot make placebo entries robustly profitable, the strong universal-rescue belief is falsified for the tested management family;
- if it can, management itself is functioning as alpha and should be treated as a strategy component in its own right.

Do not use D051’s seen 2026-H1 data to design an exit and call NR7 rescued. Any further management work must be a new hypothesis with its own validation boundary.

## Local paths

Repo: `D:\MT5_Backtests\guardian-research`
Runner workspace: `D:\MT5_Backtests\guardian-runner`
FundedNext MT5: `D:\MT5_FundedNext`
Experts: `D:\MT5_FundedNext\MQL5\Experts\GuardianResearch`
FILE_COMMON: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files`

## Style

Concise, direct, technically opinionated when evidence supports it. Distinguish fact, inference and unknown. Contradict the user when evidence warrants it. Do not manufacture optimism.
