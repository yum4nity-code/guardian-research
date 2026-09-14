# R16-R20 Confirmation Result — 2026-09-14

Confirmation window:
- 2019-07-01 through 2024-12-31
- 2025 pre-OOS remained closed
- 2026+ remained sealed

## R18 — PASS

Frozen primary metrics:
- reversal_1b: mean +3.2680e-05, day-clustered t +6.55
- reversal_2b: mean +2.6174e-05, day-clustered t +3.87

Secondary horizons also retain the expected positive reversal sign:
- reversal_4b t +3.43
- reversal_8b t +2.89
- reversal_16b t +2.40

Result:
- Independent confirmation succeeds on sign and clustered significance.
- Economic gate may now be designed/opened before any 2025 pre-OOS.
- Thresholds, event definition, overlap handling, and horizons remain frozen.

## R19 — FAIL

Frozen primary metrics:
- breakout_1b: mean +9.5431e-06, day-clustered t +0.34
- breakout_4b: mean +3.8116e-05, day-clustered t +0.74

All tested breakout horizons remain positive in mean but clustered significance is weak:
- 2b t +1.07
- 8b t +1.41
- 16b t +1.08

Result:
- Fails frozen confirmation gate.
- Do not rescue by tuning PDH/PDL definition, ATR proximity, session, or horizon.

## R16 — FAIL as confirmed edge candidate

Frozen relabelled metrics from discovery:
- reversal_2b: mean -4.7039e-05, day-clustered t -1.28
- reversal_4b: mean -4.5894e-05, day-clustered t -1.06

Sign is preserved, but magnitude/significance collapse materially versus discovery.

Result:
- Does not confirm as a robust phenomenon under the frozen definition.
- Do not tune/relabel further inside this study.

## Final funnel

- R16: discovery-interest only -> confirmation FAIL
- R17: discovery FAIL / not promoted
- R18: discovery PASS -> confirmation PASS
- R19: discovery PASS -> confirmation FAIL
- R20: discovery FAIL

Only R18 advances to the economic gate.

## Next permitted step

Design the R18 economic gate without inspecting 2025 and without opening 2026.

The economic gate must convert the confirmed phenomenon into a minimally-assumptive tradability test while preserving:
- shock definition
- M5 timeframe
- mean-reversion direction
- frozen event-generation logic

No parameter search is allowed merely to make the result profitable.
