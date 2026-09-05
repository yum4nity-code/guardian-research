# RSI Sniper v11.16.11 — BTC/ETH long-history diagnostic

Date: 2026-09-05
Status: BTC+ETH ENTRY-PATH AUDIT COMPLETE / LEGACY SIGNAL FAILS FIXED-R EDGE TEST / NATIVE MANAGEMENT NOT YET FULLY REPLAYED

## Scope

Source lineage: `Guardian_D017_PropFirmAuto_v11_16_11_STRATEGY_SWITCHES.mq5`.
Diagnostic observer: RSI v11.16.11 CLOSED-BAR recross, M1 RSI14/ATR14, BUY1 + optional BUY2, legacy spread gate and structural stop logic, no live orders/account-state/news/prop-firm selection.

Test period: 2024-01-01 -> 2025-12-31, BTCUSD + ETHUSD, M1, Every tick.

The FILEBOOTSTRAP revision used for the completed runs changed file creation/diagnostics only; signal semantics remained `V11_16_11_CLOSED_BAR`.

## Data integrity

Accepted virtual legs:
- BTCUSD: 5,104 = 4,922 BUY1 + 182 BUY2.
- ETHUSD: 4,416 = 4,258 BUY1 + 158 BUY2.
- Total: 9,520.

Year counts:
- BTC 2024: 2,736; BTC 2025: 2,368.
- ETH 2024: 2,499; ETH 2025: 1,917.

All 9,520 trade IDs have outcome telemetry. Same-M1 stop/target ambiguities are excluded rather than guessed.

Signal-process counts:
- ARM_BUY1: BTC 5,610 / ETH 5,576.
- REJECT_SPREAD: BTC 839 / ETH 1,411.
- ARM_BUY2: BTC 933 / ETH 836.
- BUY2_REJECT_PATTERN: BTC 161 / ETH 216.
- REJECT_INVALID_STOP: BTC 1 / ETH 2.

## Predeclared fixed first-touch EV — pooled

### BTCUSD
- +0.5R: -0.147R
- +1R: -0.143R
- +1.25R: -0.144R
- +1.5R: -0.131R
- +2R: -0.136R
- +2.5R: -0.134R
- +3R: -0.115R

95% EV interval at +1R: -0.171 .. -0.116R.
95% EV interval at +3R: -0.160 .. -0.069R.

BE managers:
- BE@1 -> 2R: -0.095R
- BE@1 -> 3R: -0.068R
- BE@1.25 -> 2R: -0.102R
- BE@1.25 -> 3R: -0.078R

RSI50 before structural stop: 46.9%.
RSI70 before structural stop: 21.8%.

### ETHUSD
- +0.5R: -0.122R
- +1R: -0.106R
- +1.25R: -0.100R
- +1.5R: -0.108R
- +2R: -0.120R
- +2.5R: -0.116R
- +3R: -0.104R

95% EV interval at +1R: -0.136 .. -0.077R.
95% EV interval at +3R: -0.153 .. -0.054R.

BE managers:
- BE@1 -> 2R: -0.071R
- BE@1 -> 3R: -0.067R
- BE@1.25 -> 2R: -0.084R
- BE@1.25 -> 3R: -0.073R

RSI50 before structural stop: 50.6%.
RSI70 before structural stop: 24.5%.

## Year stability

BTCUSD:
- 2024: EV +1R -0.116R; +2R -0.100R; +3R -0.058R.
- 2025: EV +1R -0.175R; +2R -0.177R; +3R -0.181R.

ETHUSD:
- 2024: EV +1R -0.108R; +2R -0.113R; +3R -0.098R.
- 2025: EV +1R -0.104R; +2R -0.129R; +3R -0.112R.

There is no broad positive year to rescue the fixed-R entry hypothesis. BTC deteriorates markedly in 2025; ETH is consistently negative in both years.

## BUY1 / BUY2 split

BUY1 is negative on both symbols and both years.

BUY2 is sparse and does not provide a robust rescue. Examples:
- BTC BUY2 pooled: +1.25R EV about -0.006R; +3R about -0.160R.
- ETH BUY2 pooled: +2R about +0.006R but +3R about -0.097R.
- Some 2025 BUY2 cells turn positive, but samples are only ~70-75 legs and the pattern does not replicate 2024.

Treat these as noise/regime hints, not production branches.

## Native RSI50 management caveat

This observer was intentionally designed as an ENTRY-PATH study, not an exact replay of post-RSI50 production management. The production v11.16.11 manager closes 40% at RSI50, then applies BE/trailing and later RSI70 handling; the observer retires sensing at RSI50.

The event stream does contain the actual RSI50 trigger price, allowing a descriptive pre-TP1 check:
- among BUY1 legs that reach RSI50, average R at RSI50 is about +0.914R BTC pooled and +0.803R ETH pooled;
- nevertheless only ~47.0% BTC BUY1 and ~50.9% ETH BUY1 reach RSI50 before the common stop;
- exiting the whole leg at first RSI50-or-stop is still negative on both symbols (about -0.10R BTC BUY1 pooled and -0.08R ETH BUY1 pooled).

If only 40% is banked at RSI50 and the remaining 60% is assumed to scratch at BE, the expectation is substantially negative. Therefore the old profitable MT5 result must have depended materially on later runner/trailing/account-state selection if it is to survive at all.

A true final verdict on the *complete legacy managed strategy* would require an exact native-cycle virtual replay including 40% RSI50 partial, BE-net, 1.50 ATR trail, RSI70 partial and runner. The present data are enough to reject the claim that the underlying RSI entry itself has a large robust fixed-R edge.

## Decision

- RSI v11.16.11 raw ENTRY EDGE on BTC: REJECT.
- RSI v11.16.11 raw ENTRY EDGE on ETH: REJECT.
- BUY1 broad: REJECT.
- BUY2: no robust rescue; REJECT as standalone branch.
- Do NOT infer that every possible managed RSI implementation is disproven: the exact legacy native manager has not been replayed end-to-end here.
- Do NOT tune RSI thresholds from this sample.

Next rational choices:
1. if preserving the historical RSI sleeve is important, build one exact v11.16.11 native-management emulator and test it unchanged over the same 2024-2025 sample;
2. otherwise stop spending research budget on the legacy RSI entry and prioritize Momentum cross-asset tests / genuinely new families.
