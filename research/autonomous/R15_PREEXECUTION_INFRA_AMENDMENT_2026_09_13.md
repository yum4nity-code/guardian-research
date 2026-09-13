# R15 pre-execution infrastructure amendment

Date: 2026-09-13
Status: frozen before any R15 market result

The original R15 preregistration referenced the previously prepared top-two XAU long-history manifest as the intended data source. At manual launch, that manifest was not present at the expected local path. No R15 market result had been produced.

To avoid either guessing a path or re-exporting data through July 2026, R15 now uses a dedicated read-only XAUUSD M1 exporter bounded strictly to:

- start: 2017-01-01 UTC
- end exclusive: 2026-01-01 UTC

The exporter is:
`research/autonomous/r15_xauusd_pre2026_market_export_v1_00.py`

It:
- connects only to the required `FundedNext-Server 2` terminal;
- exports XAUUSD M1 in monthly chunks;
- writes only 2017-2025 yearly files;
- fails closed on any 2026 timestamp;
- records SHA256 for every yearly file;
- may reconcile the 2024-2025 overlap against the already frozen Phase I-B raw dataset;
- records `protected_2026_opened=false`.

This amendment changes infrastructure provenance only. The R15 hypothesis, time-of-day mapping, statistical gates, confirmation window, economic translation, 2025 pre-OOS gates, and no-rescue rules are unchanged.
