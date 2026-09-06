# Guardian Research Runner v1

Status: foundation only — no live MT5 behavior changed yet.

## Purpose

Provide one deterministic execution path for all D0xx research experiments.

A strategy experiment should contribute only:

1. one complete, versioned strategy source;
2. one machine-readable experiment manifest;
3. reusable analysis/scoring code only when the generic scorer cannot express the frozen gates.

Everything else belongs to the runner.

## Intended command surface

```powershell
guardian-research validate D038
guardian-research compile D038
guardian-research smoke D038
guardian-research dev D038
guardian-research score D038
guardian-research run D038
```

`run` is orchestration sugar. Every stage remains individually callable and idempotent.

## Stage contract

### validate
- load experiment manifest;
- validate schema;
- verify frozen source exists;
- calculate source SHA-256;
- reject source/manifest mismatch;
- verify DEV/OOS periods do not overlap;
- verify required gates exist;
- verify no rejected experiment is accidentally reopened without an explicit new experiment id.

### compile
- copy exact repository source to MT5 staging location;
- compare source/destination SHA-256;
- invoke MetaEditor;
- require 0 errors / 0 warnings unless manifest explicitly records another frozen compile policy;
- record compile receipt.

### smoke
- run a short deterministic technical test;
- require output lifecycle (`INIT` then `FINAL`);
- validate schema/counters/identity;
- inspect at least one meaningful strategy event when feasible;
- never inspect confirmation/OOS data here.

### dev
- run only the frozen development universe;
- preserve one immutable run directory per symbol/config;
- fail closed on output integrity issues;
- do not silently retry strategy/harness defects under the same source identity.

### score
- compute frozen metrics and gates;
- distinguish `PASS`, `REJECT`, and `INVALID_RUN`;
- write `verdict.json` plus concise human summary;
- never mutate strategy parameters.

### confirm
- available only after development/robustness gates permit it;
- requires frozen source SHA + frozen gates;
- marks the confirmation period as opened before reading results;
- confirmation failure cannot be rescued by retuning the same opened sample.

## Artifact model

Target local/GitHub bundle:

```text
runs/D038/<run_id>/
  manifest.json
  source_receipt.json
  compile_receipt.json
  run_receipt.json
  stats.csv
  trades.csv
  score.json
  verdict.json
  summary.md
```

`run_id` must uniquely identify experiment, source version/SHA, stage, market, period and execution profile.

## Error classes

The runner must never collapse these into one generic failure:

- `CONFIG_ERROR` — invalid/missing manifest or dependency;
- `SOURCE_ERROR` — missing source or SHA mismatch;
- `COMPILE_ERROR` — MetaEditor failure;
- `HARNESS_ERROR` — lifecycle/output/provenance failure;
- `RUNNER_ERROR` — orchestration bug;
- `TRANSPORT_ERROR` — Git/network publication problem;
- `STRATEGY_REJECT` — valid run, frozen scientific gates failed;
- `STRATEGY_PASS` — valid run, frozen scientific gates passed.

Only transport errors are normally retryable without changing scientific provenance.

## First migration specimen

D037 will be used as the first real specimen, but the runner must remain generic.

Before that migration:
- replace textual v1.00 -> v1.01 source generation with a complete committed v1.01 source;
- preserve D037 preregistered strategy semantics;
- treat the already-recorded smoke waiver as historical execution context, not as a template for future experiments.

## Rule against framework creep

Do not add a feature to the runner because one strategy can imagine using it. Add only features required by at least one current frozen experiment or by universal reproducibility/safety requirements.
