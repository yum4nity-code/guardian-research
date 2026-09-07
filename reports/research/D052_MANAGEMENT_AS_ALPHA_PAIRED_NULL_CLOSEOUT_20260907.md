# D052 — Management-as-Alpha Paired Null-Entry Lab V0 — Closeout

Date: 2026-09-07 Europe/Paris
Status: **CLOSED — NO MANAGEMENT ALPHA IN FROZEN FAMILY**

## Formal result

Authoritative development event:
`backtests/d052/live/events/development/d052-development-score/20260907T152924Z`

Formal status:
`D052_NO_MANAGEMENT_ALPHA_IN_FROZEN_FAMILY`

Passing candidates: **0 / 11**
Selected candidate: **none**
Jul-Aug 2026 holdout: **UNOPENED**
Integrity events: **0**

## Reference null-entry economics

Reference management `REF_EOD_NO_STOP` on the paired direction-neutral null entries:
- n = 12,318 virtual legs
- mean = -0.0266264853R/leg
- total = -327.98504593R
- PF = 0.8790507722

The null-entry construction was intentionally direction-neutral: the same deterministic price-independent event opened simultaneous virtual LONG and SHORT sleeves, so a management rule had to overcome spread/cost/path effects without directional entry information.

## Frozen candidate family

Eleven preregistered management candidates were evaluated on exactly the same paired entry events:
- SL1_EOD
- SL1_TP1
- SL1_TP2
- SL1_TP3
- SL1_BE_AFTER_1R_EOD
- SL1_BE_AFTER_2R_EOD
- SL1_P50_AT_1R_BE_REST
- SL1_P40_AT_2_5R_BE_REST
- SL1_TRAIL1_AFTER_1R
- SL1_TRAIL1_5_AFTER_2R
- SL1_P50_AT_1R_TRAIL1_REST

None passed the frozen all-required gates.

## Best descriptive candidate is still negative

The least-negative candidate by aggregate mean was `SL1_BE_AFTER_1R_EOD`:
- n = 12,318
- mean = -0.0249931593R/leg
- total = -307.86573628R
- stress total = -357.25723913R
- PF = 0.8847298470
- LONG mean = -0.0122215542R
- SHORT mean = -0.0377647644R
- 2024 total = -168.34915444R
- 2025 total = -139.51658184R
- paired delta versus reference = +0.0016333260R/leg, +20.11930965R total
- absolute month-block bootstrap 95% interval = [-0.0299984896R, -0.0198765062R] around the mean
- paired-delta month-block bootstrap 95% interval = [-0.0029910883R, +0.0064052229R]

Interpretation: management produced a small descriptive reduction in losses versus the no-stop reference, but the candidate remained economically negative and its incremental lift was not robustly above zero.

## Scientific conclusion

D052 rejects the strong claim that a generic mechanical management rule from this frozen family can manufacture robust positive expectancy from an entry with no directional information.

The evidence supports a narrower statement:
- management can reshape the distribution and may modestly reduce losses;
- management does not remove the need for entry/context alpha;
- if a management rule ever creates positive expectancy from a null entry, that rule itself must encode exploitable information about future path, and D052 found no such robust rule among the eleven tested.

This conclusion is consistent with prior Guardian evidence:
- D041 showed a sophisticated manager materially degraded the already-confirmed D032 entry edge versus its +24h reference;
- Management Benchmark V1/V2 found no universal management promotion across several strategy families.

## Decision

- Close D052 V0 permanently.
- Do not open the Jul-Aug 2026 holdout because no DEV candidate passed all frozen gates.
- Do not promote a "best loser".
- Do not retune thresholds or drop losing symbols after seeing D052.
- Return research priority to **entry/context alpha**, while preserving management as risk/execution engineering rather than assuming it can rescue arbitrary signals.

## Provenance

Frozen source normalized SHA256:
`009a4bc7a5995d5d766fe6b5bec7d61b486e88d61fad0d75b29b227fb6098275`

Preregistration Git blob:
`faa986bb7460806ccc7b5423ba8a697f7569de8e`

Source Git blob:
`98ca64ebe2c8e21f2579e9f4cc804b8848d6325b`

Legacy AutoSync was not used.
