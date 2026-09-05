# D017 Momentum — long-history BTC/ETH first verdict

Date: 2026-09-05
Status: BROAD ENGINE FAILS LARGE-EDGE STANDARD / BTC SELL IS A RECURRING CLUE ONLY / DO NOT RETUNE

## Provenance

Rules and analysis were frozen before these results in:
- `research/campaigns/D017_MOMENTUM_LONG_HISTORY_DIAGNOSTIC_LOCK_2026_09_04.md`
- `research/results/D017_RSI_LONG_HISTORY_STATIC_AUDIT_2026_09_04.md`

Diagnostic EA:
- `research/ea/D017_Momentum_VirtualDiagnostic_1_01_STATIC_CONFORMANCE.mq5`

Test protocol:
- BTCUSD and ETHUSD
- 2024-01-01 through 2025-12-31
- M1 tester chart, engine internally M5/H1
- Every tick
- virtual signals only; no account / prop-firm state selection

## Input integrity / duplicate runs

Received cumulative files contain duplicate sessions:
- BTCUSD: two sessions, 1,710 trades each, content-identical after removing `session_id`.
- ETHUSD: two sessions, 1,144 trades each. First-touch statistics are identical; only five signal timestamps differ by a few seconds in late 2025 because tester tick arrival time differs, without changing signal prices or first-touch EV.

For all figures below one canonical session per symbol is used:
- BTCUSD n=1,710 = 991 in 2024 + 719 in 2025.
- ETHUSD n=1,144 = 727 in 2024 + 417 in 2025.
- combined unique population n=2,854.

48h path coverage is essentially complete: BTC has 1,707 explicit 48h snapshots and ETH 1,143; the remaining edge-of-window events use their latest available 8h/24h snapshot. Same-M1 ambiguities are excluded when relevant.

## Fixed first-touch EV — overall, before commission/slippage

### BTCUSD

| Target | Resolved | EV |
|---|---:|---:|
| +0.5R | 1,709 | -0.052R |
| +1R | 1,707 | -0.015R |
| +1.25R | 1,707 | -0.001R |
| +1.5R | 1,705 | +0.013R |
| +2R | 1,702 | +0.029R |
| +2.5R | 1,702 | +0.063R |
| +3R | 1,698 | +0.074R |

### ETHUSD

| Target | Resolved | EV |
|---|---:|---:|
| +0.5R | 1,144 | -0.036R |
| +1R | 1,143 | -0.008R |
| +1.25R | 1,141 | -0.006R |
| +1.5R | 1,141 | +0.004R |
| +2R | 1,139 | -0.018R |
| +2.5R | 1,136 | -0.033R |
| +3R | 1,135 | -0.031R |

### BTC + ETH combined

- +1R: -0.012R on 2,850 resolved.
- +1.25R: -0.003R on 2,848.
- +1.5R: +0.009R on 2,846.
- +2R: +0.011R on 2,841.
- +2.5R: +0.025R on 2,838.
- +3R: +0.032R on 2,833.

This is far below the predeclared large-edge standard (~+0.15R minimum preference, ideally +0.20R+ recurring).

## Year stability

### BTCUSD

- 2024 n=991: EV1 -0.010R / EV1.25 +0.016R / EV1.5 +0.048R / EV2 +0.070R / EV2.5 +0.096R / EV3 +0.118R.
- 2025 n=719: EV1 -0.021R / EV1.25 -0.024R / EV1.5 -0.035R / EV2 -0.027R / EV2.5 +0.018R / EV3 +0.014R.

The attractive 2024 broad BTC behavior largely disappears in 2025.

### ETHUSD

- 2024 n=727: EV1 +0.010R / EV1.25 +0.012R / EV1.5 +0.021R / EV2 -0.001R / EV2.5 +0.031R / EV3 +0.047R.
- 2025 n=417: EV1 -0.038R / EV1.25 -0.037R / EV1.5 -0.026R / EV2 -0.046R / EV2.5 -0.144R / EV3 -0.167R.

ETH deteriorates materially in 2025.

## Predeclared BUY / SELL split

### BTC SELL — only recurring clue

