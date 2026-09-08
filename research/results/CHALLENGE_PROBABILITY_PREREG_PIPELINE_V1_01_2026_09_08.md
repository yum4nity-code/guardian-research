# Challenge Probability preregistered post-validation pipeline v1.01 — implementation report

Date: 2026-09-08
Status: **VALIDATED RESEARCH INFRASTRUCTURE**

## Scope

This change closes the gap between frozen alpha/OOS scorers and Challenge Probability Lab without modifying historical scorers or allowing post-result selection of acceptance criteria.

## Canonical files

- `research/challenge_probability_lab/post_validation_pipeline_v1_01.py`
- `research/challenge_probability_lab/test_post_validation_pipeline_v1_01.py`
- `research/challenge_probability_lab/challenge_pipeline_policy_template_v1_00.json`
- lower-level gate: `research/challenge_probability_lab/post_validation_challenge_gate_v1_00.py`
- trade contract: `research/challenge_probability_lab/CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`

## Scientific design

The campaign-specific policy must be committed before protected confirmation/OOS evidence is opened. It freezes:

- accepted scorer verdict(s);
- expected stage;
- scorer verdict/stage/gates keys;
- legacy missing-gates policy;
- Monte-Carlo paths per risk;
- deterministic seed;
- complete risk grid;
- SHA256 of the frozen challenge profile.

The runtime rejects placeholder policies and verifies the profile SHA256 before computing eligibility.

Eligibility is fail-closed. Exact verdict/stage matching and all persisted scorer gates literally equal to `true` are required unless a legacy exception was explicitly frozen in the policy.

Historical frozen scorers are not edited merely to add Challenge Lab integration.

## Validation performed

### Policy/function checks

Local checks: **6/6 PASS**

1. `CONFIRM` + expected stage + all gates true -> eligible.
2. `UNCONFIRMED` -> blocked.
3. wrong stage -> blocked.
4. one false gate -> blocked.
5. placeholder expected stage -> policy rejected.
6. empty risk grid -> policy rejected.

### Integration smoke

PASS:

- valid CONFIRM scorer + frozen policy + matching profile produces `challenge_lab_eligibility.json`;
- six risk values propagate to the lower-level gate;
- `paths_per_risk=20000` propagates;
- deterministic seed propagates;
- policy/scorer/profile provenance is persisted.

### Integrity tamper smoke

PASS:

- one-byte profile modification changes SHA256;
- pipeline refuses the run with a profile SHA256 mismatch;
- no silent use of modified challenge rules.

## Operational consequence

The canonical downstream flow is now:

`frozen scorer JSON + preregistered Challenge policy + canonical trades + pinned challenge profile -> post_validation_pipeline_v1_01.py -> fail-closed eligibility -> post_validation_challenge_gate_v1_00.py -> Challenge Probability Lab only if alpha/OOS passed`

Risk optimization remains downstream and cannot rescue failed alpha.

## Remaining exactness boundary

Canonical `adverse_r` improves individual intratrade DD detection, but overlapping simultaneous adverse excursions remain approximate without synchronized portfolio mark-to-market/floating-equity snapshots.

A later v2 should add synchronized portfolio equity snapshots for exact concurrent floating-DD reconstruction.
