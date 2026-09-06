# Guardian Research Runner — migration plan

Date: 2026-09-06
Status: ACTIVE REFACTOR PLAN
Branch: `refactor/guardian-research-runner-v1`

## Objective

Reduce the elapsed time and human work between:

`strategy idea -> frozen experiment -> compile -> smoke -> development -> scoring -> verdict -> confirmation`

without weakening reproducibility, OOS discipline, realistic-cost checks, or Guardian production safety.

The refactor must simplify the research factory. It must not become another large infrastructure project.

## Non-negotiable rules

1. Guardian Core remains separate from strategy research.
2. Existing validated/rejected research evidence is preserved.
3. No legacy automation is removed from the active branch until its replacement has passed an end-to-end test.
4. Strategy source files are complete, immutable, versioned repository artifacts. Installers/builders must not manufacture new strategy code by textual patching.
5. Long MT5 runs are never the first engineering test. Compile + deterministic smoke/integrity checks come first, unless an explicit deviation is recorded before result inspection.
6. OOS periods remain scarce and protected.
7. Machine-readable state is authoritative. Human-facing summaries are generated from, or checked against, that state.
8. No active workflow may depend on Codex availability.
9. Non-Guardian personal projects are preserved but moved outside the Guardian research context.

## Target active layout

```text
/
  GUARDIAN_STATE.json                # single machine-readable project state
  START_HERE_NEXT_AI.md              # generated/thin human entrypoint

  production/                        # Guardian runtime only
  research/
    experiments/                     # one manifest per experiment
    strategies/                      # full versioned strategy sources
    runner/                          # generic deterministic research runner
    analysis/                        # reusable scorers/statistics
    results/                         # verdicts and evidence

  automation/
    v3/                              # deploy/result transport only

  archive/
    legacy_automation/               # old v1/v2 scripts after v3 proof
    handoffs/                        # historical AI handoffs after migration
    non_guardian_projects/           # preserved personal/non-Guardian material
```

## Phase 0 — freeze and map

Goal: know exactly what is current before moving anything.

Deliverables:
- refactor branch created from current `main`;
- `GUARDIAN_STATE.json` introduced;
- migration plan committed;
- current research/production/transport ambiguity explicitly recorded;
- no behavior change.

Exit gate:
- repository still usable exactly as before.

## Phase 1 — one source of truth

Goal: eliminate divergent `START_HERE`, queue, handoff and production-current states.

Actions:
- make `GUARDIAN_STATE.json` authoritative;
- add a validator that fails on contradictions;
- reduce `START_HERE_NEXT_AI.md` to a thin generated/checked entrypoint;
- convert `CURRENT_QUEUE.json` to either generated compatibility output or archive it after migration;
- remove `WAITING_CODEX` as a blocking operational concept.

Exit gate:
- an AI can determine current P0, production baseline, current runner status and next action from one file plus linked experiment manifest.

## Phase 2 — generic experiment contract

Goal: one schema for every D0xx experiment.

Each experiment manifest must freeze at minimum:
- experiment/strategy id;
- hypothesis and economic rationale;
- source path + source SHA;
- timeframe and markets;
- DEV period;
- untouched confirmation/OOS period;
- cost model;
- parameters;
- expected output contract;
- smoke gate;
- development pass/reject gates;
- confirmation gates;
- current lifecycle status;
- result paths;
- final verdict.

Exit gate:
- D038+ can be launched without inventing a new orchestration file format.

## Phase 3 — Guardian Research Runner v1

Goal: one deterministic command for all strategy experiments.

Target interface:

```powershell
guardian-research run D038
```

Runner stages:

1. resolve manifest;
2. validate repository/source identity;
3. deploy exact source to MT5 staging target;
4. verify source hash after copy;
5. compile with MetaEditor;
6. verify EX5 build result/provenance where available;
7. run short smoke/integrity test;
8. inspect INIT/FINAL lifecycle and output schema;
9. launch frozen development batch;
10. collect outputs;
11. score deterministic gates;
12. write machine-readable verdict;
13. publish result bundle;
14. update state.

The runner must stop automatically on engineering/integrity failure and must distinguish:
- strategy rejection;
- harness/integrity failure;
- transport failure;
- unavailable local dependency.

Exit gate:
- two different strategy families complete compile -> smoke -> DEV -> score without creating strategy-specific runner/install/flush scripts.

## Phase 4 — fast screening before MT5

Goal: use MT5 only where its execution realism is useful.

For strategies expressible from OHLC/bar data:
- first-pass Python screening on exported historical data;
- reject obviously weak ideas cheaply;
- only promising/frozen candidates enter MT5 conformance testing.

Python screening is discovery/development evidence, not a substitute for realistic MT5 confirmation when execution semantics matter.

Exit gate:
- a failed simple hypothesis can usually be rejected without a full MT5 campaign.

## Phase 5 — AutoSync v3

Goal: make transport boring and invisible.

Implement the existing v3 engineering standard:
- separate GitHub -> PC deploy and PC -> GitHub result pipelines;
- dedicated disposable clones;
- immutable result spool;
- durable per-run state;
- fingerprinting;
- quarantine for invalid artifacts;
- bounded retry for transport failures;
- scheduled-task supervision;
- health JSON;
- end-to-end regression harness.

Exit gate:
- two consecutive new result bundles travel PC -> GitHub with zero manual intervention;
- two source deployments prove exact source/destination hash equality.

Only then archive v1/v2.x transport scripts.

## Phase 6 — cleanup and guardrails

Goal: reduce context and prevent regression.

Actions:
- archive superseded installers/recovery scripts;
- archive historical AI handoffs outside the active read path;
- preserve rejected research and evidence ledgers;
- preserve non-Guardian personal projects under `archive/non_guardian_projects/`;
- add repository consistency checks;
- add CI for JSON/schema/state consistency and Python tests;
- optionally protect `main` once checks are stable.

Exit gate:
- new contributors/AI read a small active surface;
- historical evidence remains available without polluting normal context.

## What is explicitly NOT part of this refactor

- redesigning Guardian Core;
- changing active trading risk because of backtest performance;
- rescuing rejected D017/D023/D036 experiments;
- building a generic high-dimensional optimizer;
- tuning strategies while migrating infrastructure;
- deleting historical evidence or personal project material.

## Success metric

The main operational metric is elapsed human intervention per experiment.

Target end state:

> A new frozen simple strategy should require one manifest + one full strategy source. Everything from compile through first verdict should be deterministic and reusable.
