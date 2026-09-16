# R26 Confirmation Candidate v1.00 — Independent Cold Audit — 2026-09-16

## Verdict

**PASS_TO_PREFLIGHT**

This is a static/cold-review verdict only. It does not claim execution success
on the target Windows machine and does not authorize opening confirmation market
payloads by itself.

## Reviewed candidate

- preregistration:
  - R26_XAU_OPENING_RANGE_REVERSAL_PLAN_2026_09_16.md
- confirmation engine:
  - xau_r26_confirmation_v1_00.py
- synthetic tests:
  - test_xau_r26_confirmation_v1_00.py
- reused sealed confirmation builder:
  - build_xau_m5_r21_confirmation_slice_v1_00.py
- reused builder tests:
  - test_build_xau_m5_r21_confirmation_slice_v1_00.py
- frozen event extractor:
  - xau_edge_discovery_r21_r25_v1_03.py::r24_comex_opening_range_breakout

Cold-review source state immediately before this audit document:
- main: c3677ca7227cff1ce59c5a81bbd5aa07e3900b73

## Scientific contract review

PASS.

R26 is a new research identifier, not a relabelled R24 success.

Frozen hypothesis:
- first close outside the completed 08:20-08:35 New York COMEX opening range
  tends to reverse against the breakout direction

Frozen primary metrics:
1. reversal_2b
2. reversal_4b

Frozen joint gate:
- reversal_2b mean > 0
- reversal_2b day-clustered t > +2.0
- reversal_4b mean > 0
- reversal_4b day-clustered t > +2.0

All conditions are required.

Descriptive only:
- reversal_1b
- reversal_8b
- reversal_16b
- all continuation horizons
- yearly sign stability

No descriptive horizon can rescue a failed 2b/4b primary gate.

## Independence disclosure review

PASS WITH DISCLOSED LIMITATION.

The confirmation period 2019-07-01 through 2024-12-31 was previously opened for
R21 confirmation. However the R21 executor computed R21 only. No R24/R26 event
extraction or confirmation statistic was computed or viewed before the R26
preregistration.

Accordingly:
- R26 confirmation outcomes remain unseen before preregistration;
- the confirmation period is not virgin-byte data;
- this limitation must remain attached to any R26 interpretation.

2025 remains unopened and is not used to compensate for this limitation.

## Frozen extractor identity review

PASS.

The R26 engine aliases the exact reviewed discovery extractor:

xau_edge_discovery_r21_r25_v1_03.r24_comex_opening_range_breakout

No R26-specific event-definition rewrite exists.

After extraction only, event metadata are relabelled:
- research = R26
- origin_research = R24

This metadata relabel does not alter event timing, direction, prices, returns or
statistics.

## Event-definition review

PASS.

The reused extractor preserves:
- America/New_York timezone
- opening-range bars 08:20, 08:25, 08:30
- range complete at 08:35
- first close outside range
- search 08:35 through 09:55 bar open
- 10:00 open excluded
- one event per New York day
- missing required bar before breakout invalidates the day
- reversal_h = -breakout_direction * forward_return_h

No breakout-distance, weekday, news, volatility or magnitude filter exists.

## Stage-sealing review

PASS.

R26 reuses the already-audited immutable confirmation builder from R21:
- hard-coded start 2019-07-01
- hard-coded end 2024-12-31
- exactly 1,437 source days required
- exact first/last payload dates required
- 2025 payloads not selected/opened
- any 2026+ index row hard-fails

The R26 engine also reuses the audited R21 confirmation:
- R15 canonical-path/SHA admission
- full R15 pin-attestation validation
- exact builder-receipt validation
- generated M5 loader with absolute 300-second grid and frozen date window

## Output / rerun safety review

PASS.

Canonical output:
D:/MT5_Backtests/Research/Autonomous/r26_xau_confirmation_v100/confirmation.json

Canonical progress:
D:/MT5_Backtests/Research/Autonomous/r26_xau_confirmation_v100/progress.json

- final result written atomically
- existing final confirmation result causes hard refusal
- cleanup removes only R26 transient progress/temp artifacts
- receipts/logs are outside the cleanup surface

## Heartbeat review

PASS.

Progress covers:
- starting
- confirmation M1 -> M5 build
- M5 load
- R26 analysis
- serialization
- completion

The reused builder heartbeats first day, each 10 source days and final day.

## Synthetic test review

The test suite covers:
- exact frozen extractor identity
- exact sealed-builder module reuse
- strict joint gate PASS
- fail-closed behavior at mean=0, t=2.0 and undefined statistics
- upward breakout followed by reversal
- downward breakout followed by reversal
- correct reversal/continuation sign convention
- R26-only output and explicit R24 origin metadata
- 2025/2026 closed flags
- one-shot refusal when final result already exists
- canonical output/progress path confinement

The separate reused builder test suite covers:
- confirmation-only payload opening
- exact start/end boundary coverage
- non-confirmation payload rejection
- 2026 index hard-fail
- heartbeat callback operation

## Required preflight gate

Before R26 real confirmation is enabled, all must PASS on the same main commit:

1. orchestrator control-plane tests
2. test_xau_r26_confirmation_v1_00.py
3. test_build_xau_m5_r21_confirmation_slice_v1_00.py

Only after those exact-commit receipts exist may R26 confirmation r1 be enabled.

## Still prohibited

- 2025 pre-OOS
- 2026+
- horizon rescue using 8b/16b
- threshold/session/filter tuning
- PnL optimization
- Guardian integration
- live deployment
