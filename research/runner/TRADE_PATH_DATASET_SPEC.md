# Guardian Trade Path Dataset Contract v1

## Purpose

Every validated strategy backtest should become reusable research data, not just a final P/L number.

This contract defines the intratrade path fields future Guardian research harnesses should emit so that exit-management research can be performed later without changing the original entry-strategy verdict.

The frozen experiment decision score remains authoritative. Trade-path analytics are descriptive only until a separate exit-management hypothesis is preregistered and tested.

## Scientific boundary

Three layers must remain separate:

1. **Entry edge** — does the frozen entry strategy pass its preregistered gates?
2. **Trade path** — what happens after entry, measured without changing the trade?
3. **Exit Lab** — new preregistered experiments testing SL/TP/BE/trailing/runner/time-stop rules against saved path data or fresh harness runs.

A rejected entry experiment may still contribute descriptive trade-path data. Its verdict must never be changed post hoc because an attractive exit rule is discovered later.

## Required identifiers

One row per completed trade, with a stable trade identifier:

- `experiment_id`
- `source_version`
- `source_sha256`
- `stage`
- `symbol`
- `trade_id`
- `broker_day_key`
- `side`
- `entry_time`
- `exit_time`
- `entry_price`
- `initial_stop`
- `initial_risk_price`
- `initial_risk_money`
- `exit_reason_original`
- `gross_r_original`
- `net_r_original`

## Required intratrade path metrics

These fields must be measured during the original backtest from executable-side prices and the original initial risk denominator:

- `mfe_r` — maximum favorable excursion in R before original exit;
- `mae_r` — maximum adverse excursion in R before original exit;
- `mfe_time` — broker timestamp of MFE;
- `mae_time` — broker timestamp of MAE;
- `time_to_mfe_minutes`;
- `time_to_mae_minutes`;
- `max_retracement_from_mfe_r` — largest giveback from achieved MFE before original exit.

## R milestone first-touch fields

For each level `0.5R`, `1R`, `2R`, `3R`, `5R`:

- `reached_<level>` boolean;
- `first_touch_<level>_time` nullable timestamp;
- `time_to_<level>_minutes` nullable number.

Minimum canonical names:

- `reached_0_5r`
- `time_to_0_5r_minutes`
- `reached_1r`
- `time_to_1r_minutes`
- `reached_2r`
- `time_to_2r_minutes`
- `reached_3r`
- `time_to_3r_minutes`
- `reached_5r`
- `time_to_5r_minutes`

## Adverse-before-favorable diagnostics

For each favorable milestone reached, record the worst adverse excursion observed before first touch when practical:

- `mae_before_0_5r`
- `mae_before_1r`
- `mae_before_2r`
- `mae_before_3r`
- `mae_before_5r`

These fields are especially useful for studying initial-stop width without selecting an SL by visual curve fitting.

## Post-milestone giveback diagnostics

When practical, record:

- `min_r_after_first_1r_before_exit`
- `min_r_after_first_2r_before_exit`
- `min_r_after_first_3r_before_exit`
- `max_r_after_first_1r_before_exit`
- `max_r_after_first_2r_before_exit`
- `max_r_after_first_3r_before_exit`

These allow questions such as:

- how often does a trade touch +2R and then finish below +1R?
- after +1R, how often is +3R subsequently achieved?
- how much open profit is typically surrendered before the original exit?

## Optional bar-path storage

Do **not** publish full tick/bar paths to GitHub by default.

If a future Exit Lab requires exact replay, the local PC may retain a compressed per-trade bar-path file. GitHub should receive only:

- file SHA256;
- byte size;
- row count;
- schema version;
- local evidence identifier.

Compact path summaries remain publishable.

## Price convention

All path metrics must use the same executable-side convention as the original frozen strategy:

- long favorable/adverse calculations use executable sell-side exit prices;
- short favorable/adverse calculations use executable buy-side exit prices;
- spread assumptions must not silently differ from the original harness;
- initial R denominator is frozen at original entry time and never recomputed from a later hypothetical stop.

## Ambiguous intrabar touches

If the tester model cannot determine the order of two relevant levels touched inside the same bar, the harness must explicitly flag ambiguity rather than infer an optimistic sequence.

Recommended fields:

- `path_ambiguous` boolean;
- `path_ambiguity_reason` string.

Exit Lab may exclude ambiguous path rows or apply a preregistered conservative ordering rule.

## Rich scoring outputs

The generic rich scorer should eventually aggregate:

- MFE/MAE distributions overall and by symbol/asset class/side/year/month;
- milestone reach rates;
- conditional transition rates such as `P(reach 2R | reached 1R)`;
- time-to-milestone distributions;
- MAE-before-milestone distributions;
- giveback distributions after 1R/2R/3R;
- original-exit outcome conditioned on MFE buckets;
- concentration and tail dependence;
- duration and path ambiguity rates.

## Exit Lab rule

Looking at trade-path data may generate a new exit hypothesis, but it may not retroactively improve the parent experiment verdict.

Example:

> D037 is REJECT_V0. If its trade paths later suggest that a 2R partial + runner structure is interesting, that becomes a new preregistered Exit Lab experiment or new strategy version. D037 remains REJECT_V0 forever.

## Publishing policy

The local runner should publish compact validated analytics to the `backtest-results` branch:

- frozen decision score;
- rich descriptive score;
- compact trade outcomes;
- compact trade-path metrics when available;
- provenance manifest with source/EX5/evidence SHA256 and byte sizes;
- human-readable summary.

Large raw MT5 evidence remains local and is referenced by hashes. Legacy AutoSync is not used.
