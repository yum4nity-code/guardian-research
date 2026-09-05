# D030 — Alanazi H4 Engulfing — target-CFD first verdict

Date: 2026-09-05
Status: PRIMARY FX CORE REJECTED / ETH TRANSPORT DISCOVERY CANDIDATE
Classification: CLOSE_REPLICATION_CFD_TRANSFER for seven-major FX core; non-FX symbols are ADAPTATION / TRANSPORT DIAGNOSTICS.

## Frozen primary seven-major FX core
Signal cutoff enforced at 2026-08-31 23:59 as preregistered. Completed events:

- EURUSD n=339, mean executable R = -0.0468
- GBPUSD n=334, mean R = -0.0767
- USDJPY n=264, mean R = +0.0237
- USDCHF n=291, mean R = +0.0593
- USDCAD n=334, mean R = -0.0884
- AUDUSD n=291, mean R = -0.0713
- NZDUSD n=283, mean R = -0.0212

Pooled seven-major core:
- n = 2,136 completed trades
- mean executable R = -0.0348/trade
- fixed-size pip result = -2,797.3 pips total, -1.31 pips/trade
- only 2/7 majors positive mean R
- 32-month block bootstrap 95% interval for pooled mean R approximately [-0.0823, +0.0162]

Primary D030 gate therefore FAILS decisively. The source-like H4 engulfing rule does not reproduce a useful broad FundedNext-CFD FX edge over 2024-2026 in this implementation. Do not rescue the seven-major core on this same sample with trend filters, RSI, alternate RR, or direction selection.

## User-added transport / adaptation diagnostics
These markets were not part of the frozen primary FX replication gate and cannot rescue it.

### ETHUSD — strongest discovery anomaly
Frozen-window completed n=225.
- mean executable R = +0.1605/trade
- win rate = 57.33%
- long mean = +0.1243R (n=116)
- short mean = +0.1991R (n=109)
- yearly mean R: 2024 +0.3260; 2025 +0.0670; 2026 +0.1271
- 32-month block bootstrap 95% interval approximately [+0.0370, +0.2819]
- no-gap subset remains positive (about +0.130R in the full run before the frozen cutoff adjustment is immaterial to the interpretation)

This is the only user-added market that clears the project's nominal +0.15R pre-swap discovery threshold with a positive bootstrap lower bound and broad long/short participation.

Important cost caveat: D030 summary embeds BID/ASK spread but DOES NOT include historical swap. Current ETHUSD broker properties at run time report swap mode=points, long=-385, short=-385, triple-rollover day=5. Mean holding duration is about 24.95h, median about 9.86h; ~28% of trades last >=24h. A rough current-spec rollover stress can materially reduce the +0.1605R gross edge, so ETH is NOT production-ready and must be cost-stressed/confirmed before promotion.

Interpretation: ETH H4 engulfing is a genuine post-hoc transport discovery candidate worth a fresh preregistered untouched-period confirmation. It is not evidence that the Alanazi pattern is universally profitable on crypto.

### BTCUSD
n=218, mean +0.0524R. Bootstrap interval crosses zero. Interesting directionally but far below the +0.15R project gate. Do not promote.

### XAUUSD
n=288, mean +0.0372R. Bootstrap interval crosses zero. Broad XAU version FAILS.
Post-hoc direction diagnostic: LONG-only mean about +0.171R while SHORT-only mean about -0.095R. This is a discovery clue only and cannot be retroactively selected as validation.

### DOGUSD / LNKUSD / XRPUSD
- DOGUSD n=192, mean -0.0859R
- LNKUSD n=268, mean -0.0214R
- XRPUSD n=234, mean -0.0129R
No promotion.

### Extra FX transports
EURJPY n=297 mean +0.0621R; USDCNH n=283 mean -0.0527R. Neither meets the project edge gate.

## Decision
1. Reject D030 broad seven-major FX V0 on the target CFD feed.
2. Preserve ETHUSD H4 Alanazi-engulfing as a post-hoc transport discovery candidate and preregister an untouched pre-2024 confirmation before any such run is inspected.
3. XAU LONG-only is a watchlist clue only; do not tune or select it on this sample.
4. Swap/rollover must be explicitly stressed before any ETH production work because D030's first-pass PnL excludes historical swap.
