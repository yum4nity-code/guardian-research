# Challenge Probability Lab — Post-Validation Gate v1.00

Date: 2026-09-07 Europe/Paris
Status: **IMPLEMENTED / TESTED / CANONICAL FOR FUTURE OOS-CONFIRMATION PIPELINES**

## What changed

Challenge Probability Lab is no longer intended to be a manually launched side script.

The research pipeline is now formally:

`... -> STAT VALIDATION / OOS -> RED TEAM -> CHALLENGE PROBABILITY LAB -> PRODUCTION CANDIDATE -> ...`

The Lab remains strictly downstream. It cannot rescue failed alpha.

## New files

- `research/challenge_probability_lab/post_validation_challenge_gate_v1_00.py`
  - Git blob: `412f8ee8b627cc1600385a2f5133e89dbe611fd6`
- `research/challenge_probability_lab/test_post_validation_challenge_gate_v1_00.py`
  - Git blob: `599f2cbc2d0dd2aea3d23ed41b3d9774048c9069`
- `research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`
  - Git blob: `a3be60edaf5907ae0073a8d600dabe1a8c362e4c`

`docs/RESEARCH_PROTOCOL.md` and the Lab README were updated to make this path canonical.

## Eligibility handshake

Every future frozen OOS/confirmation scorer that can promote a strategy must persist an explicit JSON boolean:

```json
{
  "challenge_lab_eligible": true
}
```

Only a strategy/portfolio that passed its preregistered alpha/OOS/robustness requirements may set it to `true`.

The post-validation gate does **not** infer eligibility from arbitrary status strings. Missing/wrong eligibility fails closed; `false` is skipped with a persisted manifest.

## Canonical trade export contract

Future Lab-ready trade files must include:

- `run_stage`
- `symbol`
- `entry_time`
- `exit_time`
- `net_r`
- `challenge_day` — prop-firm-normalized `YYYYMMDD` day key
- `adverse_r` — signed individual adverse excursion in R, `<= 0`

The run manifest must document the day/reset basis, R denominator, cost basis and floating-equity availability.

This closes two ambiguities that existed in legacy trade CSVs:

1. raw entry-date grouping is not automatically equivalent to the prop-firm daily-loss day;
2. historical `MAE_R` sign conventions are not safe to guess.

## Automatic gate behavior

For an eligible result the gate:

1. validates the canonical export contract;
2. runs Challenge Probability Lab;
3. uses 20,000 paths per risk by default;
4. uses the frozen risk grid `0.10 / 0.15 / 0.20 / 0.25 / 0.33 / 0.50 %` unless the campaign froze another grid before outcomes;
5. emits `challenge_gate_manifest.json`;
6. emits `challenge_probability.json`, `.csv`, `.md`;
7. records DD fidelity and selected pass-optimal risk.

For a rejected/unconfirmed result it emits `SKIPPED_NOT_ALPHA_VALIDATED` and does not run the Lab.

For new canonical runs, missing `challenge_day` fails closed. Legacy validated data can only bypass this using the explicit `--allow-legacy-atomic-export` flag, and remain marked `ATOMIC_CLOSED_EQUITY`.

## Validation evidence

Local validation was performed on the exact GitHub-bound source snapshots:

- Python compile check: PASS;
- original Challenge Lab tests: **8/8 PASS**;
- post-validation gate tests: **4/4 PASS**;
- total: **12/12 PASS**.

Post-validation gate tests cover:

- rejected/unconfirmed eligibility -> skip;
- eligible canonical export -> Lab runs and writes all reports;
- missing canonical `challenge_day` -> fail closed;
- explicit legacy atomic escape hatch -> permitted but fidelity marked lower.

A real Guardian-schema integration smoke was also performed using the previously extracted D037 `trades_compact.csv` sample. Because that legacy excerpt contains neither canonical `challenge_day` nor `adverse_r`, the smoke required the explicit legacy flag and correctly emitted `dd_fidelity=ATOMIC_CLOSED_EQUITY`.

No performance conclusion is drawn from that tiny D037 smoke; it only validates transport/compatibility.

## Exactness boundary remains

`adverse_r` improves detection of an intratrade breach for one trade, but simultaneous adverse excursions from overlapping positions are still not exactly reconstructible.

Exact prop-firm floating DD remains a later v2-level objective requiring synchronized portfolio mark-to-market/equity snapshots.

## Mandatory behavior for the next Dxxx that survives validation

- its harness/scorer must implement the challenge export contract;
- its OOS/confirmation decision JSON must emit `challenge_lab_eligible`;
- if true, the post-validation gate runs automatically without asking the user for a separate command;
- the selected risk is evidence for challenge-passage sizing, not a new alpha parameter.
