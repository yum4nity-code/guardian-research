# Guardian Research — CURRENT PROJECT HANDOFF

Last updated: 2026-09-07 Europe/Paris
Status: **ACTIVE / D053 REJECTED / D054 UNCONFIRMED-CLOSED / NO CURRENT ALPHA P0 PROMOTED / CHALLENGE PROBABILITY LAB V1.00 AVAILABLE**

## Canonical resume

Read first:
1. this file;
2. latest `backtest-results` branch state for the newest Dxxx campaign;
3. `START_HERE_NEXT_AI.md` and `GUARDIAN_MASTER_MANDATE.md` for governance;
4. `CURRENT_QUEUE.json` only with the warning below.

### Important metadata warning

`CURRENT_QUEUE.json` on `main` still reflects the older Sep-6 D036 state and must not override newer run evidence. The `backtest-results` branch is newer and is the source of truth for the most recent experiment outcomes until queue reconciliation is performed.

Do not reopen rejected families merely because they remain in older handoffs/queue entries.

## Latest research state observed on 2026-09-07

### D053 — US Index ORB30 Entry Alpha V0

Latest mirrored event:
- experiment: `D053-US-INDEX-ORB30-ENTRY-ALPHA-V0`;
- stage: development;
- latest audit status: `D053_DESCRIPTIVE_AUDIT_COMPLETE_NO_VERDICT_CHANGE`;
- the audit explicitly records the formal verdict as `D053_REJECT_V0`.

The descriptive audit is post-verdict evidence only. Do not mine its weekday/symbol/latency breakdowns into a same-sample rescue.

### D054 — ORB30 Core3 Jul-Aug 2026 Confirmation V0

Latest mirrored event:
- experiment: `D054-ORB30-CORE3-JUL-AUG2026-CONFIRMATION-V0`;
- stage: confirmation;
- latest status: `D054_UNCONFIRMED_CLOSE`.

Therefore D054 is closed/unconfirmed, not promoted. No D055 campaign was present in `backtest-results` when this handoff was reconciled.

### Consequence

The old D036 P0 text previously in this file was stale relative to D037-D054 work already present in `backtest-results`. D036 remains historical evidence in its own campaign/results files; it is no longer the canonical current P0 here.

The next alpha action is to select/preregister a genuinely independent next family rather than rescue D053/D054 on inspected data.

## New research infrastructure — Challenge Probability Lab v1.00

Purpose:

> Estimate the probability that a strategy/portfolio reaches the challenge profit target before a daily or overall drawdown rule is breached, across a frozen risk grid.

This solves a different problem from PF, expectancy or generic bootstrap: it optimizes **probability of passing the challenge**, not terminal profit.

### Files

- engine: `research/challenge_probability_lab/challenge_probability_lab_v1_00.py`
- tests: `research/challenge_probability_lab/test_challenge_probability_lab_v1_00.py`
- generic profile: `research/challenge_probability_lab/guardian_reference_profile_v1_00.json`
- documentation: `research/challenge_probability_lab/README.md`
- validation report: `research/results/CHALLENGE_PROBABILITY_LAB_V1_00_IMPLEMENTATION_REPORT_2026_09_07.md`

Validated engine Git blob:
`0fbe86213b5d42dd4d8a6202e4e246ae2ed6ee75`

Validated test Git blob:
`800808538f1c2013cabb3a48c3ddaa787fb81853`

### v1.00 risk grid

- 0.10%
- 0.15%
- 0.20%
- 0.25%
- 0.33%
- 0.50%

per trade.

### Simulation method

- consumes one or more real trade CSVs with realised R;
- groups the observed process by calendar/challenge day;
- supports explicit `--day-column` for a prop-firm-normalized day key;
- circular moving-block bootstrap of contiguous days (default 5 days), not iid trade shuffle;
- common sampled day paths across risk levels for paired comparison;
- initial/reference-capital risk sizing by default, with current-balance option;
- configurable target, daily loss, max loss and static/trailing-EOD overall-loss anchor;
- explicit timeout horizon;
- optional signed adverse-R column for stronger intratrade DD checking;
- deterministic seed and input SHA256 provenance.

### Output per risk

- pass probability + Wilson 95% CI;
- daily-DD violation probability;
- max-DD violation probability;
- any-DD violation probability;
- timeout probability;
- median/P25/P75/P90 days to pass;
- median/P90 trades to pass;
- typical/bad max-DD distribution (median/P90/P95/P99/worst observed);
- risk selected specifically for maximum pass probability.

Each run writes JSON, CSV and Markdown.

### Validation

- Python compile check: PASS.
- Unit tests: 8/8 PASS.
- Real Guardian CSV-schema smoke: PASS using an 18-row excerpt from D037 `trades_compact.csv` solely as an integration check.
- No alpha/performance conclusion is allowed from that tiny smoke sample.

### Exactness boundary

Without synchronized floating-equity data, v1.00 is an **atomic/closed-equity challenge simulator**, not an exact reconstruction of prop-firm floating DD.

Ordinary `net_r` can miss an intratrade breach or a breach caused by concurrent open positions. A signed adverse-R column improves the check but still cannot reconstruct simultaneous portfolio excursions.

Preferred future harness/export enrichment:
1. normalized `challenge_day`;
2. signed MAE/adverse R;
3. ideally synchronized portfolio floating-equity / mark-to-market snapshots.

Never report atomic DD probabilities as exact floating-equity compliance probabilities when those fields are absent.

### Scientific boundary

The Challenge Lab is downstream infrastructure. It must not be used to rescue a strategy that failed its alpha/OOS gates. Risk changes the challenge path; it does not create expectancy.

## Guardian production / compliance separation

Guardian Core v12.01 remains the compile-validated pure infrastructure baseline. No Challenge Lab work changed `production/guardian/` or live trading semantics.

FundedNext request/retry hyperactivity remains separate compliance/runtime work. Do not mix it into strategy alpha or Challenge Lab scoring.

## Next safe actions

1. Keep D053 and D054 closed; do not same-sample rescue them.
2. Reconcile `CURRENT_QUEUE.json` when the next independent alpha family is selected/preregistered.
3. For the next strategy that actually survives its alpha/OOS gates, run Challenge Probability Lab on its frozen trade history with the six default risk levels.
4. Prefer 20,000+ Monte-Carlo paths for decision runs; keep seed, block length, profile, input trades and horizon frozen when comparing risks.
5. Extend future standardized trade exports with a normalized challenge-day key and adverse excursion / floating-equity evidence so the Lab can evolve toward exact daily-DD simulation.
6. Keep Guardian Core v12.01 stable unless a separate production change is explicitly justified and validated.
