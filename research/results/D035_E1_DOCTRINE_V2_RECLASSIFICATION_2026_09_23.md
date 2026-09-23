# D035-E1 — Doctrine V2 reclassification

Date: 2026-09-23
Status: RETROSPECTIVE RECLASSIFICATION / NO NEW DATA ACCESS

Parent:
- D035 broad family: DISCOVERY_REJECT
- D035-E1: E1_DO_NOT_ADVANCE / EXPLORATORY_SAME_SAMPLE_NOT_CONFIRMATION

## Causal evidence already obtained

The E1 correction fixed the look-ahead issue in the post-hoc dual-source label by moving the tradable signal timestamp to the later/second BTC or ETH shock.

Primary target remained frozen as XLMUSD.

2024-2025 E1:
- causal dual-source events: 973
- primary XLM rows: 870
- mean executable SHORT +15m: +6.705 bps
- median executable SHORT +15m: 0.000 bps
- mean event-control differential: +13.490 bps
- raw day-cluster bootstrap 95% interval: [+1.996,+11.549] bps
- differential bootstrap 95% interval: [+8.793,+18.302] bps
- mean executable +30m: +3.697 bps
- 2024 mean +15m: +4.104 bps
- 2025 mean +15m: +9.935 bps

The historical E1 advancement gate failed only the large-effect threshold (>=15 bps) and strictly-positive median rule. Six of eight gates passed.

## Doctrine V2 interpretation

This evidence is stronger than a generic positive point estimate:
- raw executable mean is positive;
- raw cluster-bootstrap lower bound is positive;
- event-minus-control differential is positive with a positive lower bound;
- both calendar years are positive;
- +30m remains positive.

However, this was explicitly a same-sample exploratory follow-up on already-inspected 2024-2025 data. Therefore it is NOT a fresh Layer-1 confirmation.

V2 classification:
- discovery/causal credibility: SUPPORTED
- fresh existence status: NOT_YET_FRESHLY_TESTED
- economic size: MINI_EDGE_CANDIDATE
- ensemble status: NOT_TESTED
- production status: NOT_PRODUCTION_READY

The old >=15 bps hurdle is retained as a standalone production-size threshold, not as proof that no edge exists.

## Next scientific action

A fresh 2026-H1 confirmation may be designed prospectively using the exact frozen E1 rule:
- BTC+ETH shocks within <=5m;
- signal at the later/second shock;
- XLMUSD primary target only;
- +15m primary horizon;
- SHORT direction;
- unchanged Binance source definitions / cooldown;
- no target substitution or threshold retuning.

No 2026 data is opened by this reclassification.
