# Guardian Research Runner v1

Status: GitHub/static validation green; first Windows MT5 proof still required before merge.

## Purpose

Reduce a frozen strategy experiment to:

`manifest + complete .mq5 source -> compile -> MT5 batch -> integrity checks -> frozen gates -> verdict`

No Codex and no AutoSync are required for the local research path.

A strategy experiment should contribute only:
1. one complete, versioned strategy source;
2. one machine-readable experiment manifest;
3. reusable analysis/scoring code only when the generic scorer cannot express frozen gates.

## Implemented now

- authoritative project-state validation;
- generic D0xx manifest validation;
- source SHA-256 verification;
- exact local copy into the dedicated MT5 Experts research folder;
- source/destination SHA-256 equality proof;
- MetaEditor compile and 0 errors / 0 warnings requirement;
- EX5 SHA-256 build receipt;
- MT5 Strategy Tester `.ini` generation;
- sequential multi-symbol testing;
- stale `FILE_COMMON` result quarantine;
- immutable local result evidence;
- lifecycle / source identity / row-count / integrity validation;
- deterministic D037 development gate scoring;
- one-command compile -> batch -> score pipeline.

Not yet proven on the user's Windows MT5 machine:
- actual local path autodetection;
- MetaEditor invocation against the installed FundedNext terminal;
- terminal `/config:` Strategy Tester launch;
- end-to-end `FILE_COMMON` collection.

Therefore this branch must not be treated as locally validated yet.

## Command surface

```powershell
python research/runner/guardian_research.py doctor D037
python research/runner/guardian_research.py plan D037
python research/runner/guardian_research.py compile D037
python research/runner/guardian_research.py test-one D037 --stage development --symbol USDJPY
python research/runner/guardian_research.py batch D037 --stage development
python research/runner/guardian_research.py score D037
python research/runner/guardian_research.py run D037
```

`run` currently means: fresh compile -> frozen default-stage batch -> score.

## First local proof

From the repository root on the MT5 research PC, while on branch `refactor/guardian-research-runner-v1`:

```powershell
powershell -ExecutionPolicy Bypass -File research/runner/Run-GuardianResearch.ps1 -BootstrapOnly
```

This only autodetects/configures paths and runs `doctor`. It launches no backtest.

Then compile D037 only:

```powershell
python research/runner/guardian_research.py compile D037
```

Required evidence before any DEV run:
- repository source SHA matches the D037 manifest;
- deployed source SHA equals repository source SHA;
- MetaEditor reports 0 errors / 0 warnings;
- EX5 exists;
- build receipt contains EX5 SHA.

Then one symbol:

```powershell
python research/runner/guardian_research.py test-one D037 --stage development --symbol USDJPY
```

Only after that succeeds should the complete current pipeline run:

```powershell
powershell -ExecutionPolicy Bypass -File research/runner/Run-GuardianResearch.ps1
```

## Reference tester model

D037 is pinned to MT5 `Model=0` (Every tick) as the reference execution mode until a short conformance experiment proves that a faster model produces equivalent D037 trade evidence. Speed must not silently alter strategy semantics.

The manifest records `Model=1` (1 minute OHLC) only as the current fast candidate, not as an approved replacement.

## Result layout

The local workspace defaults to `D:/MT5_Backtests/guardian-runner` when available.

```text
builds/<experiment>/<utc>/build.json
runs/<experiment>/<stage>/<run-id>/run.json
batches/<experiment>/<stage>/<utc>/batch.json
scores/<experiment>/<stage>/<utc>/verdict.json
quarantine/stale_outputs/...
```

Raw MT5 CSV files are copied into each immutable run directory and SHA-256-addressed in `run.json`.

## Failure classes

The runner must not collapse these into one generic failure:
- project/manifest contradiction;
- source identity failure;
- missing local dependency;
- compile failure;
- missing MT5 output;
- lifecycle/integrity failure;
- strategy gate rejection;
- transport failure.

An engineering/integrity failure is never treated as strategy rejection.

## Confirmation discipline

A development pass only produces `CANDIDATE_CONFIRM`. The runner does not automatically open the untouched confirmation sample. Opening confirmation requires an explicit state transition after the development verdict is recorded.

## AutoSync

Legacy AutoSync v1/v2 is not part of this execution path and is never used as fallback. A future AutoSync v3 is transport only, after the local runner is proven.

## Rule against framework creep

Do not add a feature because one strategy can imagine using it. Add only features required by a current frozen experiment or by universal reproducibility/safety requirements.
