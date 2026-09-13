# R15 Dukascopy transport repair

Date: 2026-09-13
Status: FROZEN AFTER INFRA FAILURE / BEFORE ANY R15 MARKET RESULT

The R15 v1.01 deterministic methodology/source preflight passed on the user's machine.

The subsequent four-date remote Dukascopy source probe failed on 2010-06-01 with Windows socket reset error WinError 10054 after five urllib attempts. No R15 market result was produced and no scientific gate was evaluated.

Classification: infrastructure/transport FAIL only.

Repair:
- keep the frozen R15 scientific hypothesis and engine unchanged;
- replace only the remote downloader transport with v1.01;
- curl HTTP/1.1 is primary when available, urllib is fallback;
- force Connection: close and identity encoding;
- bounded retries remain fail-closed;
- full acquisition becomes sequential instead of concurrent;
- deterministic inter-request delay reduces server pressure;
- successfully downloaded compressed daily payloads are cached atomically so a later transient failure can resume without redownloading prior days;
- true HTTP 404 remains a missing/holiday day rather than a fabricated price;
- 2026 URL, cache-path and row guards remain hard failures.

The transport repair is not an alpha rescue and changes no clock mapping, regression, stage boundary, statistical gate, cost assumption, 2025 gate or protected-2026 rule.
