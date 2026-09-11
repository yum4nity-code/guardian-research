# R5 causal next-open preregistration — 2026-09-11

Status: FROZEN BEFORE EXECUTION

## Motivation

R4 is closed because its close-to-close objective captured price movement that was not available after the source bar closed. R5 is a new discovery family whose outcome representation is causal by construction. It does not reuse or retune R4 survivors.

## Data boundary

- Allowed: canonical pre-2026 Phase I-B XAUUSD CSVs only.
- Discovery year: 2024.
- Independent confirmation year: 2025.
- Protected 2026: forbidden; no file containing known 2026/OOS markers may be inspected, and any loaded input containing a timestamp >= 2026-01-01 must be rejected.

## Signal and execution semantics

- Features at bar t may use information through the close of bar t only.
- Signal becomes available after bar t closes.
- Earliest entry proxy: open of the next available bar t+1.
- For horizon h, exit proxy: open of bar t+h+1.
- Return: direction * (exit_open - entry_open) / ATR(t).
- Signal, entry and exit must remain inside the same calendar year; cross-year outcomes are purged.

## Frozen search space

- Feature families: lagged returns 1/3/6/12/24/48, normalized range/body/wicks, RSI7/14, SMA distance 5/10/20/50/100, ATR regime, hour/day-of-week, volume z-score when present.
- Tail quantiles: 5%, 10%, 20%, 30% lower/upper tails.
- Horizons: 1, 3, 6, 12, 24, 48 bars.
- Directions: long and short.
- Optional session gates: 35% probability; start hour 0-23; width 2/4/6/8 hours.
- Trials: 150,000.
- Seed: 260914.
- Thresholds are fit on 2024 only.

## Discovery gate — 2024

Selected-vs-session-complement conditional edge must exceed 0.02 ATR with fast two-sample p < 0.01 and at least 100 selected and baseline observations.

## Confirmation gate — untouched 2025

- Full-year conditional edge > 0.015 ATR.
- All four calendar quarters positive with minimum 30 selected/baseline observations per quarter.
- HAC significance calculated with lag max(48, 2*h).
- Benjamini-Hochberg FDR q <= 0.05 across all 2024 discovery candidates tested in 2025.
- Adjacent same-tail quantile stress: at least one neighboring threshold, also fit only on 2024, must retain > 0.0075 ATR edge in 2025.

## Interpretation

A PASS is only a causal gross-return discovery/confirmation survivor. It is not an EA and does not authorize protected 2026. Survivors must still undergo reject-only consolidation/robustness and realistic cost/execution feasibility before any protected-OOS request.

## Preflight requirement

The deterministic synthetic test `test_strategy_factory_causal_next_open_v1_00.py` must PASS before the R5 factory job is allowed to execute. The test verifies next-open semantics, direction inversion, calendar-boundary purging, rule masking and BH behavior without reading market data.
