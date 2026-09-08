# ACTION_REQUISE — Challenge Probability pipeline v1.01 is now canonical

Date: 2026-09-08
Priority: apply to the **next new Dxxx capable of promotion**. Do not retrofit/reopen D053/D054.

This note **supersedes the Sep-7 process instruction wherever it conflicts**.

## What changed

Do not edit a historical frozen scorer just to add `challenge_lab_eligible` after results exist.

Canonical bridge is now:

`research/challenge_probability_lab/post_validation_pipeline_v1_01.py`

It reads an untouched frozen scorer JSON plus a **pre-registered Challenge policy** and then calls the lower-level gate.

## Required before protected OOS/confirmation is opened

1. Trade export must follow `research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md` and include canonical `challenge_day` + signed `adverse_r <= 0`.
2. Create a campaign-specific policy from `challenge_pipeline_policy_template_v1_00.json`.
3. Replace every placeholder and commit the policy **before viewing the protected result**.
4. Freeze in that policy:
   - accepted verdict(s),
   - expected stage,
   - scorer keys / gates behavior,
   - 20,000 paths/risk unless preregistered otherwise,
   - deterministic seed,
   - complete risk grid,
   - SHA256 of the frozen challenge profile.

## After scoring

Run `post_validation_pipeline_v1_01.py` automatically.

It must:
- verify policy/profile SHA;
- exact-match verdict and stage;
- require all persisted gates true unless a legacy exception was frozen in advance;
- write `challenge_lab_eligibility.json`;
- call `post_validation_challenge_gate_v1_00.py`;
- skip rejected/unconfirmed alpha;
- run Challenge Lab only when eligible.

Do not use risk optimization to rescue failed alpha.

## Current state

- `CURRENT_QUEUE.json` reconciled: no active alpha P0; D053 rejected; D054 closed unconfirmed.
- Challenge Probability Lab engine v1.00 + gate v1.00 + preregistered pipeline v1.01 are validated infrastructure.
- Validation report: `research/results/CHALLENGE_PROBABILITY_PREREG_PIPELINE_V1_01_2026_09_08.md`.
- Guardian Core v12.01 remains unchanged.
