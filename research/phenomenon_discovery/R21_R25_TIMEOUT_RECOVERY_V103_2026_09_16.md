# R21-R25 discovery timeout recovery — 2026-09-16

## Incident classification

R21-R25-XAU-DISCOVERY r4 and r5 did not produce scientific verdicts.

- r4 was killed by the orchestrator default 150-second timeout.
- r5 was killed by the explicitly configured 1800-second timeout.
- r5 receipt had empty stderr/stdout tails and protected_2026_untouched=true.
- The worker process was independently observed consuming CPU while executing
  xau_edge_discovery_r21_r25_v1_02.py.
- These receipts are infrastructure TIMEOUT evidence only. They are not FAIL
  verdicts for R21-R25 and must never be used as alpha evidence.

Audit receipts and logs are preserved.

## Recovery design

New immutable versions:

- build_xau_m5_discovery_slice_v1_02.py
- xau_edge_discovery_r21_r25_v1_03.py
- test_build_xau_m5_discovery_slice_v1_02.py
- test_xau_edge_discovery_r21_r25_v1_03.py

Scientific definitions, R15 pin, discovery window and protected-period doctrine are
unchanged.

The builder now exposes a progress callback every 10 source days plus first/last
day. The v1.03 engine writes an atomic canonical progress heartbeat:

D:/MT5_Backtests/Research/Autonomous/r21_r25_xau_v103/progress.json

The progress contract covers:

- starting/cleanup
- M1 -> M5 reconstruction
- M5 load
- R21 through R25 analysis
- serialization
- completion

The orchestrator timeout policy will point to that progress file. Reaching the
nominal adaptive time limit does NOT kill a process while the heartbeat remains
fresh. A kill is permitted only when both the adaptive limit has been exceeded
and the heartbeat has been stale for the configured interval.

## Cleanup doctrine

Before r6 starts, v1.03 removes only transient artifacts from interrupted local
R21-R25 attempts:

- stale discovery.json/progress.json in v1.02/v1.03 output directories
- stale temporary directories with exact prefixes guardian_r21r25_v102_ or
  guardian_r21r25_v103_

It deliberately preserves:

- orchestrator receipts
- logs
- published backtest-results evidence
- R15 source/index/manifests
- all protected data

## Safety state

No confirmation is authorized.
2025 remains inaccessible.
2026+ remains hard-sealed.
No Guardian/live integration is authorized.
