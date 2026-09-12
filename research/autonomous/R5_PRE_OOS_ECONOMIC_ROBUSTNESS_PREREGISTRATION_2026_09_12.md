# R5 pre-OOS economic robustness preregistration — 2026-09-12

Status: FROZEN BEFORE EXECUTION

## Question

Do any of the 96 frozen R5 causal-next-open survivors remain economically credible when translated to first-available canonical raw-M1 execution references, overlap is removed chronologically, and the already-established E1 and STRESS cost profiles are applied on 2024/2025 only?

A PASS answers only this pre-OOS feasibility question. It is not an EA, is not final validation, and does not authorize protected 2026.

## Frozen upstream evidence

- R5 result: `strategy-factory-r5-causal-next-open`, 96 survivors.
- Exact R5 result SHA256: `81dd16fabf001025c4dc144035d538fa46fab2fc768ba237610e027af1c7d34e`.
- R5 post-result cold audit r3: `PASS_INTERPRETABLE`, 96 survivors, material semantic changes = 0, protected 2026 unopened.
- Cold-audit published artifact SHA256: `ee3847d5a2c5c81b7cfb51290fa96d170c8e7fd4ac976d0bfca3cc03908fd628`.

No R5 rule, threshold, direction, horizon, session gate, dataset choice, or survivor membership may be changed in this screen.

## Admitted market inputs

Exactly these Phase I-B files are admitted, and their hashes are frozen:

- `xauusd_m1_2024_2025_raw.csv` — `f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445`
- `xauusd_m1_2024_2025_news_clean.csv` — `b116c61d0be7d73c455f4a4f897efdf0bf77a2b88594ed4b93ebee0d707570ee`
- `xauusd_m5_2024_2025_raw.csv` — `ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66`
- `xauusd_m5_2024_2025_news_clean.csv` — `972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503`

Any file containing a timestamp on or after `2026-01-01T00:00:00Z`, any hash mismatch, unexpected dataset, or unexpected survivor count is a hard infrastructure/data failure before scientific interpretation.

## Execution semantics

For each frozen survivor:

1. Rebuild its signal on its original frozen source dataset using the R5 feature/rule implementation.
2. A signal is known only after source bar `t` closes.
3. Entry is the first canonical raw-M1 open at or after that source-bar close.
4. The frozen horizon is counted in source bars. Exit availability is the corresponding source horizon boundary, resolved to the first canonical raw-M1 open at or after it.
5. Signal/entry/exit must remain inside the same calendar year and strictly before protected 2026.
6. Enforce one position at a time per candidate. While a trade is active, later signals for that same candidate are ignored. Exit processing precedes a new signal at an equal timestamp.
7. No stop, take-profit, trailing, sizing optimization, or other money-management rescue is introduced.

These conventions are inherited from the prior frozen economic-feasibility framework and the R5 causal cold audit; they are reject-only.

## Frozen costs

Reuse the established R4 pre-OOS economic profiles without retuning:

- E1: commission rate `0.000007` per modeled price leg, half-spread `0.0002 / 2`, slippage `0.0001` per side.
- STRESS: commission rate `0.000014` per modeled price leg, half-spread `0.0005 / 2`, slippage `0.0002` per side.

For direction `d`, entry open `oe`, exit open `ox`, and `f = half_spread + slippage`:

- modeled entry = `oe * (1 + d*f)`
- modeled exit = `ox * (1 - d*f)`
- net = directional gross - spread cost - slippage cost - commission.

No cost parameter may be changed after results are known.

## Frozen reject-only pass gate

The pass gate intentionally reuses the prior R4 economic-feasibility criteria rather than selecting new thresholds after seeing R5.

For each candidate:

- executable trades: >=100 in 2024, >=100 in 2025, >=40 in 2025 H1, >=40 in 2025 H2;
- E1 net PnL > 0 in 2024, 2025, 2025 H1, and 2025 H2;
- STRESS net PnL > 0 in 2024 and 2025;
- 2025 STRESS net PnL remains > 0 after removing the single best positive trade.

A candidate PASS requires every gate above. A candidate failing any gate is rejected; there is no same-sample repair.

The phase PASS means at least one of the 96 frozen candidates passes all gates. Phase FAIL means none do. Either outcome is scientifically interpretable if provenance/integrity checks pass.

## Outputs

Publish:

- phase summary with counts and frozen hashes;
- one diagnostics JSON and CSV row per frozen survivor;
- exact failure reasons for every rejected survivor;
- signal/overlap/boundary accounting;
- E1 and STRESS metrics for 2024, 2025, 2025 H1 and 2025 H2;
- explicit `protected_2026_opened=false`.

## Protection / next decision

Protected 2026 is forbidden in this phase. A PASS does not automatically open it. Any later protected-OOS action requires a separate committed preregistration and, under the current owner instruction, explicit owner approval before first inspection.
