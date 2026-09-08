# Phenomenon Discovery — Current Handoff — 2026-09-08

Repository: `yum4nity-code/guardian-research`

Branches:
- `main` = code / governance / autonomous queue
- `backtest-results` = published run evidence

Owner worktree:
- `D:\MT5_Backtests\guardian-phaseA-20260908`

Autonomous control plane:
- `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md`
- `research/autonomous/RESEARCH_QUEUE.json`
- `research/autonomous/guardian_research_orchestrator_v1_00.py`

**Read the autonomous mandate and queue before this file.** Never ask the owner to copy/paste run output when GitHub publication exists.

## Scientific chronology completed

Protected final OOS rule:
- 2024 = discovery.
- 2025 = internal confirmation.
- **2026 remains sealed final OOS and cannot be opened without explicit owner approval plus committed preregistration.**

BTC/ETH 5m chronology:
- A data gate PASS.
- B coarse atlas: 38 survivors, mostly low-movement.
- C robustness: **18 robust low-movement/no-trade phenomena**; no directional survivor.
- D exact 3-clause states: 0 directional survivors.
- E-A derivative context gate PASS; E-B transition atlas 0 survivors.
- F-A orderflow gate PASS; F-B/F-C 0 survivors.
- G constrained ensemble 0 survivors.
- H-A rare-event shock matrix PASS; H-B 1,140 hypotheses / 75 frozen shortlist / **0 confirmation survivors**.

Conclusion:
- BTC/ETH 5m directional search on this information family is closed.
- Do not rescue rejected families with more filters/tails/named strategies.
- Preserve Phase C only as a possible future low-amplitude/no-trade filter, after exact live ATR-slope conformance is checked.

## XAU pivot

### Phase I-A — PASS

Historical high-impact USD news mask exported from the canonical sole-open FundedNext MT5 session.

Verified final evidence:
- server: `FundedNext-Server 2`
- terminal/data path: `D:\MT5_FundedNext`
- 2024 high-impact USD events: 504
- 2025: 477
- XAU-relevant event rows: 981
- merged exclusion intervals: 634
- conservative exclusion: +/-5 minutes
- duplicates: 0
- protected 2026 rows: 0
- integrity: PASS

Publication:
- `phenomenon-discovery/phase-ia-news-mask/LATEST.json` on `backtest-results`

### Phase I-B — current data gate

Goal:
- export XAUUSD M1 + M5 for 2024-2025 only;
- exact same FundedNext server and `TERMINAL_DATA_PATH` as I-A;
- apply the frozen I-A +/-5m news mask before research use;
- integrity-check raw/clean coverage and keep 2026 sealed.

Canonical resilient files:
- `research/phenomenon_discovery/export_mt5_xau_history_v1_01.mq5`
- `research/phenomenon_discovery/START_PHASE_IB_XAU_DATASET_OPEN_SESSION_V1_01.ps1`
- `research/phenomenon_discovery/build_xau_news_clean_dataset_v1_00.py`
- `research/phenomenon_discovery/check_xau_news_clean_dataset_v1_00.py`

Latest known GitHub state at this handoff update: I-B `RUNNING`; do not infer success from the MT5 script merely appearing/disappearing. Read `backtest-results`.

### Phase I-C — already preregistered and queued

Once I-B publishes PASS, the local autonomous orchestrator is allowed to run Phase I-C automatically.

Frozen files:
- `research/autonomous/phase_ic_xau_phenomenon_policy_v1.json`
- `research/autonomous/phase_ic_xau_phenomenon_atlas_v1_00.py`

Design:
- M5 news-clean data only;
- 2024 fits/freeze state cutpoints and screens;
- 2025 confirms with frozen cutpoints;
- horizons 15m / 30m / 1h / 2h;
- XAU-native price/volatility/volume/session state representation;
- BH multiple-testing control;
- effect retention and quarterly sign-stability gates;
- contiguous-bar labels cannot jump across news-excluded gaps;
- **no PnL, SL, TP, sizing, execution optimization or 2026 access.**

A Phase I-C survivor is a phenomenon candidate only. The autonomous supervisor must preregister the next robustness/translation stage before any trading-rule test.

## MT5 session rule

For I-A/I-B, use the one and only MT5 session already open on the owner's PC as canonical broker/server/data source. If zero or more than one `terminal64.exe` is running, fail closed.

Do not silently switch to another installation. Do not pretend `[StartUp] Script=` injects into an already-running GUI instance.

After I-B, ordinary research/backtests should preferentially run in Python from the frozen clean dataset. MT5 should only be re-entered when broker/server data or execution-fidelity validation is genuinely required.

## Autonomous execution

The persistent local executor uses:
- deploy clone: `D:\MT5_Backtests\guardian-autonomous-main`
- durable state: `D:\MT5_Backtests\Research\Autonomous`
- queue: `research/autonomous/RESEARCH_QUEUE.json`

Jobs are immutable by `(id, revision)`. The deterministic executor never invents hypotheses; ChatGPT is the scientific supervisor and updates the queue only after reading published evidence.

Codex is disabled by default. Use it only for a tightly scoped code blocker after deterministic repair attempts fail, within the mandate budget.

The owner is not a log courier. Normal research churn continues without notification. Escalate only for:
- a meaningful candidate that needs explicit permission to open 2026;
- unrecoverable local/MT5/account blockage;
- production/live-trading changes requiring approval.

## Watchdog rule

Runtime alone does not imply a hang. Use observed progress, expected duration and P95 of comparable successful runs. With heartbeat available, timeout requires both adaptive hard-limit breach and stale heartbeat. See autonomous mandate for the exact rule.

## Publication discipline

At `published`, `fini`, `résultat ?`, inspect GitHub directly.

Do not call an internal 2024/2025 survivor validated alpha. Do not use sizing or Challenge Probability Lab to rescue failed alpha. Challenge Lab only runs after a genuinely validated frozen candidate reaches the appropriate downstream gate.
