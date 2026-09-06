# Guardian — PC ↔ GitHub AutoSync Engineering Standard

Date: 2026-09-06
Status: mandatory design standard for future Guardian transfer automation
Scope: Windows PC, MT5 research outputs, GitHub `main` and `backtest-results`

## 1. Core rule: two one-way pipelines, never one bidirectional sync

The system is split into two independent flows:

1. **Code deploy:** GitHub `main` -> dedicated local deploy clone -> MT5 `MQL5\Experts\GuardianReasearch`.
2. **Result publish:** MT5 `Terminal\Common\Files` -> immutable local spool -> dedicated Git writer clone -> GitHub `backtest-results`.

The same directory is never both a Git working tree and an MT5 write target. The same file is never edited by both sides of a sync loop.

## 2. Dedicated clones only

Never use `D:\MT5_Backtests\guardian-research` (the human/research working clone) as the transactional writer for automation.

Use separate disposable clones:

- `D:\MT5_Backtests\guardian-deploy-main` — read-only deployment mirror of `main`.
- `D:\MT5_Backtests\guardian-backtest-autosync-results` — single-writer clone of `backtest-results`.

A destructive Git reset is allowed only inside these dedicated disposable clones, never in the human working clone.

## 3. GitHub -> PC -> MT5 deploy transaction

A deploy is complete only when all of the following pass:

1. `git fetch origin main` succeeds in the dedicated deploy clone.
2. The deploy clone is moved to the exact `origin/main` commit (clean disposable clone only).
3. The requested source file exists at the expected repository path.
4. Source SHA-256 is calculated.
5. File is copied to the exact MT5 target path.
6. Destination exists.
7. Destination SHA-256 equals source SHA-256.
8. A deploy receipt records repository commit, source path, destination path, source hash, destination hash and timestamp.

No message may claim “installed” before step 7 succeeds.

## 4. MT5 -> PC -> GitHub result publication transaction

MT5 output files are never pushed directly from their live write location.

For each candidate pair:

1. Discover candidate.
2. Confirm expected companion files exist.
3. Determine fingerprint immediately.
4. If fingerprint is terminal (`PUSHED` or `INVALID`), skip immediately with zero stability wait.
5. For a new candidate only, confirm stability (size + mtime unchanged; hash after stable interval).
6. Validate lifecycle/schema/counters.
7. If invalid, write a permanent quarantine record and never reprocess it unless file content/fingerprint changes.
8. Copy the validated files into an immutable spool directory named by fingerprint/run id.
9. From that spool, perform the Git transaction.
10. Only after remote push succeeds mark the fingerprint `PUSHED`.

An invalid artifact is a terminal state for that fingerprint, not a retryable transport error.

## 5. Queue/state model

Do not maintain only one loose array of published hashes.

Each fingerprint has an explicit durable state:

- `DISCOVERED`
- `STABLE`
- `VALIDATED`
- `SPOOLED`
- `COMMITTED`
- `PUSHED`
- `INVALID` (terminal)
- `GIT_RETRY` (retryable)

State writes must be atomic (write temp file then rename). Prefer one small record per fingerprint/run over one monolithic mutable JSON state file.

Every error is classified as either:

- **artifact error** -> `INVALID`, terminal;
- **transport/Git/network error** -> retry with bounded exponential backoff;
- **watcher process error** -> process restart, queue survives.

## 6. Discovery: polling/reconciliation is canonical

Filesystem events may be used only as a wake-up hint.

The canonical mechanism is a reconciliation scan:

- on process start;
- periodically thereafter;
- after any watcher event.

This prevents missed events from losing runs and prevents duplicate events from creating duplicate publications.

The scan order must never allow one invalid old file to starve newer candidates.

## 7. No head-of-line blocking

Each candidate is processed independently.

Forbidden pattern:

- sleep 20 seconds on item A;
- discover A is already published or permanently invalid;
- repeat A every cycle before reaching B.

Required pattern:

- fingerprint/terminal-state check first;
- quarantine/skip old invalids immediately;
- stability delay only for genuinely new candidates;
- continue to next item after an artifact validation failure.

## 8. Git writer transaction and non-fast-forward recovery

The immutable spool is the source of truth for the publication transaction.

For each spooled run:

1. fetch `origin/backtest-results`;
2. synchronize the dedicated writer clone to the current remote branch before staging;
3. copy exactly one immutable spool item into the branch;
4. generate manifest + `LATEST.json`;
5. commit;
6. push;
7. verify remote branch contains the commit/run;
8. mark `PUSHED`.

If push is rejected because the remote advanced:

- do not edit the spool;
- refresh the disposable writer clone from remote;
- replay the same immutable spool item;
- recommit and retry.

Never resolve an automation conflict by rewriting the human working clone.

## 9. Process supervision

Do not rely on a Startup-folder `.cmd` as the final production mechanism.

Production watcher should be installed as a Windows Scheduled Task with:

- one instance only (`IgnoreNew` or equivalent);
- start when available;
- restart on failure with bounded restart count/interval;
- explicit user/security context;
- no dependency on an interactive PowerShell window.

PID/mutex remains a secondary guard, not the supervisor.

## 10. Health contract

Health JSON must expose at minimum:

- watcher version;
- PID/process start time;
- current time / last successful reconciliation;
- queue counts by state;
- last candidate inspected;
- last invalid fingerprint + reason;
- last pushed run id/fingerprint;
- last successful Git remote commit;
- consecutive Git failures;
- current backoff;
- source directory and destination branch.

`WAITING_NEW_FINAL` is healthy only if reconciliation itself succeeded.

## 11. Logging

One structured log event per state transition, not repeated noise every polling cycle.

Permanent invalid files are logged once when quarantined, then skipped silently except in health counters.

Git retries log attempt number and final classification.

## 12. Versioning

Any code change creates a new script filename/version. Never overwrite a runtime-validated automation under the same filename.

Installers are not allowed to generate strategy EAs by textual patching. Strategy `.mq5` files are complete versioned repository sources.

## 13. Mandatory pre-delivery tests

No automation version reaches the user's live PC until it passes an isolated local harness using a temporary directory and a temporary/local Git repository.

Minimum tests:

1. empty directory;
2. incomplete STATS without TRADES;
3. non-FINAL STATS;
4. valid finalized pair;
5. duplicate candidate event;
6. already-pushed fingerprint;
7. permanently invalid pair;
8. invalid older pair followed by valid newer pair (must prove no starvation);
9. files changing during stability window;
10. simulated Git push failure and recovery;
11. process restart with queued item;
12. two sequential valid new pairs;
13. exact deploy copy with source/destination hash equality.

The acceptance criterion for AutoSync is not static review. It is an end-to-end proof that two consecutive new artifacts travel through the entire pipeline without manual intervention.

## 14. Immediate lessons from v2.01–v2.05

- A generic rewrite must not replace a runtime-proven lifecycle primitive without an isolated regression test.
- An array/regex language edge case must be caught in the local harness, not on the user's PC.
- Published/invalid candidates must be skipped before any expensive stability wait.
- Validation errors must quarantine one artifact, not poison the entire scan loop.
- A watcher can appear alive while making zero useful progress; health needs queue/progress semantics.
- “File exists in GitHub” and “file installed in MT5” are different facts; deployment requires destination verification and hash equality.

## 15. Future implementation target

Next major rewrite should be **AutoSync v3**, built from this standard rather than another incremental patch of v2.x.

v2.05 may remain as a temporary recovery watcher, but no further architectural features should be bolted onto it. Any emergency patch must stay minimal and must not change the v3 design target.
