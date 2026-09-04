# Guardian v11.17.05 Shared Intel Observer — live smoke PASS

Date: 2026-09-04
Status: PASS
Scope: FTMO Demo, Guardian_D017_PropFirmAuto_v11_17_05_SHARED_INTEL_OBSERVER_CANDIDATE

## Evidence
Guardian itself (not the standalone probe) produced live observer logs:

- `[SHAREDINTEL][OBSERVER] ready=YES gen=1788515343726 age=274ms BTC=OK ETH=OK | READ_ONLY_NO_TRADING_EFFECT`
- BTC features present: OI deltas 1m/5m, funding, basis, spot/perp returns 1m/5m, dislocation, liquidation long/short/net, coverage flags.
- ETH features present with the same feature set.
- Coverage flags were complete on both 1m and 5m groups (`cov1/5=1111/1111`) for the sampled log.
- Freshness age observed: 274 ms.
- BTC and ETH status both `OK`.

## Sample values
BTC:
- OI d1/d5: -0.0064% / -0.0392%
- funding: 0.00635%
- basis: -0.0449%
- spot return 1m/5m: -0.0351% / -0.0761%
- perp return 1m/5m: -0.0280% / -0.0930%
- dislocation 1m/5m: +0.0071% / -0.0169%
- liquidations long/short/net 1m/5m: 0

ETH:
- OI d1/d5: +0.0195% / +0.0409%
- funding: 0.01000%
- basis: -0.0432%
- spot return 1m/5m: -0.0317% / -0.2797%
- perp return 1m/5m: -0.0262% / -0.2692%
- dislocation 1m/5m: +0.0055% / +0.0105%
- liquidations long/short/net 1m/5m: 0

## Interpretation
The observer integration is confirmed live inside Guardian. The shared-intelligence transport and parser are functioning and freshness is low. This gate does not authorize any strategy, risk, SL, TP, sizing, compliance, RSI, Momentum, or LER behavior to depend on these fields yet.

## Next gate
Run a longer observer session and then move to research-only feature studies comparing baseline vs externally-enriched hypotheses for RSI, Momentum, and D025/LER. No live trading influence before OOS/statistical validation and red-team review.
