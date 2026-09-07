# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **D054 CLOSED / ORB30 CORE-3 UNCONFIRMED**

## Read this first on a new chat

Read in this order:
1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `reports/research/D054_ORB30_CORE3_CONFIRMATION_CLOSEOUT_20260907.md`
4. `research/experiments/D054.json`
5. `research/campaigns/D054_ORB30_CORE3_JUL_AUG_2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md`
6. `research/runner/d053_orb30_deep_audit.py`
7. `reports/research/D053_US_INDEX_ORB30_DEV_CLOSEOUT_20260907.md`
8. `GUARDIAN_MASTER_MANDATE.md`

`GUARDIAN_STATE.json` is authoritative. `START_HERE_NEXT_AI.md` and `CURRENT_QUEUE.json` are generated compatibility views.

Important: the similarly named older file
`research/campaigns/D054_ORB30_CORE3_JUL_AUG2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md`
is **SUPERSEDED / DO NOT EXECUTE**.

## Canonical operator UX

- Assistant prepares GitHub/state/research tooling.
- Give one short PowerShell block only when local execution is required.
- Runner publishes evidence automatically to `backtest-results`.
- User normally replies only **`fini`**.
- On `fini`, fetch GitHub evidence directly; do not ask for pasted logs if transport worked.
- Transport failure alone never justifies replaying valid MT5 science.
- Keep MT5 sequential.

## Hard boundaries

- Guardian Core v12.01 remains frozen compile-validated production baseline.
- Do not merge to `main` unless explicitly requested/reviewed.
- Never `git reset --hard` or destructively clean unrelated work.
- Legacy AutoSync v1/v2 and Guardian Backtest Bot are untrusted historical systems; never fallback.
- No post-hoc rescue, threshold retune, symbol deletion after results, direction selection after results, or reuse of seen data as OOS.

## D053 — economically strong, formally rejected

Experiment: `D053-US-INDEX-ORB30-ENTRY-ALPHA-V0`

2024-2025:
- n **2,042**
- mean **+0.061984R/trade**
- PF **1.1349**
- total **+126.57R**
- stress **+88.56R**
- 2024 **+67.54R**
- 2025 **+59.03R**
- LONG **+61.76R**
- SHORT **+64.81R**
- integrity **0**

Per symbol:
- SPX500 **+36.99R**
- NDX100 **+48.08R**
- US30 **+46.21R**
- US2000 **-4.71R**

D053 passed 11/12 frozen DEV gates. Sole failure: month-block bootstrap lower95 **-0.029041R** required >0. Formal verdict remains `D053_REJECT_V0`.

Descriptive audit event:
`backtests/d053/live/events/development/d053-descriptive-audit/20260907T182547Z`

Useful descriptive findings from already-seen 2024-2025 data include:
- Friday was strongest historically;
- first 15 minutes after 17:00 server carried most historical edge;
- DST mismatch proxy was much weaker than aligned periods;
- these are hypothesis-generation only and cannot rescue D053/D054.

## D054 — independent Core-3 confirmation

Experiment:
`D054-ORB30-CORE3-JUL-AUG2026-CONFIRMATION-V0`

D054 was a new derived hypothesis, not a D053 rewrite. Core-3 was explicitly chosen post-D053 discovery:
- SPX500
- NDX100
- US30

It reused exact D053 v1.01 source bytes, unchanged.

Source SHA256:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

Independent confirmation window:
- **2026-07-01 through 2026-08-31**
- untouched before D054
- Model0 / Every tick

Authoritative score event:
`backtests/d054/live/events/confirmation/d054-confirmation-score/20260907T182809Z`

Result:
- n **127**
- mean **-0.199334R/trade**
- PF **0.559651**
- total **-25.315464R**
- spread-stress **-26.342194R**
- integrity **0**

Per symbol:
- SPX500: 43 trades, **-6.053875R**
- NDX100: 42 trades, **-9.204839R**
- US30: 42 trades, **-10.056750R**
- positive symbols: **0/3**

By month:
- July 2026 **-18.952060R**
- August 2026 **-6.363405R**

By direction:
- LONG: 61 trades, **-12.130049R**, mean **-0.198853R**
- SHORT: 66 trades, **-13.185416R**, mean **-0.199779R**

Day-block bootstrap, 20,000 reps:
- lower95 **-0.368529R/trade**
- median **-0.200567R/trade**
- upper95 **-0.017671R/trade**

The entire bootstrap interval is below zero.

Formal verdict:
`D054_UNCONFIRMED_CLOSE`

Closeout:
`reports/research/D054_ORB30_CORE3_CONFIRMATION_CLOSEOUT_20260907.md`

Interpretation: this is not another near-pass. The exact historical ORB30 baseline failed broadly on untouched data: all three indices negative, both months negative, both directions negative, stress negative, PF well below 1 and even bootstrap upper95 below zero. Do not promote to production.

## Scientific consequence

No second Jul-Aug 2026 ORB variant is allowed after seeing D054.

The D053 audit plus D054 failure may generate a new hypothesis, but any D055 must be preregistered and judged only on a **new untouched/prospective evidence boundary**. Historical observations such as Friday strength, early-breakout strength or DST alignment cannot be applied retrospectively to Jul-Aug and called confirmation.

The most defensible next step is hypothesis design, not another immediate salvage run.

## Current operator action

**No PowerShell command is required now.**

Next research action is assistant-side review/design of a new D055 candidate. If a D055 is justified, freeze its source/rules/gates before any new unseen data are evaluated, then return to the canonical one-command operator workflow.

## Local paths

Repo: `D:\MT5_Backtests\guardian-research`
Runner workspace: `D:\MT5_Backtests\guardian-runner`
FundedNext MT5: `D:\MT5_FundedNext`
MetaEditor: `D:\MT5_FundedNext\MetaEditor64.exe`
Terminal: `D:\MT5_FundedNext\terminal64.exe`
Experts: `D:\MT5_FundedNext\MQL5\Experts\GuardianResearch`
FILE_COMMON: `C:\Users\armor\AppData\Roaming\MetaQuotes\Terminal\Common\Files`

## Style

Concise, direct, technically opinionated when evidence supports it. Distinguish fact, inference and unknown. Contradict the user when evidence warrants it. Do not manufacture optimism.
