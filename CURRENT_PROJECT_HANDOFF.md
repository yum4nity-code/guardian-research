# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D053 REJECTED / D054 UNCONFIRMED-CLOSED / NO CURRENT ALPHA P0 PROMOTED / CHALLENGE LAB AUTO POST-VALIDATION GATE INSTALLED**

## Canonical resume

Read first:
1. this file;
2. latest `backtest-results` branch state for the newest Dxxx campaign;
3. `START_HERE_NEXT_AI.md` and `GUARDIAN_MASTER_MANDATE.md`;
4. `docs/RESEARCH_PROTOCOL.md`;
5. `CURRENT_QUEUE.json` only with the warning below.

### Important metadata warning

`CURRENT_QUEUE.json` on `main` still reflects older Sep-6 research state and must not override newer run evidence. The `backtest-results` branch is newer for the latest experiment outcomes until queue reconciliation is performed.

Do not reopen rejected families merely because they remain in older queue/handoff entries.

## Latest alpha state observed on 2026-09-07

### D053 — US Index ORB30 Entry Alpha V0

Latest mirrored evidence records the formal verdict `D053_REJECT_V0`. The later descriptive audit explicitly does not change that verdict. Do not mine weekday/symbol/latency diagnostics into a same-sample rescue.

### D054 — ORB30 Core3 Jul-Aug 2026 Confirmation V0

Latest mirrored confirmation status is `D054_UNCONFIRMED_CLOSE`. D054 is closed/unconfirmed, not promoted.

No new alpha P0 is invented here. The next alpha action is selection/preregistration of a genuinely independent family.

## Challenge Probability Lab v1.00 — core engine

Purpose:

> Estimate the probability that a strategy/portfolio reaches the challenge profit target before a daily or overall drawdown rule is breached, and select risk for **passing the challenge** rather than maximizing terminal profit.

Core files:
- `research/challenge_probability_lab/challenge_probability_lab_v1_00.py`
- `research/challenge_probability_lab/test_challenge_probability_lab_v1_00.py`
- `research/challenge_probability_lab/guardian_reference_profile_v1_00.json`
- `research/challenge_probability_lab/README.md`
- `research/results/CHALLENGE_PROBABILITY_LAB_V1_00_IMPLEMENTATION_REPORT_2026_09_07.md`

Validated core engine Git blob:
`0fbe86213b5d42dd4d8a6202e4e246ae2ed6ee75`

Validated core tests Git blob:
`800808538f1c2013cabb3a48c3ddaa787fb81853`

Frozen default risk grid:
- 0.10%
- 0.15%
- 0.20%
- 0.25%
- 0.33%
- 0.50%

per trade.

Core validation: Python compile PASS, 8/8 core unit tests PASS, real Guardian CSV-schema smoke PASS.

## NEW — automatic post-validation gate v1.00

Challenge Lab is no longer a manual side step. `docs/RESEARCH_PROTOCOL.md` now defines the canonical flow:

`... -> STAT VALIDATION / OOS -> RED TEAM -> CHALLENGE PROBABILITY LAB -> PRODUCTION CANDIDATE -> ...`

New files:
- gate: `research/challenge_probability_lab/post_validation_challenge_gate_v1_00.py`
- gate tests: `research/challenge_probability_lab/test_post_validation_challenge_gate_v1_00.py`
- export contract: `research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`
- integration report: `research/results/CHALLENGE_PROBABILITY_POST_VALIDATION_GATE_V1_00_2026_09_07.md`

Validated Git blobs:
- gate: `412f8ee8b627cc1600385a2f5133e89dbe611fd6`
- gate tests: `599f2cbc2d0dd2aea3d23ed41b3d9774048c9069`
- export contract: `a3be60edaf5907ae0073a8d600dabe1a8c362e4c`

Validation:
- core suite 8/8 PASS;
- gate suite 4/4 PASS;
- total local tests 12/12 PASS;
- real D037 legacy-schema gate smoke PASS with explicit legacy flag and correct lower-fidelity label.

### Eligibility handshake — mandatory for future confirmation scorers

Every future frozen OOS/confirmation decision JSON that can promote a strategy must persist:

```json
{
  "challenge_lab_eligible": true
}
```

Only a strategy/portfolio that actually passed its preregistered alpha/OOS/robustness gates may write `true`.

The gate deliberately does **not** infer eligibility from arbitrary strings like `PASS`, `CONFIRM`, etc. `false` is skipped; missing/malformed eligibility fails closed.

Risk optimization cannot rescue failed alpha.

### Canonical future trade export

Lab-ready future trade files must include at least:
- `run_stage`
- `symbol`
- `entry_time`
- `exit_time`
- `net_r`
- `challenge_day`
- `adverse_r`

`challenge_day` is a prop-firm-normalized `YYYYMMDD` key based on the actual daily-loss reset rule.

`adverse_r` is the individual worst adverse excursion in R, **signed <= 0**. Do not guess the sign of historical `MAE_R`; convert/document explicitly.

Run metadata must document day basis, R denominator, cost basis, floating-equity availability and `challenge_export_contract=GUARDIAN_CHALLENGE_TRADE_EXPORT_V1`.

### Automatic gate behavior

For `challenge_lab_eligible=true`:
1. validate canonical export;
2. run Challenge Probability Lab automatically;
3. default to **20,000 paths per risk**;
4. use the six frozen default risks unless the campaign froze another grid before outcomes;
5. emit `challenge_gate_manifest.json`;
6. emit `challenge_probability.json`, `.csv`, `.md`;
7. persist DD fidelity + pass-optimal risk.

For rejected/unconfirmed results: `SKIPPED_NOT_ALPHA_VALIDATED`, no Lab run.

For future canonical results, missing `challenge_day` fails closed. Legacy validated evidence can only use explicit `--allow-legacy-atomic-export` and remains labelled lower fidelity.

### DD exactness boundary

Current fidelity levels:
- `ATOMIC_CLOSED_EQUITY`
- `ATOMIC_PLUS_INDIVIDUAL_ADVERSE_R`

Even with `adverse_r`, simultaneous adverse excursions from overlapping positions are not exact. Exact prop-firm floating DD requires synchronized portfolio mark-to-market/equity snapshots in a later v2-level extension.

Never describe current atomic DD probabilities as exact floating-equity compliance probabilities.

## Guardian production / compliance separation

Guardian Core v12.01 remains the compile-validated pure infrastructure baseline. Challenge Lab work did **not** modify `production/guardian/` or live trading semantics.

FundedNext request/retry hyperactivity remains separate compliance/runtime work. Do not mix it into alpha or Challenge Lab scoring.

## Next safe actions

1. Keep D053 and D054 closed; no same-sample rescue.
2. Select/preregister the next independent alpha family when ready.
3. **From the next new Dxxx onward, build `challenge_day` + signed `adverse_r` into the trade export from the start.**
4. Make every future OOS/confirmation scorer emit `challenge_lab_eligible` explicitly.
5. If that flag is true, run `post_validation_challenge_gate_v1_00.py` automatically — no separate user request/command.
6. Keep 20,000 paths/risk, seed, profile, block length, horizon and risk grid frozen for decision comparisons unless preregistered otherwise.
7. Later v2 improvement: synchronized portfolio floating-equity/mark-to-market snapshots for exact concurrent DD reconstruction.
8. Keep Guardian Core v12.01 stable unless a separate production change is explicitly justified and validated.
