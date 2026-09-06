# Manager Evidence Ledger

Purpose: track cross-strategy / cross-market evidence that exit management itself may be a reusable source of improvement.

Policy:
- Manager tuning is NOT forbidden.
- What is forbidden is tuning a manager on one inspected sample and then calling that same sample validation.
- A manager study becomes justified when the same management weakness appears across multiple independent sleeves or markets.
- When justified, freeze a finite candidate family, tune only on a designated development sample, then confirm on genuinely untouched data / markets.
- Prefer reusable manager components over strategy-specific rescue rules.
- Do not demand a perfect entry with frozen exits forever; manager quality is itself a research object.

## Current evidence — 2026-09-06

All D17 figures below compare the same v11.17 entry events under NATIVE_RATCHET versus FIXED_3R.

| Market | N | Native net R/trade | Fixed 3R net R/trade | Native - Fixed |
|---|---:|---:|---:|---:|
| BTCUSD | 1739 | -0.116 | -0.147 | +0.031 |
| ETHUSD | 1141 | -0.119 | -0.208 | +0.088 |
| EURUSD | 300 | -0.076 | -0.271 | +0.195 |
| GBPUSD | 429 | -0.118 | -0.073 | -0.044 |
| USDJPY | 524 | -0.009 | -0.045 | +0.037 |
| XAUUSD | 676 | -0.049 | +0.041 | -0.090 |

### Interpretation
- Ratchet helps 4/6 tested markets versus fixed 3R, but hurts GBPUSD and XAUUSD.
- ETHUSD and EURUSD show clearly positive paired manager deltas on the inspected sample; BTCUSD and USDJPY improvements are smaller/inconclusive.
- XAUUSD is the strongest warning against a universal manager: FIXED_3R is mildly positive pooled while NATIVE_RATCHET is negative.
- Therefore manager tuning is justified as a future component study, but the current evidence argues against one universal fixed trail setting across all asset classes.
- Asset-class-specific or state-dependent manager hypotheses may be researched later, but only with finite preregistered candidate families and untouched confirmation.

### D17 entry-system conclusion so far
- BTCUSD/ETHUSD: insufficient net alpha after costs.
- EURUSD/GBPUSD: negative under both managers.
- USDJPY: near-flat Native pooled, but strong 2024 positive / 2025 negative regime flip; not validated alpha.
- XAUUSD: FIXED_3R pooled about +0.041R/trade but 2024 negative / 2025 positive regime flip; not validated alpha.
- USDCAD is still missing from this exact v11.17 cost-aware batch.

Decision:
- Keep dedicated MANAGER-STUDY hypothesis alive.
- Do not rescue D17 by tuning on these same inspected markets and calling that validation.
- Finish USDCAD exact v11.17 cost-aware attribution.
- Then move to independent strategy sleeves (USDJPY ORB, D032 Doji, etc.) and log whether similar exit-management weaknesses recur. If they do, open a formal manager campaign.