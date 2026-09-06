# D036 Donchian Trend Breakout H1 V0 — Development Result

Date: 2026-09-06
Stage: DEV_2024_2025
Universe: BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, XAUUSD

## Initial scorer output

The six-ledger scorer initially reported:
- n = 2747
- total net R = +1357.74061128
- mean = +0.49426305 R/trade
- PF = 1.85266217
- 2024 = +1376.07140824 R
- 2025 = -18.33079696 R
- verdict = REJECT_V0 because the preregistered 2024-and-2025-positive gate failed.

## Integrity audit of extreme outliers

Two extreme winning trades were not economically valid market exits:

### EURUSD
- signal: 2024-06-26 12:00
- entry: 2024-06-26 13:00
- exit time: 2024-06-27 04:00
- side: SHORT
- entry = 1.06846
- initial stop = 1.06993
- exit channel = 1.06905
- recorded exit = -0.00008
- recorded net R = +724.36610169

### GBPUSD
- signal: 2024-06-26 10:00
- entry: 2024-06-26 11:00
- exit time: 2024-06-27 06:00
- side: SHORT
- entry = 1.26649
- initial stop = 1.26821
- exit channel = 1.26321
- recorded exit = -0.00032
- recorded net R = +737.74606872

Negative FX exit prices are impossible here and conflict with the simultaneously recorded positive channel levels. Both rows correspond to the single PnL fallback observed in each V1.02 FX run. The fallback prevented a missing ledger row but accepted the nonsensical exit price, turning the bad price into a huge synthetic profit.

## Corrected diagnostic excluding the two invalid rows

This is an integrity diagnostic, not a rescue optimization. Removing only the two impossible-price rows gives:
- n = 2745
- total net R = -104.37155913
- mean = -0.03802243 R/trade
- approximate PF = 0.93445458

Per-symbol corrected totals for the affected symbols:
- EURUSD: 475 valid rows, -66.50572483 R, approximate PF 0.7642
- GBPUSD: 475 valid rows, -52.87101601 R, approximate PF 0.8145

The originally reported SHORT contribution of +1280.16056179 R becomes -181.95160862 R after removing the two impossible-price rows; approximate SHORT PF becomes 0.7675. LONG contribution remains +77.58004949 R.

## Verdict

**REJECT_V0 — CLOSED.**

Reasons:
1. The frozen development gate requiring both 2024 and 2025 positive already failed before the integrity correction.
2. The apparent +1357.74 R aggregate was dominated by two impossible FX exit prices.
3. After removing only those two invalid rows, the development sample is negative overall with PF below 1.
4. No 2026-H1 confirmation is permitted.
5. No rescue tuning of the opened 2024-2025 sample.

Engineering follow-up: any future research harness must hard-reject non-positive or economically impossible exit prices before PnL fallback and must never convert an invalid market price into a valid PnL row.
