# D032-E3 — Bullish Doji Star H1 reclaim-high delayed entry

Date: 2026-09-05
Status: EARLY REJECTION ON POST2024 CORE / ENTRY-LOCALIZATION FIX FAILED
Classification: POSTHOC_ENTRY_TIMING_DEVELOPMENT

Canonical preregistration: `research/campaigns/D032_E3_DOJI_RECLAIM_HIGH_ENTRY_DIAGNOSTIC_PREREGISTRATION_2026_09_05.md`

## Supplied run window
User supplied BTCUSD, ETHUSD, DOGUSD core plus LNKUSD/XRPUSD transport runs covering 2024-01-01 through 2026-06-24 on the current FundedNext historical feed using M1 + `1 minute OHLC`.

Although the preregistration allowed the broader 2018-2026 development window and requested PRE2024/POST2024 robustness views when available, the supplied batch is POST2024 only. Because the candidate fails its central purpose — reducing adverse excursion — on all three core symbols, no PRE2024 rescue run is required. This is treated as a cheap-fail rejection, not a full pooled 2018-2026 gate pass/fail table.

## Frozen candidate
- signal unchanged: confirmed Bullish Doji Star H1 + strict 144h SMA downtrend;
- immediate baseline = first ASK after H1 signal;
- delayed entry = first ASK when BID reclaims the closed Doji H1 high;
- reclaim must occur within 6h;
- both entries evaluated at the same original signal +24h BID;
- no SL, TP or trailing.

## POST2024 core results
Clean reclaim-triggered core events = 59:
- BTCUSD: 23
- ETHUSD: 25
- DOGUSD: 11

Pooled reclaim result:
- mean reclaim +24h = +0.679R/event;
- median reclaim +24h = +50.09 bps;
- win rate = 64.4%;
- all three core symbols have positive mean reclaim +24h R;
- largest positive event contributes only ~8.5% of total positive reclaim R, so concentration is not the problem.

However, relative to taking the same Doji immediately, the delayed entry loses value:
- mean paired reclaim-minus-baseline delta = **-0.391R/event**;
- median paired delta = **-0.349R/event**;
- paired triggered baseline mean = +1.071R/event.

Per symbol mean paired delta:
- BTCUSD: -0.387R;
- ETHUSD: -0.366R;
- DOGUSD: -0.458R.

The reclaim-high rule therefore pays a materially worse entry price on average.

## MAE — decisive failure
The primary reason for D032-E3 was to improve adverse excursion enough to make realistic stop-based sizing possible.

On the same 59 clean triggered events:
- immediate-entry median MAE = **-1.017R**;
- reclaim-entry median MAE = **-1.364R**;
- change = **-0.347R**, i.e. the delayed entry is about 0.35R MORE adverse, not >=0.25R less adverse as required.

Mean MAE also worsens:
- immediate baseline mean MAE = -1.497R;
- reclaim mean MAE = -1.787R.

Per-symbol median MAE also worsens on every core market:
- BTC: -0.841R -> -1.304R;
- ETH: -1.103R -> -1.455R;
- DOG: -0.691R -> -0.923R.

This is a direct failure of the candidate's intended mechanism, not a marginal miss.

## Other diagnostics
Mean reclaim delay is roughly one hour:
- BTC ~74 min;
- ETH ~62 min;
- DOG ~72 min.

The higher trigger price reduces remaining upside and does not protect against subsequent downside. In this sample, waiting for a reclaim of the Doji high is therefore the wrong type of confirmation for the entry-localization problem.

Transport diagnostics are not part of the primary verdict. LINK remains positive in raw reclaim R but also suffers a negative paired delta and worse MAE; XRP remains negative. They do not rescue the rule.

## Decision
**REJECT D032-E3 reclaim-high as the entry-timing fix.**

Do not retune the same sample to 1h/3h/12h reclaim windows or neighboring trigger levels. Do not reinterpret the positive raw +24h reclaim mean as success: the underlying Doji edge already exists, while the tested timing rule makes the actual entry price and MAE worse.

The underlying D032 Bullish Doji Star entry edge remains confirmed. The unresolved problem remains operational entry/risk management. Next work should avoid another arbitrary confirmation threshold and either:
1. test a structurally different execution concept that can enter LOWER rather than higher after the Doji, or
2. preserve immediate entry and solve risk through a separately frozen management design.

Because D032 remains sparse, independent higher-frequency strategy research should continue in parallel.
