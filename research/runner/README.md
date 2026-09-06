# Guardian Research Runner v1

Status: Windows MT5 compile, single-symbol integrity, six-symbol DEV batch and frozen decision scoring have been locally proven on D037. Rich analytics and isolated GitHub results publishing are implemented and awaiting first local `finalize` proof.

## Purpose

Reduce a frozen strategy experiment to:

`manifest + complete .mq5 source -> compile -> MT5 batch -> integrity checks -> frozen decision gates -> rich analytics -> compact publish bundle`

No Codex and no legacy AutoSync are required for the local research path.

A strategy experiment should contribute only:
1. one complete, versioned strategy source;
2. one machine-readable experiment manifest;
3. reusable analysis/scoring code only when the generic scorer cannot express frozen gates.

## Scientific separation

The runner keeps two score layers separate:

- **Decision score** — preregistered frozen gates only. This alone decides `REJECT_V0` / `CANDIDATE_CONFIRM`.
- **Rich score** — descriptive research data retained for later cross-strategy analysis and Exit Lab hypotheses. It never changes the originating experiment verdict.

D037 is permanently `REJECT_V0`, even though its validated 2,377 DEV trades remain useful descriptive data.

## Implemented

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
- rich descriptive analytics;
- compact UTF-8 trade outcome dataset;
- isolated `backtest-results` branch publisher;
- idempotent publish path keyed by validated batch id;
- one-command finalization without rerunning MT5.

## Command surface

```powershell
py -3 research/runner/guardian_research.py doctor D037
py -3 research/runner/guardian_research.py plan D037
py -3 research/runner/guardian_research.py compile D037
py -3 research/runner/guardian_research.py test-one D037 --stage development --symbol USDJPY
py -3 research/runner/guardian_research.py batch D037 --stage development
py -3 research/runner/guardian_research.py score D037 --stage development
py -3 research/runner/guardian_research.py rich-score D037 --stage development
py -3 research/runner/guardian_research.py publish D037 --stage development
py -3 research/runner/guardian_research.py finalize D037 --stage development
```

`run` means: fresh compile -> frozen default-stage batch -> decision score.

`finalize` means: consume an already integrity-passed batch -> frozen decision score -> rich descriptive score -> compact publication to `backtest-results`. It launches no MT5 backtest and never opens confirmation automatically.

## Rich analytics

Where supported by the evidence, the common scorer records:

- trade count, total/mean/median/stdev/quantiles of net R;
- gross/net/stressed Profit Factor;
- win rate, average winner/loser, payoff ratio;
- realized trade-close cumulative-R drawdown and win/loss streaks;
- commission drag;
- duration and risk-money distributions;
- per symbol, asset class, side, exit reason, year and month;
- symbol × year matrix;
- positive/negative symbol/year/month counts;
- top/bottom 1%, 5%, 10% trade concentration;
- descriptive entry-hour and weekday breakdowns;
- realized exit-R threshold counts.

Realized exit-R thresholds are not MFE/MAE. D037 did not record intratrade path telemetry.

Future harnesses should follow `research/runner/TRADE_PATH_DATASET_SPEC.md` so MFE, MAE, first touch 0.5R/1R/2R/3R/5R, time-to-level and giveback metrics are collected natively.

## Reference tester model

D037 is pinned to MT5 `Model=0` (Every tick) as the reference execution mode until a short conformance experiment proves that a faster model produces equivalent trade evidence. Speed must not silently alter strategy semantics.

The manifest records `Model=1` (1 minute OHLC) only as a fast candidate, not as an approved replacement.

## Local result layout

The workspace defaults to `D:/MT5_Backtests/guardian-runner` when available.

```text
builds/<experiment>/<utc>/build.json
runs/<experiment>/<stage>/<run-id>/run.json
batches/<experiment>/<stage>/<batch-id>/batch.json
scores/<experiment>/<stage>/<utc>/verdict.json
rich_scores/<experiment>/<stage>/<utc>/rich_score.json
publish_bundles/<experiment>/<stage>/<utc>/...
publish_receipts/<experiment>/<stage>/<batch-id>.json
quarantine/stale_outputs/...
```

Raw MT5 CSV files remain immutable local evidence and are SHA-256-addressed in receipts.

## GitHub result publishing

Validated compact bundles are published to the existing `backtest-results` branch under:

```text
backtests/<short-experiment-id>/<stage>/<batch-id>/
```

Published files:

- `SUMMARY.md`
- `decision_score.json`
- `analytics.json`
- `manifest.json`
- `trades_compact.csv` when <= 5 MiB

Large raw evidence stays on the PC; GitHub receives SHA256 and byte-size provenance.

The publisher creates a temporary isolated single-branch clone under the runner workspace. It never checks out `backtest-results` in the user's active research working tree, never runs `git reset --hard`, and never uses legacy AutoSync. Re-publishing the same validated batch with the same evidence is a no-op; a same-path payload collision fails closed.

## Failure classes

The runner must not collapse these into one generic failure:

- project/manifest contradiction;
- source identity failure;
- missing local dependency;
- compile failure;
- missing MT5 output;
- lifecycle/integrity failure;
- strategy gate rejection;
- rich-analysis failure;
- result-publication failure.

An engineering/integrity failure is never treated as strategy rejection.

## Confirmation discipline

A development pass only produces `CANDIDATE_CONFIRM`. The runner does not automatically open the untouched confirmation sample. Opening confirmation requires an explicit state transition after the development verdict is recorded.

## Rule against framework creep

Do not add a feature because one strategy can imagine using it. Add only features required by a current frozen experiment or by universal reproducibility/safety requirements.
