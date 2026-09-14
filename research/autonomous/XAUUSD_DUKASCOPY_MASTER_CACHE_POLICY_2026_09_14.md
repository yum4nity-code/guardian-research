# XAUUSD Dukascopy M1 master-cache reuse policy

Date: 2026-09-14
Status: CANONICAL DATA-REUSE POLICY

## Purpose

The ongoing R15 Dukascopy acquisition is expensive in wall-clock time. The downloaded source payloads must therefore be treated as a reusable historical XAUUSD source rather than as disposable R15-only input.

## What is actually downloaded

For each requested weekday from 2004-11-08 through 2025-12-31, Guardian downloads the complete Dukascopy XAUUSD BID **M1 daily candle payload** (`BID_candles_min_1.bi5`).

R15 itself only needs four exact New York boundary opens per eligible day:
- 11:30
- 12:00
- 15:30
- 16:00

The R15 compact CSV therefore stores only those four boundary observations, but the full compressed daily M1 payload remains cached locally under the acquisition cache.

This is **not** an M15-only download.

## Reuse rule

Once the acquisition completes, the existing cached daily `.bi5` payloads become the preferred historical XAUUSD source for future Guardian research covering the same dates.

Future XAU research must:
1. reuse the cached source payloads before attempting any remote redownload;
2. derive any required M5/M15/M30/H1/H4/D1 bars locally from M1 where scientifically appropriate;
3. preserve original payload SHA256 provenance;
4. never overwrite or mutate the original cached `.bi5` payloads;
5. create study-specific derived datasets beside the source cache rather than modifying source data;
6. document aggregation semantics explicitly (timezone, bar boundary, OHLC construction, missing-bar policy);
7. keep protected 2026 excluded unless a separately preregistered final-OOS step explicitly authorizes it.

## Canonical location

Current acquisition root:
`D:\MT5_Backtests\Research\Autonomous\r15_dukascopy_xauusd_v1\`

Current source payload cache:
`D:\MT5_Backtests\Research\Autonomous\r15_dukascopy_xauusd_v1\payload_cache\`

The directory name remains historical provenance from R15. Do not rename or move it while acquisition is running.

After completion, register it through:
`research/autonomous/register_xauusd_dukascopy_master_cache_v1_00.py`

The registration step is read-only with respect to the cached payloads and writes a master-cache manifest that future research can reference.

## Scientific caution

Reuse of the same source data across multiple studies does not make those studies independent. Each strategy/phenomenon still requires its own preregistration, chronology, multiple-testing control where applicable, confirmation logic, cost/execution stage and protected-OOS discipline.