BTC SELL is positive in both years at larger targets:
- 2024 n=359: EV2 +0.111R / EV2.5 +0.150R / EV3 +0.170R.
- 2025 n=402: EV2 +0.053R / EV2.5 +0.114R / EV3 +0.085R.
- pooled n=761: EV2 +0.080R / EV2.5 +0.131R / EV3 +0.125R.

Approximate Wilson EV interval pooled:
- +2.5R: +0.018R to +0.251R.
- +3R: +0.002R to +0.258R.

This is a genuine recurring clue, but it still does **not** meet the locked production threshold after pooling and has no cost cushion.

BTC BUY is not attractive:
- pooled n=949: EV2 -0.012R / EV2.5 +0.008R / EV3 +0.033R.
- 2025 BUY is clearly negative (EV2 -0.127R, EV3 -0.076R).

ETH has no useful recurring side branch:
- pooled BUY EV2 +0.014R / EV3 +0.023R.
- pooled SELL EV2 -0.049R / EV3 -0.085R.

## Predeclared BE management diagnostics

### BTC overall
- BE@+1R -> +2R: +0.013R.
- BE@+1R -> +3R: +0.054R.
- BE@+1.25R -> +2R: +0.018R.
- BE@+1.25R -> +3R: +0.054R.
- descriptive 25%@+2R, BE armed +1.25R, 75% runner to +3R: +0.045R.

### ETH overall
- BE@+1R -> +2R: -0.020R.
- BE@+1R -> +3R: -0.040R.
- BE@+1.25R -> +2R: -0.022R.
- BE@+1.25R -> +3R: -0.043R.
- descriptive 25%@+2R / BE1.25 / runner3: -0.040R.

### BTC SELL only

The predeclared side split remains the only interesting branch:
- pooled BE@1 -> 3R: +0.135R.
- pooled BE@1.25 -> 3R: +0.123R.
- descriptive 25%@2 / BE1.25 / runner3: +0.109R.

Year-by-year descriptive comparator:
- 2024 BTC SELL: +0.112R.
- 2025 BTC SELL: +0.106R.

Again: repeatable, but still below the required edge standard and before realistic costs.

## Important comparison with the spectacular short-window Guardian result

The known 2026-09-02 BTC Momentum-only isolation baseline was:
- +7,353.28 USD
- PF 1.68
- max equity DD 1.80%
- 115 trades

The new two-year intrinsic-signal observer produces 1,710 BTC signals and only a few hundredths of R broad EV. Therefore the old spectacular short-window result **does not generalize to the unrestricted two-year Momentum signal population**.

This does not prove the historical P/L was false. It means one or more of the following mattered materially:
- the short window/regime itself;
- Guardian/account-state selection (daily trade cap, cooldowns, position limits, etc.);
- exact native manager (BE1.25, 25% TP at 2R, ATR trailing) selecting/realizing path differently;
- interaction with the specific production sample.

Because the current diagnostic deliberately removed account-state selection, it measures intrinsic signal quality rather than exact portfolio P/L.

## Cost caveat

The virtual entry uses current ask for BUY and bid for SELL and retains the production spread/SL gate, so entry spread is partly reflected in R geometry. It does **not** fully model commission, slippage, swap, or ask-side SELL stop execution. Any small positive EV should therefore be treated as an upper-bound clue rather than production-ready net edge.

## Decision

**Broad D017 Momentum FAILS the long-history large-edge standard on BTCUSD and ETHUSD.**

Do not keep the broad engine in production merely because the short-window backtest was spectacular.

However, do not throw away the research lineage completely yet: **BTC SELL Momentum is a predeclared, recurring branch worth preserving as a hypothesis/watchlist**, because it stays positive in both 2024 and 2025. Its pooled edge (~+0.13R at 2.5R / ~+0.125R at 3R) is still too small for production under the user's standard.

No parameter retuning is authorized from this sample. The next decision should wait for the RSI long-history result. If RSI also fails, return to genuinely new strategy families. If RSI survives strongly, prioritize RSI. If a future D017 follow-up is justified, it must be a prospectively locked **BTC SELL-only** validation or exact-native-manager test, not a post-hoc threshold sweep.
