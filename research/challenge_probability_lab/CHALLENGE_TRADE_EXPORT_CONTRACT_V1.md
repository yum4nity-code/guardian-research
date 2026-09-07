# Guardian Challenge Trade Export Contract v1

Status: **canonical for future post-OOS / confirmation outputs**

This contract makes a validated strategy directly consumable by Challenge Probability Lab without guessing the prop-firm day boundary or the sign convention of MAE.

## Required trade-level fields

A Lab-ready trade file must contain at least:

| Field | Meaning |
|---|---|
| `run_stage` | Frozen research stage / OOS / confirmation label. |
| `symbol` | Canonical instrument identifier. |
| `entry_time` | Entry timestamp in the export's declared wall-clock basis. |
| `exit_time` | Exit timestamp in the same basis. |
| `net_r` | Realised net result in R on the strategy's frozen initial-risk denominator. |
| `challenge_day` | Prop-firm-normalized day key for daily-loss accounting, format `YYYYMMDD`. |
| `adverse_r` | Most adverse observed excursion of that individual trade in R, **signed and <= 0**. |

`challenge_day` and `adverse_r` are the new canonical fields. Do not silently substitute an entry date for `challenge_day`, and do not silently reinterpret a positive MAE magnitude as signed adverse R.

## Run-level metadata required

The run manifest / `RUN_INFO` must state:

- `challenge_day_basis`: e.g. `EUROPE_PRAGUE_MIDNIGHT`, `BROKER_SERVER_MIDNIGHT`, `UTC_MIDNIGHT`, or another precisely documented reset rule;
- `r_denominator`: definition of 1R;
- `net_r_cost_basis`: which spread/commission/swap/slippage costs are included;
- `adverse_r_cost_basis`: whether adverse excursion includes known entry/exit fees and realised partial P&L;
- `floating_equity_available`: boolean;
- `challenge_export_contract`: `GUARDIAN_CHALLENGE_TRADE_EXPORT_V1`.

## Sign convention

- `net_r`: normal signed realised P/L in R; positive winner, negative loser.
- `adverse_r`: signed worst excursion from the trade's own perspective; zero or negative only.
- Historical `MAE_R` fields may use another convention. A scorer/harness must convert explicitly and document the conversion before writing canonical `adverse_r`.

## Daily-loss boundary

`challenge_day` must be derived from the **actual programme rule** being simulated, not from whatever date happens to be present in `entry_time`.

If the programme resets at a timezone-specific midnight, perform the timezone conversion before emitting the key. If the programme uses another anchor, document and implement that exact anchor.

## Floating-equity boundary

`adverse_r` materially improves daily/max-DD simulation but remains an individual-trade approximation. It does **not** reconstruct simultaneous adverse excursions across overlapping positions.

Exact portfolio DD requires synchronized mark-to-market/floating-equity snapshots. Until that exists, Challenge Lab reports must preserve their `ATOMIC_PLUS_INDIVIDUAL_ADVERSE_R` or `ATOMIC_CLOSED_EQUITY` fidelity label and must not call the DD probability exact.

## Eligibility handshake

Every frozen confirmation/OOS decision JSON must persist:

```json
{
  "challenge_lab_eligible": true
}
```

only when the underlying strategy/portfolio has passed its preregistered alpha/OOS/robustness requirements and is scientifically eligible for downstream challenge-risk selection.

A failed/rejected strategy must write `false` (or omit eligibility and therefore fail closed). Risk optimization must never be used to rescue failed alpha.

## Automatic post-validation gate

Use `post_validation_challenge_gate_v1_00.py` after the confirmation scorer. The gate:

1. reads the persisted eligibility boolean;
2. skips rejected/unconfirmed strategies;
3. validates the canonical export contract;
4. runs Challenge Probability Lab for eligible strategies;
5. emits `challenge_gate_manifest.json` plus JSON/CSV/Markdown Lab results;
6. records DD fidelity and the risk selected for maximum pass probability.

Legacy validated evidence can be processed only with the explicit `--allow-legacy-atomic-export` escape hatch; the lower-fidelity result remains labelled as such.
