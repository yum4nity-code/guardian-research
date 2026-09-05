# RSI Sniper v11.16.11 — XAUUSD + EURUSD long-history entry-path verdict

Date: 2026-09-05

Source population: cumulative corrected FILEBOOTSTRAP observer output. Signal semantics unchanged: `V11_16_11_CLOSED_BAR`. This is an ENTRY-PATH study, not an exact replay of post-RSI50 native management.

## Integrity / populations

New sessions present:
- XAUUSD: n=2,515 accepted virtual legs = 2,409 BUY1 + 106 BUY2
  - 2024: 1,241
  - 2025: 1,274
- EURUSD: n=2,004 accepted virtual legs = 1,940 BUY1 + 64 BUY2
  - 2024: 1,257
  - 2025: 747

Same-M1 stop/target ambiguity counts excluded from fixed first-touch EV:
- XAUUSD: 11
- EURUSD: 21

## XAUUSD — broad fixed first-touch

Pooled:
- +0.5R: -0.162R
- +1R: -0.147R, 95% CI ~[-0.186,-0.108]
- +1.25R: -0.168R
- +1.5R: -0.182R
- +2R: -0.202R
- +2.5R: -0.196R
- +3R: -0.172R, 95% CI ~[-0.236,-0.109]

2024:
- EV1 -0.175R
- EV2 -0.213R
- EV2.5 -0.237R
- EV3 -0.219R

2025:
- EV1 -0.120R
- EV2 -0.191R
- EV2.5 -0.155R
- EV3 -0.126R

BE managers remain negative:
- pooled BE@1 -> 2R: -0.134R
- pooled BE@1 -> 3R: -0.109R
- pooled BE@1.25 -> 2R: -0.152R
- pooled BE@1.25 -> 3R: -0.129R

RSI50 before structural stop: ~44.3%
RSI70 before structural stop: ~19.5%

BUY1 is negative in both years and throughout the target grid.

BUY2 is sparse and unstable:
- pooled n=106: EV3 +0.115R
- 2024 n=57: EV3 -0.158R
- 2025 n=49: EV3 +0.447R
This sign flip plus tiny cell size is not a valid rescue.

Decision: **XAUUSD legacy RSI entry edge REJECT.**

## EURUSD — broad fixed first-touch

Pooled:
- +0.5R: -0.082R
- +1R: -0.069R, 95% CI ~[-0.113,-0.025]
- +1.25R: -0.054R
- +1.5R: -0.052R
- +2R: -0.044R
- +2.5R: -0.043R
- +3R: -0.070R, 95% CI ~[-0.144,+0.004]

2024:
- EV1 -0.105R
- EV2 -0.080R
- EV2.5 -0.087R
- EV3 -0.115R

2025:
- EV1 -0.009R
- EV1.25 +0.005R
- EV2 +0.016R
- EV2.5 +0.030R
- EV3 +0.004R

Pooled BE managers are essentially flat, not a usable edge:
- BE@1 -> 2R: +0.008R
- BE@1 -> 3R: -0.002R
- BE@1.25 -> 2R: +0.021R
- BE@1.25 -> 3R: -0.001R

Year split shows regime dependence rather than robustness:
- 2024 BE variants remain negative (~-0.029R to -0.056R)
- 2025 BE variants improve (~+0.083R to +0.108R), still below the user's large-edge standard and not replicated in 2024.

RSI50 before structural stop: ~46.3%
RSI70 before structural stop: ~20.1%

BUY1 pooled remains negative. BUY2 pooled is superficially better (n=64, EV2 +0.172R / EV2.5 +0.148R / EV3 +0.125R), but this is driven by only 20 BUY2 events in 2025; 2024 n=44 does not replicate. Do not promote or tune from this split.

Decision: **EURUSD legacy RSI broad entry edge REJECT / 2025 improvement is regime-specific and below robustness standard.**

## Cross-asset conclusion

Adding XAUUSD and EURUSD does not rescue the legacy v11.16.11 raw RSI entry family.

Across BTC, ETH, XAU and EUR:
- broad fixed first-touch entry EV is negative or near-zero;
- no market shows a recurring >=~+0.15R pre-cost broad edge across both 2024 and 2025;
- sparse BUY2 subcells can look attractive in isolated years but fail replication.

Do not retune RSI thresholds from these samples.

Critical caveat unchanged: this observer retires sensing at RSI50 and does not emulate the exact native post-RSI50 manager (40% TP1, BE-net, 1.50 ATR trailing, RSI70 partial, runner). Therefore the exact fully managed strategy is not disproven end-to-end, but the entry signal itself is now rejected across four tested assets.
