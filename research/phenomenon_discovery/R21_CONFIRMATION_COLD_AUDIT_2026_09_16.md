# R21 Confirmation Candidate v1.00 — Independent Cold Audit — 2026-09-16

## Verdict

**PASS_TO_PREFLIGHT**

This is a static/cold-review verdict only. It does not claim that the candidate
tests have executed on the target Windows machine, and it does not authorize
opening confirmation data by itself.

Real confirmation must remain disabled until the exact-main-commit preflights
below have all returned PASS.

## Reviewed candidate

- discovery freeze:
  - R21_R25_DISCOVERY_FREEZE_2026_09_16.md
- confirmation builder:
  - build_xau_m5_r21_confirmation_slice_v1_00.py
- confirmation engine:
  - xau_r21_confirmation_v1_00.py
- builder tests:
  - test_build_xau_m5_r21_confirmation_slice_v1_00.py
- engine tests:
  - test_xau_r21_confirmation_v1_00.py
- frozen source extractor:
  - xau_edge_discovery_r21_r25_v1_01.py::r21_comex_unconditional_drift

Cold-review source state immediately before this audit document:
- main: 839e707815fa859f423521e28e137281363fcc5b

## Scientific contract review

PASS.

R21 only is executable.

Frozen hypothesis:
- 08:20 America/New_York M5 close anchor
- unconditional forward close-to-close return
- primary horizon: 15 minutes
- primary sign: positive

Frozen confirmation gate:
- post_15m mean > 0
- post_15m day-clustered t > +2.0

Descriptive only:
- post_30m
- post_60m
- post_120m
- yearly sign stability

No descriptive metric can rescue a failed post_15m primary.

R22, R23, R24 and R25 are absent from the confirmation executor.

## Extractor identity review

PASS.

The confirmation wrapper does not reimplement the R21 event logic. It aliases:

xau_edge_discovery_r21_r25_v1_01.r21_comex_unconditional_drift

This is the same frozen R21 extractor used by the reviewed R21-R25 discovery
wrapper.

The confirmation test explicitly asserts object identity between the wrapper
extractor and the frozen discovery extractor.

## Stage-sealing review

PASS.

The confirmation builder has hard-coded immutable boundaries:
- 2019-07-01
- 2024-12-31

There are no start/end CLI arguments and no alternate stage mode.

The builder:
- selects only rows inside the frozen confirmation window
- checks the date gate again immediately before decode_day opens payload bytes
- requires exact first selected date 2019-07-01
- requires exact last selected date 2024-12-31
- requires exactly 1,437 source weekdays
- refuses any 2026+ index row
- reports confirmation_opened=true only on successful confirmation build
- reports pre_oos_2025_opened=false
- reports protected_2026_opened=false

Scanning pinned index metadata for 2025 is permitted; 2025 market payload bytes are
not selected or opened.

## R15 provenance review

PASS.

The engine admits only the canonical R15 index path and pinned SHA256:

d77fb76e5b5ee0600a488c331084e70972a8800a33ae59a957c1044dc39ef566

Before the builder receives the index, the engine also requires the persisted R15
attestation to match:
- status PASS
- phase r15-dukascopy-xauusd-boundary-union
- payload_count 5518
- eligible_boundary_days 5518
- known_missing_or_holiday_weekdays 0
- window 2004-11-08 through end_exclusive 2026-01-01
- protected_2026_opened false
- exact pinned index SHA256

The verified index bytes are copied to a private temporary snapshot before use.

## M5 / event-data integrity review

PASS.

Generated confirmation M5 rows must:
- be exactly M5
- lie on the absolute 300-second grid
- be strictly increasing
- remain inside the frozen confirmation window
- have finite positive OHLC and valid OHLC geometry

The builder also rejects non-increasing emitted epochs.

## Output / rerun safety review

PASS.

Canonical result:
D:/MT5_Backtests/Research/Autonomous/r21_xau_confirmation_v100/confirmation.json

Canonical heartbeat:
D:/MT5_Backtests/Research/Autonomous/r21_xau_confirmation_v100/progress.json

The result is written atomically.

If confirmation.json already exists, the engine refuses a scientific overwrite.
A completed confirmation therefore cannot be silently rerun and replaced.

Cleanup is limited to:
- progress.json
- progress.json.tmp
- confirmation.json.tmp
- exact-prefix R21 confirmation temporary directories

Receipts/logs are outside this cleanup surface.

## Heartbeat review

PASS.

The builder reports progress at:
- first source day
- every 10 source days
- last source day

Later phases report:
- load_m5
- analyze_R21
- serialize
- complete

The progress artifact distinguishes authorization from actual opening:
- confirmation_authorized=true
- confirmation_opened=false at starting
- confirmation_opened=true only after confirmation payload processing begins

## Test review

The synthetic suites cover:
- exact reuse of the frozen R21 extractor
- primary gate PASS and fail-closed boundary behavior
- rejection of 2025 rows by the confirmation loader
- rejection of off-grid M5 rows
- rejection of a receipt claiming a 2025 payload
- confirmation-only pipeline behavior
- full R15 attestation requirements
- refusal to overwrite an existing scientific result
- canonical output/progress confinement
- builder opening only confirmation payloads
- exact confirmation boundary coverage
- explicit rejection of non-confirmation payload dates
- hard failure on a 2026 index row
- progress callback operation

During cold review, the builder test was found inconsistent after exact-boundary
hardening because its synthetic fixture contained only the start boundary. That
test defect was corrected before this verdict by adding the 2024-12-31 boundary.

## Required preflight gate

Before real confirmation is enabled, all must PASS on the same main commit:

1. orchestrator control-plane tests
2. test_xau_r21_confirmation_v1_00.py
3. test_build_xau_m5_r21_confirmation_slice_v1_00.py

Only after those exact-commit receipts exist may R21 confirmation r1 be enabled.

## Still prohibited

- 2025 pre-OOS
- 2026+
- R22/R23/R24/R25 confirmation
- post-result filter or horizon rescue
- PnL optimization
- Guardian/live integration
