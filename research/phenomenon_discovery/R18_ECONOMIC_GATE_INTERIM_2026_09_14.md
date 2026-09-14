# R18 Economic Gate — Interim Result — 2026-09-14

## Status

R18 remains alive but is not yet economically validated.

The confirmed statistical phenomenon survives causal next-M5-open translation before costs, but the available cost budget is small.

## Frozen economic translation

- XAUUSD M5
- shock definition unchanged: abs(current M5 return) / sample stdev(previous 48 contiguous M5 returns) >= 2.0
- contrarian direction
- executable entry: next M5 open after shock close
- frozen horizons: 1, 2, 4, 8, 16 bars
- no SL/TP/trailing/sizing optimization
- non-overlap audit
- 2025 unopened
- 2026 unopened

## Non-overlap break-even all-in costs

### Discovery
- 1b: 0.1548 bp
- 2b: 0.1572 bp
- 4b: 0.0199 bp
- 8b: -0.0049 bp
- 16b: 0.1696 bp

### Confirmation
- 1b: 0.3230 bp
- 2b: 0.2677 bp
- 4b: 0.3356 bp
- 8b: 0.4530 bp
- 16b: 0.7757 bp

## Known FTMO commission floor

FTMO published Metals CFD commission of 0.0007% of volume per side. This corresponds to 0.07 bp per side, or 0.14 bp round trip, before spread and slippage.

For the frozen primary horizons in confirmation this leaves approximately:
- 1b: 0.1830 bp for spread + slippage
- 2b: 0.1277 bp for spread + slippage

This is not yet a pass/fail verdict. The remaining required evidence is the actual executable XAUUSD spread/slippage distribution under FTMO-like conditions, especially around R18 volatility shocks.

## Scientific decision

Do not open 2025 yet.
Do not optimize the R18 threshold, lookback, direction, or horizons.
Do not reject R18 using an arbitrary cost assumption.
Next gate: independently measure executable costs and compare them with the frozen break-even budgets above.
