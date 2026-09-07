# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D054 ORB30 CORE-3 INDEPENDENT CONFIRMATION READY**

## Read this first on a new chat

Read in this order:
1. `GUARDIAN_STATE.json`
2. `docs/OPERATOR_POWERSHELL_HANDOFF_WORKFLOW.md`
3. `research/campaigns/D054_ORB30_CORE3_JUL_AUG_2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md`
4. `research/experiments/D054.json`
5. `research/runner/d054_orb30_core3_run.py`
6. `research/runner/d054_orb30_core3_workflow.py`
7. `research/runner/d053_orb30_deep_audit.py`
8. `reports/research/D053_US_INDEX_ORB30_DEV_CLOSEOUT_20260907.md`
9. `GUARDIAN_MASTER_MANDATE.md`

`GUARDIAN_STATE.json` is authoritative. `START_HERE_NEXT_AI.md` and `CURRENT_QUEUE.json` are generated compatibility views.

Important: the similarly named older file
`research/campaigns/D054_ORB30_CORE3_JUL_AUG2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md`
is explicitly **SUPERSEDED / DO NOT EXECUTE**.

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

## D053 closeout — economically strong, formally rejected

Experiment: `D053-US-INDEX-ORB30-ENTRY-ALPHA-V0`

Authoritative DEV event:
`backtests/d053/live/events/development/d053-development-score/20260907T162026Z`

Formal verdict: `D053_REJECT_V0`

2024-2025 result:
- n **2,042**
- mean **+0.061984R/trade**
- PF **1.1349**
- total **+126.57R**
- 1.5x spread-stress total **+88.56R**
- 2024 **+67.54R**
- 2025 **+59.03R**
- LONG **+61.76R**
- SHORT **+64.81R**
- integrity **0**

Per symbol:
- SPX500: **+36.99R / 511 trades**
- NDX100: **+48.08R / 512 trades**
- US30: **+46.21R / 509 trades**
- US2000: **-4.71R / 510 trades**

D053 passed 11/12 frozen DEV gates. Sole failure:
- required month-block bootstrap lower95 >0;
- observed **-0.029041R**.

Therefore D053 remains rejected. Jul-Aug 2026 was **not opened by D053**.

Closeout:
`reports/research/D053_US_INDEX_ORB30_DEV_CLOSEOUT_20260907.md`

## D054 scientific boundary

D054 is a **new derived hypothesis**, not a rewrite or rescue of D053.

The Core-3 universe is explicitly post-D053 discovery:
- SPX500
- NDX100
- US30

US2000 is excluded because D053 discovery showed it negative. This selection is permitted only because D054 pays for that selection entirely on untouched Jul-Aug 2026. D053 itself remains unchanged.

Experiment:
`D054-ORB30-CORE3-JUL-AUG2026-CONFIRMATION-V0`

Authoritative preregistration:
`research/campaigns/D054_ORB30_CORE3_JUL_AUG_2026_CONFIRMATION_PREREGISTRATION_2026_09_07.md`

Preregistration Git blob:
`2c1bb149664a9e4153c6f6cb8ae59ce1e874da57`

Exact D053 v1.01 source reused:
`research/strategies/d053/D053_USIndex_ORB30_Tick_M15_v1_00.mq5`

Source Git blob:
`7da58ecf8968d6814b634be0ee0043b9616fb6c6`

Normalized source SHA256:
`d39182cc7bd0376322fee474ec7c321b9e1f5d4db93cdb6ff301f0fb60aba7ad`

No D054 trading-source fork exists. This prevents semantic drift.

Exact rule remains D053 v1.01:
- M15, Model0 / Every tick;
- FundedNext server OR 16:30–17:00;
- first breakout +1 trade tick;
- opposite OR executable extreme initial stop;
- one trade/day;
- no TP, BE, trail, partial or filter;
- normal liquidation first executable tick >=22:45;
- unchanged `SESSION_END` fallback if session supplies no 22:45-or-later same-day tick;
- executable bid/ask;
- zero explicit index commission;
- frozen 1.5x spread stress.

## D053 deep audit

Tool:
`research/runner/d053_orb30_deep_audit.py`

It uses only already-seen local D053 2024-2025 CSVs and launches **zero MT5 backtests**.

It reports:
- monthly results and positive/negative month count;
- rolling 3m/6m stability;
- symbol and side attribution;
- weekdays;
- breakout latency after 17:00;
- exit reasons;
- risk-width quartiles;
- MFE/MAE and timing;
- US-vs-Europe DST mismatch proxy.

It is descriptive only. D054 rules/gates were frozen before this audit and cannot change from it. Any DST-aligned hypothesis must become D055 or later with a new evidence boundary.

## D054 execution

Engineering smoke:
- 2023-10-02 through 2023-10-31
- SPX500 / NDX100 / US30
- engineering only; economics ignored

Independent confirmation holdout:
- **2026-07-01 through 2026-08-31**
- SPX500 / NDX100 / US30
- untouched before D054

Frozen confirmation gates — **all 14 required**:
1. aggregate n >=100
2. each symbol n >=25
3. aggregate mean net R >0
4. aggregate PF >=1.05
5. aggregate total net R >0
6. 1.5x spread-stress total >0
7. at least 2/3 symbols positive
8. July 2026 total >0
9. August 2026 total >0
10. LONG mean >0
11. SHORT mean >0
12. day-block bootstrap 95% lower bound >0; 20,000 reps; seed 540054
13. max positive-symbol contribution share <=0.70
14. integrity events =0

Pass: `D054_CONFIRMED_CORE3_ENTRY_ALPHA`

Any scientific gate failure: `D054_UNCONFIRMED_CLOSE`

Engineering/data failure: `D054_ENGINEERING_INCOMPLETE` with no scientific verdict.

No second Jul-Aug variant is allowed after seeing D054.

## Current operator action

Run exactly:

```powershell
git pull
py -3 .\research\runner\d054_orb30_core3_run.py
```

This performs:
1. frozen D054 preflight;
2. D053 descriptive audit from existing local CSVs only;
3. compile exact D053 v1.01 source under D054 evidence identity;
4. 3-symbol engineering smoke;
5. if clean, opens Jul-Aug 2026 holdout exactly once;
6. 3-symbol confirmation;
7. strict 14-gate score including month, direction, concentration and day-bootstrap stability;
8. automatic GitHub publication.

No 2024-2025 MT5 rerun.

Then user normally replies only: `fini`.

On `fini`, fetch `backtests/d054/live/latest.json` from `backtest-results` and the D053 descriptive-audit event under `backtests/d053/live/events/development/d053-descriptive-audit/...`.

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
