# Guardian Shared Intelligence Service — architecture proposal

Date: 2026-09-04
Status: DESIGN / NOT YET IMPLEMENTED

## Motivation

Guardian may run simultaneously on several MT5 terminals/accounts and, during research, on several tester instances. External market intelligence is account-independent: BTC/ETH spot/perp, open interest, funding and liquidation data should not be fetched and recomputed independently by each Guardian instance.

The target architecture is one shared local intelligence service per machine, consumed read-only by all Guardian instances.

## Core principle

Separate market intelligence from broker/account execution.

- Shared service: collects and transforms external market data once for the whole machine.
- Guardian instance: keeps account-specific execution, prop-firm compliance, risk, margin, broker prices, SL/TP and emergency protections.
- External intelligence can influence strategy context only. It must never be required for Guardian protection/compliance to function.

## Proposed layers

### 1. Raw External Data Collector

Single process per PC.

Inputs initially:
- BTC/ETH spot price;
- BTC/ETH perpetual price;
- open interest;
- funding;
- long/short liquidations;
- provider/source timestamps and health.

Responsibilities:
- provider adapters;
- reconnect/deduplication;
- timestamp normalization;
- raw daily append-only archive;
- health/staleness.

This is the current Guardian EIB V1 direction.

### 2. Shared Intelligence Engine

Single process per PC, fed by the raw collector.

It computes neutral, reusable market facts rather than strategy BUY/SELL decisions.

Candidate features:
- spot return over 1m/5m/15m/1h;
- perpetual return over the same horizons;
- spot/perp basis and return dislocation;
- open-interest deltas and standardized shocks;
- long/short liquidation sums over rolling windows;
- liquidation z-scores;
- liquidation-to-price-impact ratios;
- funding level/change;
- data quality, age and source availability;
- optional explicit market regimes such as NORMAL / LEVERAGED / DELEVERAGING / LIQUIDATION_SHOCK / DISLOCATED, only after research defines them.

Important: strategy-specific interpretation remains in each strategy. Example: a DELEVERAGING state may be favourable context for RSI/LER but a veto or caution flag for Momentum.

Do not produce an opaque global "AI BUY score".

### 3. Local Shared State / IPC

All Guardian instances consume a compact latest-state snapshot instead of raw external history.

Initial robust implementation preference:
- atomic local snapshot files in a shared directory;
- one compact state per symbol or one global snapshot;
- monotonic `generation_id`;
- `available_at_ms`, `computed_at_ms`, source ages and quality flags included;
- Guardian caches the latest generation and only reparses when it changes.

This is simpler to audit and reproduce than direct API calls from every EA.

A later production version may replace or supplement files with Windows named pipes/shared memory/local IPC if measurement shows a need. Local HTTP/WebRequest should not be the only mechanism because it complicates Strategy Tester reproducibility and introduces MT5 allow-list/dependency concerns.

## Live architecture

```text
Public market feeds
        |
        v
ONE Raw Collector
        |
        v
ONE Shared Intelligence Engine
        |
        v
Atomic local market-state cache
   |        |        |        |
   v        v        v        v
Guardian  Guardian  Guardian  Guardian
FTMO      FundedNext  test/live ...
```

All accounts see the same external market facts. Each Guardian combines those facts with its own broker/account state.

## Backtest architecture

Live current-state IPC must never be used as historical truth during Strategy Tester runs.

For backtests:
1. raw external observations are archived with `available_at_ms`;
2. shared derived features are computed historically once and stored as a timestamped feature stream;
3. each tester instance reads the same immutable feature archive;
4. replay exposes only records with `available_at_ms <= simulated_time_ms`;
5. no live external service is required for deterministic historical tests.

This means five parallel Strategy Tester workers can share one precomputed feature dataset without each recomputing OI/liquidation/basis features.

## Expected efficiency gain

With N Guardian instances:
- external network connections stay approximately constant instead of multiplying by N;
- rolling-window calculations are done once instead of N times;
- raw archives are written once;
- all strategies/accounts receive consistent synchronized values;
- provider rate-limit/reconnect logic exists in one place;
- debugging and audit become substantially easier.

The cost for several Guardian consumers becomes primarily a tiny local snapshot read, which is negligible compared with duplicate external collection/calculation.

## Strategy use

### RSI Sniper
Possible future inputs after validation:
- OI collapse/deleveraging confirmation;
- liquidation shock;
- perp-vs-spot dislocation;
- data-quality veto.

### Momentum
Possible future inputs after validation:
- participation confirmation via OI;
- spot/perp agreement;
- liquidation-driven move warning;
- deleveraging/dislocation veto or down-weighting.

### D025 LER
External intelligence is a natural enrichment for:
- forced-liquidation intensity;
- OI unwind;
- declining price impact despite continued liquidation flow;
- perp/spot dislocation and normalization.

None of these uses are accepted into strategy production before event studies prove incremental value.

## Safety boundaries

- One intelligence service failure must not stop Guardian manual protection, risk, compliance or emergency exits.
- External state includes explicit OK/STALE/PARTIAL/DOWN quality.
- Guardian must never silently reuse stale values as current.
- No external provider credentials with trading permission.
- Shared service cannot submit MT5 orders.
- Broker/account-specific risk remains inside Guardian.

## Product direction

For a commercial Guardian release, this service should eventually be installed as a background component by the Guardian installer, auto-started, health-monitored and versioned independently from the EA when useful.

The end user should not manage Python, Git, PowerShell or provider adapters manually.

## Decision

Preferred architecture: **centralize external collection and reusable feature computation once per PC; keep strategy decisions and account risk inside each Guardian instance.**

Next implementation step after EIB V1 live smoke passes: prototype a compact shared `market_state_v1` snapshot and measure read/update behaviour with multiple Guardian/test consumers before introducing any strategy rule changes.
