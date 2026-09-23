# M04 Validation — Exact Robustness/Parity Semantics Addendum

Date: 2026-09-23
Status: FROZEN BEFORE 2018-2022 OUTCOME ACCESS

This addendum only makes implementation details explicit.

## Trim-best semantics

For trim-best p in {1%,2%}:
- sort validation event endpoint_scores descending;
- remove exactly ceil(N * p) highest endpoint_scores;
- compute the mean of all remaining episodes;
- pass requires the trimmed mean > 0.

No absolute-value trimming and no symmetric trimming.

## Pre-2018 parity snapshot

Before opening any 2018-2022 source:
- reconstruct M04 corr_break and corr_break_z from 2011-2017 only;
- verify the reconstruction reproduces the published 2015-2017 replication results;
- freeze the 2011-2017 corr_break/corr_break_z series for EURUSD/GBPUSD/AUDUSD/USDCHF against UDXUSD;
- record SHA256.

The validation engine must match that frozen pre-2018 reference before scoring 2018-2022.

This addendum changes no alpha rule, signal rule, target, threshold, pair, horizon, cooldown or statistical gate.
