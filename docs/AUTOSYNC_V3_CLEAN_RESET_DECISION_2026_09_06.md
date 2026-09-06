# AutoSync v3 — clean reset decision

Date: 2026-09-06
Status: AUTHORITATIVE MIGRATION DECISION

## Owner clarification

The legacy Guardian AutoSync never reached a reliably working state in practice.

Therefore the migration must not treat v1/v2.x as a trusted runtime baseline, fallback mechanism, or behavior that needs to be preserved.

## Consequence

AutoSync v3 is a clean implementation from the engineering standard, not an incremental migration of v1/v2.x.

Legacy scripts remain available only as historical evidence of failure modes and previously attempted fixes. They must not be extended with new architectural behavior.

## Build order

1. isolated temporary-directory harness;
2. local source -> staging deploy with SHA equality proof;
3. local synthetic result pair -> immutable spool;
4. schema/lifecycle validation;
5. local Git repository publish transaction;
6. duplicate, invalid-artifact, restart and retry tests;
7. two consecutive end-to-end synthetic successes;
8. only then connect to real MT5 directories and GitHub branches;
9. prove two consecutive real result publications and two verified source deployments;
10. archive legacy v1/v2.x automation from the active path.

## Non-goals

- no patching v2.05 into v3;
- no reliance on a currently installed watcher;
- no compatibility layer for broken legacy state files;
- no claim that legacy AutoSync is an emergency fallback.

## Acceptance criterion

AutoSync is considered working only after repeatable end-to-end proof. A watcher process being alive, a file appearing locally, or a single successful Git push is not sufficient.
