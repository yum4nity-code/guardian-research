# Guardian Research — Repository Map

This file explains which parts of the repository are current control surfaces and which are historical evidence.

## Canonical entrypoints

Use these first:

1. `CURRENT_PROJECT_HANDOFF.md` — concise current state and resume procedure.
2. `START_HERE_NEXT_AI.md` — takeover order and hard rules.
3. `GUARDIAN_MASTER_MANDATE.md` — durable project mission, architecture and research principles.
4. `docs/RESEARCH_PROTOCOL.md` — scientific protocol.
5. `research/autonomous/AUTONOMOUS_RESEARCH_MANDATE.md` — autonomous research control contract.
6. `research/autonomous/RESEARCH_QUEUE.json` + `RESEARCH_QUEUE_APPEND.json` — executable queue state.
7. `backtest-results` branch — published runtime evidence and receipts.

For the current R4/R5 campaign, the canonical detailed handoff is:

`handoff/2026/09/11/GUARDIAN_R4_R5_CURRENT_HANDOFF_2026_09_11.md`

## Directory roles

### `research/autonomous/`

Current and historical autonomous research engines, tests, queue definitions and preregistration support.

Rule:
- code may be historical even if it remains present;
- queue enablement + current handoff determine what is active;
- never infer active status from filename presence alone.

### `research/protocols/`

Preregistered protocols and frozen experiment definitions.

These are provenance-critical. Do not rewrite a historical protocol after results are known. Create a new revision/path instead.

### `research/results/`

Research reports, audit evidence and campaign result summaries.

Treat as historical evidence. Do not delete merely because a family failed.

### `handoff/`

Continuity and agent-to-agent transfer material.

Current dated handoffs live under:
`handoff/YYYY/MM/DD/`

Legacy subtrees such as:
- `handoff/chatgpt_to_codex/`
- `handoff/codex_to_chatgpt/`
- older D0xx handoffs

are preserved for provenance and are not current instructions unless referenced by the canonical current handoff.

### `production/`

Production Guardian infrastructure. Research must not modify production behavior without an explicit, separately validated production change.

### `automation/`

Installers, launchers and operational automation. Historical scripts may remain for reproducibility.

### `docs/`

Durable documentation, research protocol, repository map and architecture notes.

### `candidates/`

Only for strategies that have actually earned candidate/promotion status under the current validation rules. Presence elsewhere does not imply production candidacy.

## Archive policy

Guardian research depends heavily on provenance, so repository cleanup should be **non-destructive by default**.

Preferred cleanup order:

1. mark one canonical current entrypoint;
2. archive superseded summary documents;
3. add clear legacy/current labels;
4. preserve historical code/results/receipts;
5. delete only proven disposable duplicates, caches or generated clutter that are not part of scientific provenance.

Git history is useful but is not a substitute for preserving named scientific artifacts referenced by receipts/handoffs.

## Current archive note

The previously accumulated `CURRENT_PROJECT_HANDOFF.md` was preserved at:

`handoff/archive/CURRENT_PROJECT_HANDOFF_LEGACY_THROUGH_2026_09_11.md`

The top-level file is now intentionally short and points to the current dated handoff.

## What wins when documents disagree

Priority for current operational truth:

1. direct current runtime evidence / receipt;
2. current dated canonical handoff;
3. `CURRENT_PROJECT_HANDOFF.md`;
4. current executable queue;
5. durable mandate/protocol;
6. older handoffs and historical campaign notes.

For scientific provenance, however, the frozen preregistration and exact result artifact for that historical experiment remain authoritative for what that experiment actually did.
