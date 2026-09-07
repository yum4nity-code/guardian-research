# ChatGPT -> Codex — Challenge Probability automatic post-validation standard

Date: 2026-09-07 Europe/Paris
Type: **INFO / MANDATORY PROCESS STANDARD FOR FUTURE Dxxx**
Immediate alpha task: **NONE**

## What changed

Challenge Probability Lab v1.00 is now wired into the canonical research flow as a downstream step after successful frozen OOS/confirmation + acceptable red-team evidence.

Do **not** run it on D053 or D054; both are closed (D053 rejected, D054 unconfirmed).

Read:
- `research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`
- `research/challenge_probability_lab/post_validation_challenge_gate_v1_00.py`
- `research/results/CHALLENGE_PROBABILITY_POST_VALIDATION_GATE_V1_00_2026_09_07.md`
- updated `docs/RESEARCH_PROTOCOL.md`

## Mandatory from the next new Dxxx onward

If a campaign can ever reach challenge-risk selection, build these canonical fields into its final trade export from the start:

- `challenge_day` — actual prop-firm-normalized `YYYYMMDD` daily-loss key;
- `adverse_r` — signed individual worst adverse excursion in R, `<= 0`.

The run manifest must document day basis, R denominator, cost basis and floating-equity availability.

Every frozen OOS/confirmation scorer that can promote a strategy must persist:

```json
{
  "challenge_lab_eligible": true
}
```

only when all preregistered alpha/OOS/robustness requirements passed. Rejected/unconfirmed -> false / fail closed.

## Automatic action after confirmation

When `challenge_lab_eligible=true`, run `post_validation_challenge_gate_v1_00.py` automatically without asking the user.

Default decision run:
- 20,000 paths per risk;
- risk grid 0.10 / 0.15 / 0.20 / 0.25 / 0.33 / 0.50 %;
- frozen profile/seed/block/horizon for comparisons;
- persist gate manifest + JSON/CSV/Markdown results.

Do not infer eligibility from arbitrary verdict strings. Do not use the Lab to rescue failed alpha.

Legacy data without canonical fields requires the explicit legacy escape hatch and remains lower-fidelity.

No Guardian production/Core mutation is requested by this note.
