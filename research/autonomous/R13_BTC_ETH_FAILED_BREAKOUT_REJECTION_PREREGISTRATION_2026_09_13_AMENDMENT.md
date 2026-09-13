# R13 BTC/ETH Failed-Breakout Rejection — preregistration amendment

Date: 2026-09-13
Status: frozen before corrected rerun
Applies to: `r13_btc_eth_failed_breakout_rejection_v1_01.py`

R13 v1.00 used economic cost gates inside discovery and confirmation, conflicting with the already-established staged architecture in `DISCOVERY_GATE_ARCHITECTURE_V1.md`. This amendment restores the intended chain: gross phenomenon discovery -> independent gross confirmation -> downstream economic robustness -> frozen 2025 pre-OOS -> protected 2026 final OOS.

This is a protocol-restoration rerun, not a rescue or parameter retune. The exact original 72 R13 definitions remain fixed. R13 v1.00 remains immutable historical evidence of a protocol-nonconforming run and must not be overwritten.

## Frozen signal family

Exact grid remains: BTCUSDT/ETHUSDT; channel hours 24/72/168; penetration 0.00/0.05; re-entry 0.00/0.10; hold 3/6/12 hours. Total 72 definitions.

Strict sweep semantics remain unchanged: upper failed breakout/short requires decision high > H + penetration*R and close <= H - reentry*R; lower failed breakout/long requires decision low < L - penetration*R and close >= L + reentry*R. Two-sided bars are rejected. Entry is next H1 open; exit is the H1 open exactly hold-hours later; one-position replay and gap/year-crossing rejection remain unchanged.

## Stage 1 — discovery 2018-2022

E1 and STRESS are diagnostic only. Across all 72 definitions compute gross p-values and BH-FDR q-values. Pass only if n>=75, gross mean>0, at least 3/5 years have positive gross net sum, and BH q<=0.05. Freeze IDs/SHA before confirmation.

## Stage 2 — confirmation 2023-2024

No retuning. Pass only if n>=25, gross mean>0, 2023 gross net sum>0, 2024 gross net sum>0, and BH q<=0.05 across frozen discovery survivors. E1/STRESS are not confirmation selectors. Freeze IDs/SHA before economic robustness.

## Stage 3 — economic robustness

Only independently confirmed definitions enter. Pass only if E1 mean>0 and STRESS mean>0 on frozen 2023-2024 confirmation trades. E1 round-trip cost=0.001; STRESS=0.002. Freeze IDs/SHA before 2025.

## Stage 4 — 2025 pre-OOS

Pass only if n>=10, E1 mean>0, STRESS mean>0, H1 E1 net sum>0, H2 E1 net sum>0, STRESS net sum after removal of the best STRESS trade>0, and largest positive STRESS trade / total positive STRESS PnL <=0.35.

## Mandatory auditability

Persist a full 72-definition discovery diagnostic ledger and funnel: tested -> enough_n -> gross_positive -> gross_stability -> discovery_fdr -> discovery_pass -> confirmation_pass -> economic_pass -> preoos_survivors.

## Protected 2026

2026 remains unopened. Reject any filename containing `2026` and any row timestamp >= 2026-01-01 UTC. No 2026 information may affect this corrected rerun.
