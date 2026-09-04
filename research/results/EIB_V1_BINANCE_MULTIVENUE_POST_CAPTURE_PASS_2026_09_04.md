# EIB V1 — Binance + Bybit Multi-Venue Post-Capture Gate — PASS

Date: 2026-09-04
Status: **PASS**

## Capture

- Smoke start: `2026-09-04T10:16:43.894Z`
- Start ms: `1788517003894`
- Observed duration: `175.981 s`
- Data dir: `D:\MT5_Backtests\Research\ExternalIntelligence`
- Validation mode: post-capture, after the live smoke completed its intended data window but hung during shutdown.

## Integrity

- Unique events: `593`
- Bybit records: `298`
- Binance records: `295`
- Duplicate event IDs: `0`
- Availability-before-receive violations: `0`
- Invalid venue records: `0`
- Missing core channels: `[]`
- Failures: `[]`

## Provider/channel coverage

Both venues supplied BTCUSD and ETHUSD spot price, perpetual price, open interest, funding rate, and aggregate health records during the capture.

Representative core counts were ~35–36 observations per REST metric per symbol over the ~3 minute window. Bybit also observed one ETH liquidation qty/notional event pair.

## Final multi-venue state

Generation: `1788517183456`

For both BTCUSD and ETHUSD:
- Bybit status: `OK`
- Binance status: `OK`
- `both_core_ok = true`
- Cross-venue spot/perp price spreads were populated.
- Funding by venue and funding spread were populated.
- Basis by venue and basis spread were populated.
- 1-minute OI mean/dispersion/direction agreement were populated.
- 1-minute cross-venue returns/dislocation were populated.
- Venue-specific liquidation semantics were preserved; no fake exhaustive cross-venue liquidation total was emitted.

### BTCUSD final 1m examples

- OI mean change: `-0.0244725099 %`
- OI dispersion: `0.0351792423 pp`
- OI same direction: `true`
- Spot return mean: `-0.0250234529 %`
- Perp return mean: `-0.0140434273 %`
- Perp-minus-spot dislocation mean: `+0.0109800256 pp`
- Binance-minus-Bybit spot spread: `+0.0067292753 %`
- Binance-minus-Bybit perp spread: `+0.0006187476 %`

### ETHUSD final 1m examples

- OI mean change: `-0.0101759435 %`
- OI dispersion: `0.0032359181 pp`
- OI same direction: `true`
- Spot return mean: `+0.0099325090 %`
- Perp return mean: `+0.0159003659 %`
- Perp-minus-spot dislocation mean: `+0.0059678569 pp`
- Binance-minus-Bybit spot spread: `+0.0019863103 %`
- Binance-minus-Bybit perp spread: `-0.0019872103 %`

## Expected nulls

5m/15m/1h rolling values were still null in the final snapshot because the validated capture was shorter than those windows and the coverage-aware engine correctly refused to fabricate full-window coverage. This is expected behavior, not a failure.

## Verdict

`[Guardian] BINANCE MULTI-VENUE POST-CAPTURE GATE: PASS.`

The multi-venue research state is accepted for the next engineering gate: publish it through the MT5 shared bridge in read-only form before allowing any strategy to consume it.

## Remaining engineering issue

The live smoke itself hung during shutdown because a quiet Binance WebSocket reader could remain blocked after the stop event. This does not invalidate the captured data or the post-capture PASS, but the shutdown path must be fixed and regression-tested before the multi-venue runtime is promoted for unattended use.
