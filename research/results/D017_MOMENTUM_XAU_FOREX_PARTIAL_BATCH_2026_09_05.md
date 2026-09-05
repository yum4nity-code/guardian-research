# D017 Momentum — XAU / Forex partial long-history batch — 2026-09-05

Period: 2024-01-01 -> 2025-12-31. Diagnostic: `D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`. M1 tester, Every tick, defaults. Pure virtual signal-path analysis; no exact Guardian account/news/portfolio gating and no exact realized native trail.

Received cumulative files contain canonical non-crypto sessions for XAUUSD, EURUSD, GBPUSD, USDJPY. USDCAD is not present in this batch. BTC/ETH duplicate sessions were ignored; one canonical session per symbol was used.

## Populations
- XAUUSD: 676 signals = 327 (2024) + 349 (2025)
- EURUSD: 476 = 239 + 237
- GBPUSD: 444 = 178 + 266
- USDJPY: 536 = 247 + 289

## Broad fixed first-touch EV

| Symbol | +1R | +2R | +2.5R | +3R |
|---|---:|---:|---:|---:|
| XAUUSD | -0.037R | -0.033R | +0.010R | +0.003R |
| EURUSD | +0.032R | -0.048R | -0.152R | -0.220R |
| GBPUSD | -0.053R | -0.088R | -0.049R | -0.024R |
| USDJPY | +0.013R | +0.014R | -0.039R | -0.024R |

No broad non-crypto symbol clears the user's large-edge standard.

## Year stability

### XAUUSD
- 2024: EV1 -0.067R / EV2 -0.126R / EV2.5 -0.106R / EV3 -0.113R
- 2025: EV1 -0.009R / EV2 +0.055R / EV2.5 +0.119R / EV3 +0.112R
- Strong regime flip. XAU broad is not robust.
- XAU BUY is attractive only in 2025: EV2.5 +0.196R / EV3 +0.190R, but 2024 BUY is negative (-0.066R / -0.074R respectively). Do not promote post-hoc 2025 XAU BUY.

### EURUSD
- 2024: EV1 +0.059R / EV2 +0.034R / EV2.5 -0.045R / EV3 -0.150R
- 2025: EV1 +0.004R / EV2 -0.130R / EV2.5 -0.260R / EV3 -0.289R
- EUR broad rejects.
- EUR SELL +1R repeats mildly positive in both years: 2024 +0.043R, 2025 +0.065R, pooled +0.052R (n=232 resolved, Wilson-style EV interval about -0.077..+0.178R). Too small for promotion.

### GBPUSD
- 2024: EV1 -0.029R / EV2 -0.047R / EV2.5 +0.015R / EV3 +0.054R
- 2025: EV1 -0.068R / EV2 -0.115R / EV2.5 -0.091R / EV3 -0.075R
- No robust side branch. Reject broad GBP Momentum.

### USDJPY
- 2024: EV1 +0.067R / EV2 +0.103R / EV2.5 +0.152R / EV3 +0.217R
- 2025: EV1 -0.032R / EV2 -0.060R / EV2.5 -0.197R / EV3 -0.223R
- Very strong regime flip. Broad USDJPY rejects.
- USDJPY SELL +1R repeats mildly positive in both years: 2024 +0.044R, 2025 +0.095R, pooled +0.075R (n=227 resolved; Wilson-style EV interval about -0.055..+0.202R). +2R also remains positive but tiny: +0.057R / +0.037R by year, pooled +0.045R.
- BE@1 -> 2R pooled USDJPY SELL ~+0.085R. Still below threshold and uncertainty crosses zero.

## Management comparators
Broad BE comparators do not rescue the population:
- XAU BE@1 -> 3R ~ -0.044R; BE@1.25 -> 3R ~ -0.065R
- EUR BE@1 -> 3R ~ -0.055R; BE@1.25 -> 3R ~ -0.108R
- GBP BE@1 -> 3R ~ -0.005R; BE@1.25 -> 3R ~ -0.007R
- USDJPY BE@1 -> 2R ~ +0.043R, but BE@1 -> 3R ~ 0.000R and BE@1.25 -> 3R ~ -0.004R

The descriptive Momentum comparator (25%@2R, BE@1.25, rest->3R; not exact native trail) is not attractive on the identified branches: EUR SELL ~-0.017R, USDJPY SELL ~-0.040R, XAU BUY ~-0.006R.

## Decision from current batch
- XAUUSD broad: REJECT
- EURUSD broad: REJECT
- GBPUSD broad: REJECT
- USDJPY broad: REJECT
- XAU BUY 2025: regime-specific descriptive clue only, not robust
- EURUSD SELL +1R: weak recurring clue only (~+0.05R), below threshold
- USDJPY SELL +1R / +2R: weak recurring clue only (~+0.075R / +0.045R), below threshold
- No non-crypto branch in this partial batch currently justifies assuming Guardian will rescue it. Guardian selection may materially alter results, but that must be tested prospectively rather than credited in advance.

USDCAD remains missing and should be analyzed when/if the user supplies that session. This partial verdict must not be misreported as a complete five-market batch.