# EA01-XR-RSI-LONG-V1 — V2 read-only audit of existing OOS 2023-2025

Date: 2026-09-23
Status: FROZEN BEFORE READ-ONLY DIAGNOSTIC
Parent historical verdict: KILL (preserved)
Purpose: reclassify under Guardian Validation Doctrine V2 without changing the candidate or opening new market data.

## Frozen evidence

Candidate: EA01-XR-RSI-LONG-V1
Existing OOS period: 2023-01-01 through 2025-12-31
Protected 2026: unopened

Canonical local files:
- Research/Autonomous/edge_atlas/EA01-XR-RSI-LONG-V1-OOS-2023-2025/signals.csv
- result.json
- verdict.json

Expected hashes:
- signals.csv: 35ab88bb139a9b8c23f0ad28287718af9c1906af1eae6cfe78087464a255c3ac
- result.json: b052f49ae30b54169a5e11fdd424d5c5e8c3281937474557a324dad402a44713
- verdict.json: 3d7075fea4dd800cc3562707dadf139c14e45f289c9339ff35481a0c288dcc12

Frozen published aggregates:
- raw candidate signals: 944
- non-overlap signals: 654
- cost 0.10 mean: +0.06216246499009125 R/trade
- cost 0.10 PF: 1.0868273589119208
- cost 0.20 mean: +0.01576173506412815 R/trade
- cost 0.20 PF: 1.0213334511927052
- cost 0.10 total: +40.65425210351968 R
- cost 0.20 total: +10.30817473193981 R
- historical KILL reason: primary PF 1.087 < frozen PF >=1.10 threshold
- temporal gate: PASS
- stress gate: PASS

Historical cost-0.10 annual result:
- 2023: n245, mean -0.0035R
- 2024: n231, mean +0.0431R
- 2025: n178, mean +0.1772R

## What this audit may compute

Using ONLY the existing OOS signal ledger:
- exact hash/parity verification;
- monthly / quarterly / yearly summaries;
- leave-one-year-out;
- month-cluster bootstrap uncertainty;
- trim-best 1% / 2%;
- remove best 1/3/5/10 trades;
- positive-return concentration;
- rolling 100-trade diagnostics;
- cumulative R and max drawdown;
- same diagnostics under the already-published cost 0.20 stress.

These are diagnostics under Doctrine V2, not new optimization criteria.

## What this audit may NOT do

- change direction;
- change RSI threshold/alignment;
- change extension/range threshold;
- change horizon;
- change overlap/cooldown rule;
- choose a better subgroup from the OOS result;
- alter cost assumptions beyond the already published 0.10 and 0.20 cases;
- inspect 2026;
- reread raw market data;
- rerun the strategy engine;
- convert a diagnostic into a new ex-post filter.

## V2 classification

After exact parity:
- Layer 1 existence is classified NEGATIVE / POSITIVE_UNCERTAIN / POSITIVE_CONFIRMED using the unchanged cost-0.10 outcome and month-cluster uncertainty.
- A positive estimate is retained even if the uncertainty interval crosses zero.
- Layer 2 economic size: positive cost-0.10 expectancy qualifies for MINI_EDGE; positive cost-0.20 adds STRESS_POSITIVE.
- Layer 4 production remains separate. The old PF>=1.10 failure remains historically valid as a production-size gate.

No new market-data result is authorized by this document.
