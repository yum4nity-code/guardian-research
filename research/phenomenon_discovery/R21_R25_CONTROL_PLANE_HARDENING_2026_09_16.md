# R21–R25 control-plane hardening — 2026-09-16

This change responds to the post-v1.02 review without authorizing execution.

## Queue replacement

Generation 84 explicitly supersedes generation 83 and uses
`replace_base_jobs=true`. The orchestrator requires the superseded generation to
equal the base generation, then replaces the base jobs instead of appending to
them. The effective queue contains exactly three R21–R25 revision-4 jobs, all
disabled, with `human_approved_2026=false`.

## Receipt binding

Local receipt dependencies now require exact `job_id`, `revision`, accepted
status and `main_commit`. A receipt for the job itself is considered completed
only when its identity and `main_commit` match the currently checked-out main
commit. Receipts from another commit therefore cannot unlock or suppress a job.

## Output confinement

The v1.02 CLI accepts only the canonical absolute output:

`D:/MT5_Backtests/Research/Autonomous/r21_r25_xau_v102/discovery.json`

The canonical parent, directory and file are checked for redirection before the
result is written. Arbitrary `.bi5`, manifest, provenance and alternate JSON
paths are rejected.

## Persisted R15 pin evidence

`R15_INDEX_PIN_ATTESTATION_2026_09_16.json` records the metadata of the local R15
PASS union manifest, including its raw-file SHA256, the pinned payload-index
SHA256, payload count, window and protected-2026 flag. The v1.02 engine validates
the committed attestation against its embedded index digest before reading the
canonical index.

No market payload was opened, no historical backtest was launched, and no job
was enabled. This correcting-author verification is not the final independent
cold audit.
