# Guardian Research Runner — Ergonomics & Speed Audit

Date: 2026-09-07 Europe/Paris
Status: **AUDIT COMPLETE / MINIMAL CHANGES APPLIED**

## Executive conclusion

The research runner is now scientifically usable end-to-end. The next bottleneck is not missing infrastructure; it is MT5 `Model=0` tick simulation and the number of genuinely independent hypotheses worth testing.

The correct optimization is therefore **less operator friction and less duplicate transport**, not more daemons, more orchestration or unsafe parallel MT5 instances.

## What is now proven

D038 proved the complete live path:

`compile -> smoke -> native Trade Path -> DEV six-market batch -> frozen decision score -> rich score -> compact GitHub publication -> stable latest pointer`

The PC successfully published machine-readable results to `backtest-results`, allowing the user to say only `fini` and the assistant to retrieve the result from GitHub.

This is the first ergonomically useful transport state in the project.

## Friction found

### 1. One experiment at a time — FIXED

Before this audit, six new strategies would require repeating compile/batch/path/score/rich/publish commands manually for each experiment.

Applied change:
- added `research/runner/campaign.py`;
- exposed it through the unified `guardian_research.py campaign ...` interface;
- campaign runs several frozen experiments sequentially in one unattended pass;
- each experiment compiles independently;
- each symbol batch remains sequential;
- native Trade Path is validated automatically when the manifest requires it;
- development campaigns can score, rich-score and publish each experiment;
- scientific rejection does **not** stop later experiments;
- an engineering/integrity failure is isolated to that experiment and recorded, then the campaign continues;
- a global campaign receipt is persisted.

Example future smoke command once D039..D045 are executable:

```powershell
py -3 .\research\runner\guardian_research.py campaign D039 D040 D041 D042 D043 D044 D045 --stage smoke --no-finalize
```

This is deliberately sequential, not parallel.

### 2. Rich-score GitHub event duplicated the full analytics payload — FIXED

The rich score was already copied as `rich_score.json`, but `result_transport.py` also embedded the full analytics tree inside `event.json`. D038 produced an event envelope over ~300 KiB even though the same evidence existed beside it.

Applied change:
- rich-score `event.json` now carries only a compact summary/pointer;
- full `rich_score.json` and `trades_compact.csv` remain separately published with SHA/size provenance;
- the idempotence fingerprint still covers the original full payload;
- no scientific evidence is discarded.

Expected benefit: smaller Git commits, faster `latest` inspection, less repository bloat.

### 3. Legacy Backtest Bot is still publishing duplicate inbox commits — SAFE INSPECTION ADDED

During D038 the branch still received commits authored by `Guardian Backtest Bot` with messages like `Auto-sync validated D038 CSV ...`, while the new runner also published its own clean events.

Conclusion:
- this old publisher is **not required**;
- it creates duplicate evidence/noise and can race the new transport;
- it must not be used as fallback;
- it should be identified and disabled on the Windows PC before a large unattended multi-strategy campaign.

Applied safety change:
- added `research/runner/Inspect-LegacyResultTransport.ps1`;
- it is read-only;
- it lists matching scheduled tasks and running process command lines;
- it never stops/disables/deletes anything.

Use it first, identify the task/process that actually owns commits authored as `Guardian Backtest Bot <guardian-backtest@local>`, then disable only that legacy component. Do not guess based on a task name containing `Guardian`.

### 4. Stage lifecycle still requires manifest state transitions — ACCEPTED FOR NOW

D038 demonstrated that the EA strategy no longer needs a different source for smoke/DEV/confirmation: tester date ranges control the stage.

However, the current runner still uses `default_stage` as a lifecycle guard. This causes a controlled manifest update between smoke and DEV.

This is mildly inconvenient but scientifically useful: it prevents accidentally opening confirmation or running a locked stage. Do **not** remove this guard merely to save one state commit.

Future minimal refinement may separate:
- `stage transport = TESTER_DATE_RANGE_ONLY`, from
- `stage authorization = manifest lifecycle status`.

Do this only with regression tests; it is not worth destabilizing the runner before D039 smoke.

### 5. MT5 Model=0 dominates runtime — NO UNSAFE SPEEDUP

D038 six-market two-year DEV took only a few minutes, which is already acceptable for overnight/multi-strategy work.

Do not switch scientific runs to `Model=1` / 1-minute OHLC merely for speed:
- entry side is executable BID/ASK;
- stop order sequencing matters;
- native MFE/MAE and first-touch milestones require tick path;
- same-bar ordering ambiguity would otherwise return.

`Model=0` remains the reference model.

### 6. Parallel MT5 strategy execution — REJECTED FOR NOW

Running several MT5 terminals/experiments concurrently could shorten wall-clock time but currently risks:
- shared `FILE_COMMON` names;
- stale-output quarantine races;
- terminal portable-data contention;
- result ownership ambiguity;
- CPU/disk saturation changing tester throughput unpredictably.

The new campaign runner therefore uses:

`SEQUENTIAL_EXPERIMENTS_SEQUENTIAL_SYMBOLS`

This is the right trade-off until process-level output isolation is proven in a dedicated engineering experiment.

## Data/science audit after D038

### Good

- decision scoring is frozen and separate from rich analytics;
- D038 remained `REJECT_V0` despite attractive performance because n=459 missed the preregistered 480 gate;
- native Trade Path successfully turned a rejected V0 into reusable research evidence without changing the verdict;
- result publication now works without user copy/paste;
- 2026 confirmation remained unopened.

### Important weakness discovered and fixed

The first rich scorer still hardcoded the old D037 message `trade_path.available=false`. D038's native MFE/MAE fields were present but ignored.

This was corrected before using path data for the next management hypothesis. Regression coverage now proves native Trade Path is recognized.

## Recommended operator workflow from D039 onward

For one new strategy:

1. assistant preregisters + writes source + freezes SHA in GitHub;
2. user pulls once;
3. user runs compile/smoke, or a campaign smoke for several ready experiments;
4. user says only `fini`;
5. assistant reads `backtests/<id>/live/latest.json` and evidence;
6. only after engineering PASS does DEV open;
7. development campaign can automatically score/rich-score/publish;
8. confirmation is never opened automatically from a failed DEV verdict.

For multiple ready strategies, prefer the unified `guardian_research.py campaign ...` command rather than repeated manual command sequences.

## Anti-sprawl decision

Do **not** build now:
- AutoSync v3 daemon;
- web dashboard;
- database;
- parallel MT5 farm;
- job queue service;
- remote control plane.

The minimal runner + isolated Git publisher now solves the immediate research ergonomics problem. Spend the next effort on alpha/attribution, not infrastructure.
