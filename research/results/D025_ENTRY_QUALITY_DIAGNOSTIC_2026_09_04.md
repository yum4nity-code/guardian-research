# D025 entry-quality diagnostic — 2026-09-04

Source: user-supplied MT5 CSV exports from `D025_LER_Trading_1_01` on FundedNext, BTCUSD and ETHUSD, 2025-01-01 -> 2026-06-28, M1.

## Scope

This diagnostic does **not** judge the 48h no-TP trade construction. It asks a narrower question: after a D025 `VALID_SIGNAL` entry, how often did price reach +1R, +2R, +3R, +4R, or +5R **before** the structural SL was touched?

The CSVs contain 399 opened trades total: 230 BTCUSD and 169 ETHUSD. Outcomes contain the five horizons (1H, 4H, 8H, 24H, 48H) for every trade. The final 48H row was used only as the cumulative holder of hit timestamps. A +R threshold counts as successful only when its hit timestamp is non-zero and is strictly earlier than `stop_utc`, or when no stop occurred within the observed 48h.

Important limitation: MFE/MAE fields continue updating after a stop because the research tracker remains active until 48h. Therefore raw 48H MFE/MAE are **not valid pre-stop excursion measures** and are not used here to judge entry quality.

## Overall threshold hits before structural SL

| Symbol | Trades | +1R before SL | +2R before SL | +3R before SL | +4R before SL | +5R before SL | SL touched within 48h |
|---|---:|---:|---:|---:|---:|---:|---:|
| BTCUSD | 230 | 102 (44.35%) | 56 (24.35%) | 30 (13.04%) | 16 (6.96%) | 10 (4.35%) | 166 (72.17%) |
| ETHUSD | 169 | 60 (35.50%) | 33 (19.53%) | 23 (13.61%) | 14 (8.28%) | 10 (5.92%) | 115 (68.05%) |

No `ambiguous_same_m1=YES` case was present in these 399 trades.

## First-touch view: target vs SL

This excludes trades that reached neither the target nor the SL within the observation window.

| Symbol | Target | Target first | SL first | Unresolved | Target-first rate among resolved |
|---|---|---:|---:|---:|---:|
| BTCUSD | +1R | 102 | 118 | 10 | 46.36% |
| BTCUSD | +2R | 56 | 148 | 26 | 27.45% |
| BTCUSD | +3R | 30 | 160 | 40 | 15.79% |
| ETHUSD | +1R | 60 | 93 | 16 | 39.22% |
| ETHUSD | +2R | 33 | 108 | 28 | 23.40% |
| ETHUSD | +3R | 23 | 110 | 36 | 17.29% |

Interpretation: the entries are **not useless**. A large fraction reaches +1R before the structural stop, especially BTC. However, a naive full-position TP=1R / SL=1R construction would still be below the ~50% pre-cost break-even level overall, and the +2R/+3R first-touch rates are also below their simple one-shot break-even thresholds. This does not rule out partial-profit/runner or sub-1R management; it only says the raw entry stream is not sufficient by itself for a simple symmetric target/stop system.

## Validation path diagnostics

| Symbol | Path | N | +1R before SL | +2R before SL | +3R before SL |
|---|---|---:|---:|---:|---:|
| BTCUSD | ACCEPTANCE | 128 | 54.69% | 32.81% | 17.19% |
| BTCUSD | RETEST | 102 | 31.37% | 13.73% | 7.84% |
| ETHUSD | ACCEPTANCE | 87 | 28.74% | 17.24% | 11.49% |
| ETHUSD | RETEST | 82 | 42.68% | 21.95% | 15.85% |

The path effect reverses by symbol: BTC ACCEPTANCE is much stronger than BTC RETEST, while ETH RETEST is stronger than ETH ACCEPTANCE. This is a diagnostic observation only; it must not be converted into symbol-specific tuning without a new preregistered hypothesis and independent validation.

## Level-family diagnostics

Notable raw observations:
- BTC PDH: 14 trades, 85.71% reached +1R before SL, but the sample is small and only 14.29% reached +2R.
- BTC H4_SWING_HIGH: 16 trades, 62.50% reached +1R and 50.00% reached +2R before SL.
- ETH H4_SWING_LOW: 12 trades, 58.33% reached +1R and 41.67% reached +2R before SL.
- Several other level families are materially weaker.

These are subgroup diagnostics, not permission to cherry-pick a profitable subset post hoc.

## Verdict

- `D025 ENTRY QUALITY`: **NOT REJECTED / MIXED / WORTH FURTHER EXIT-AND-FIRST-TOUCH STUDY**.
- `D025 Trading 1.01 48H no-TP construction`: **REJECTED**.
- The current CSVs prove that the previous final-balance result materially understates entry quality because many trades reached favorable R thresholds before later hitting the structural SL or being closed at 48h.
- The next clean experiment should keep the entry rules frozen and test a **small preregistered set of exit constructions**, not retune the entry thresholds. The highest-value missing measurement is +0.5R first-touch because the current logger starts at +1R.

Suggested next research step: add +0.5R timestamp tracking only, keep the exact entry logic frozen, and compare a tiny predefined exit set such as full TP 0.5R, full TP 1R, and one partial-at-1R + runner construction. Do not run a broad optimization grid.
