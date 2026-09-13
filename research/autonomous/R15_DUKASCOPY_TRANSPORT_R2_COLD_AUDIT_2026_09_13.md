# R15 Dukascopy transport r2 cold audit

Date: 2026-09-13
Status: STATIC AUDIT PASS / deterministic transport preflight not yet claimed executed

Frozen repair:
`research/autonomous/R15_DUKASCOPY_TRANSPORT_REPAIR_2026_09_13.md`

Audited blobs:
- resilient exporter: `c3fe8a5fbdb1aed6d6f176cfecf9f9a42240e66a`
- deterministic transport tests: `7f3c7ae22b4e02318169a34e078f9c776366a54f`

Cold checks:
- scientific R15 v1.01 engine is unchanged;
- only transport/acquisition behavior changed after the WinError 10054 infrastructure failure;
- acquisition is sequential, so the previous three-worker pressure is removed;
- curl HTTP/1.1 is attempted first when present, urllib is fallback;
- both transports request Connection: close and identity encoding;
- retries are bounded and remain fail-closed;
- successful compressed daily payloads are cached atomically and decoded before acceptance;
- cached payloads are decoded again before reuse;
- genuine HTTP 404 is classified as missing/holiday and is not fabricated;
- probe uses the same four frozen representative dates;
- full range remains 2004-11-08 through 2025-12-31 only;
- both URL construction and cache-path construction hard-reject 2026;
- full output again rejects any 2026 New York date;
- no concurrency primitive remains in the repaired exporter;
- the downloader remains read-only with respect to the external source;
- no clock, regression, confirmation, economic, 2025 or protected-OOS rule changed.

The deterministic transport test specifically simulates the observed curl/socket-style failure path, verifies fallback recovery, verifies cache resume without network reuse, checks 404 semantics, and checks hard 2026 guards.

This audit does not claim the remote source probe has passed. That must be demonstrated by actual execution.
