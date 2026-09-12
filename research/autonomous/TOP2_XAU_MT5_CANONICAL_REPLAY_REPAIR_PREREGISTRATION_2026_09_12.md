# Top-2 XAU MT5 canonical replay fidelity repair — preregistration

Date: 2026-09-12
Status: frozen infrastructure/fidelity repair

## Trigger

Generation 63 exact-parity audit scientifically failed. For frozen candidates R6B-347 and R6B-307, the completed generation-62 MT5 Strategy Tester trades had zero exact entry-time matches against the canonical Phase I-B/R6 schedules in both 2024 and 2025. Generation 62 is therefore descriptive-only and must not be used as execution-fidelity evidence.

## Frozen scientific hypothesis

No alpha hypothesis, parameter, direction, horizon, session, threshold, cost profile or candidate selection is changed.

- R6B-347: LONG, lookback 96 M5 bars, buffer 0.10 ATR, horizon 96 M5 bars, session 00:00-08:00 in the canonical Phase I-B server-time coordinate.
- R6B-307: LONG, lookback 96 M5 bars, buffer 0.00 ATR, horizon 48 M5 bars, session 00:00-08:00 in the canonical Phase I-B server-time coordinate.

The canonical schedule is recomputed only by the already committed `r6_xau_low_turnover_breakout_v1_00.py` from the hash-pinned Phase I-B inputs:

- `xauusd_m5_2024_2025_news_clean.csv` SHA256 `972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503`
- `xauusd_m1_2024_2025_raw.csv` SHA256 `f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445`

## Repair

The repaired MT5 harness MUST NOT recompute the R6 signal from tester bars. Python first regenerates the exact canonical 2024/2025 trade ledger and exports only the frozen entry/exit schedule. A tester-only MQL5 replay EA then executes that schedule on FundedNext XAUUSD M1 data. The EA may trade only when `MQL_TESTER` is true and the launch config keeps live trading disabled.

The canonical HCC datetime coordinate is retained directly as FundedNext server time, per the frozen Phase I-B recovery policy. No UTC/server offset adjustment is introduced.

## Window and protection

Allowed schedule/test window: 2024-01-01 00:00:00 through 2025-12-31 23:59:59 in the canonical server-time coordinate.

2026 is forbidden in this repair. The schedule generator must fail closed if any canonical schedule row is in 2026 or later. The Strategy Tester configuration must end at 2025-12-31.

## Pass/fail

Infrastructure replay PASS requires each candidate to produce a tester trade CSV and no tester-only guard violation.

Scientific fidelity PASS requires the existing exact canonical parity audit to report, for both candidates and both 2024 and 2025:

- tester trade count equals canonical trade count;
- every entry timestamp matches exactly;
- every entry/exit pair matches exactly.

Any mismatch is scientific/fidelity FAIL for this repaired harness. It does not justify changing R6 parameters. A failure may only trigger another infrastructure repair that preserves the same frozen schedules.

## Interpretation

A PASS establishes that FundedNext Strategy Tester can reproduce the frozen canonical timing schedule. It does not create a new alpha result, does not retune R6, and does not authorize production/live deployment.
