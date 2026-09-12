# R7 pre-OOS economic robustness preregistration — 2026-09-12

Status: FROZEN BEFORE EXECUTION

## Question

Do any of the eight frozen R7 long-history causal-factory survivors remain economically credible when translated into non-overlapping fixed-notional trades and subjected to conservative cost sensitivity across the complete pre-OOS history, without opening protected 2026?

A PASS answers only this reject-only pre-OOS feasibility question. It is not an EA, does not prove broker-specific executability, and does not authorize protected 2026.

## Frozen upstream evidence

- Phase: `r7-long-history-causal-factory`.
- Scientific status: PASS with 8 pre-OOS survivors after 2017-2022 discovery, frozen 2023-2024 confirmation, and frozen 2025 pre-OOS gate.
- Exact published result SHA256: `aeafdf64cb1d8e60b42fb6e1e3b872fcfcf40949410c0b456f895c250d949b1c`.
- Frozen discovery IDs SHA256: `2615b8c89bc091ee59b17132e76df2a026b7597f18d5597ee8ce1f8f650b3811`.
- Frozen confirmation IDs SHA256: `312746af153ac96ddb71204df4fd52616bf884c516abd1b970d8cd51e05dbe92`.
- Protected 2026 was untouched upstream.

No candidate membership, feature, threshold, direction, timeframe, horizon, session gate, execution timing, or upstream selection criterion may be changed in this screen.

## Frozen market inputs

Exactly these official-history files are admitted:

- `BTCUSDT_spot_5m_2017_2025.csv` — SHA256 `75d0d48dcfa7e649192d1eb2c96e89a591aa49bcfac11d394a1f84113264f6e8`
- `ETHUSDT_spot_5m_2017_2025.csv` — SHA256 `21b170675eae6bd2e3d442391e2acb9392abdff443f517b5cb0ee1946a12aa13`

Any hash mismatch, any timestamp on or after `2026-01-01T00:00:00Z`, an unexpected survivor count, or a mismatch in the frozen upstream result hash is an infrastructure/provenance failure before scientific interpretation.

## Execution semantics

For every frozen candidate:

1. Rebuild its original M15/H1 bars and features from the admitted 5-minute file using the frozen R7 implementation.
2. A signal is known only after source bar `i` closes.
3. Entry is source bar `i+1` open; exit is source bar `i+h+1` open for the frozen horizon `h`.
4. Reject any path crossing a data gap, calendar-year boundary, end of available data, or protected 2026.
5. Enforce one position at a time per candidate. While a trade is active, later signals are ignored. Exit processing precedes a new entry at an equal timestamp.
6. Use fixed notional return accounting. No sizing, stop, take-profit, trailing, compounding optimization, or money-management rescue is introduced.

## Frozen cost sensitivity

Because R7 uses official Binance spot history as a discovery/confirmation research feed rather than a final broker execution feed, this phase uses deliberately simple all-in one-way cost sensitivities rather than pretending to know a future broker-specific spread:

- E1: 5 basis points per side (`0.0005` fractional return per side; 10 bps round trip).
- STRESS: 10 basis points per side (`0.0010` fractional return per side; 20 bps round trip).

For every trade:

`gross_return = direction * (exit_open / entry_open - 1)`

`net_return(profile) = gross_return - 2 * one_way_cost(profile)`

These profiles are reject-only research hurdles. They may not be reduced after results are known. Broker/prop-firm fidelity remains a later gate for any survivor.

## Frozen diagnostics

For each candidate, record at minimum:

- executable trade count and ignored-overlap count;
- yearly metrics for 2018-2025;
- 2025 H1/H2 metrics;
- aggregate discovery 2018-2022, confirmation 2023-2024, and pre-OOS 2025 metrics;
- E1 and STRESS net return sums, means, win rates, best/worst trade, cumulative-return max drawdown;
- monthly E1/STRESS sums and rolling 6/12-month sums over 2018-2025;
- best-trade concentration and 2025 STRESS net after removing the single best trade;
- explicit protected-data status and exact input/upstream hashes.

## Frozen reject-only pass gate

A candidate PASS requires every condition below:

1. executable trades >=100 in each of 2023, 2024 and 2025;
2. executable trades >=40 in each 2025 half-year;
3. at least 4 of the 5 full discovery years 2018-2022 have E1 net sum >0;
4. aggregate 2018-2022 STRESS net sum >0;
5. E1 net sum >0 separately in 2023, 2024 and 2025;
6. STRESS net sum >0 separately in 2023, 2024 and 2025;
7. E1 net sum >0 in both 2025 H1 and 2025 H2;
8. 2025 STRESS net sum remains >0 after removing the single best trade.

No monthly/rolling/drawdown diagnostic is used to tune or rescue a failure. They are characterization evidence for later decisions.

Phase PASS means at least one of the eight frozen candidates passes all gates. Phase FAIL means none do. Either result is scientifically interpretable if provenance/integrity checks pass.

## Protection and next decision

Protected 2026 is forbidden in this phase. If zero candidates pass, close R7 without rescue. If candidates pass, freeze/deduplicate the exact finalists, perform a cold red-team review, and only then preregister any protected-2026 test. Under the owner's current instruction, protected 2026 must not be opened without explicit owner approval plus committed preregistration.
