# D035-E1 — causal BTC+ETH dual-source diagnostic — verdict

Date: 2026-09-06 Europe/Paris
Status: **E1_DO_NOT_ADVANCE / D035 FAMILY CLOSED FOR IMMEDIATE CONFIRMATION**
Scientific status: **EXPLORATORY_SAME_SAMPLE_NOT_CONFIRMATION**

Canonical preregistration: `research/campaigns/D035_E1_CAUSAL_DUAL_SOURCE_DIAGNOSTIC_PREREGISTRATION_2026_09_06.md`.

## Returned pack

User returned `D35 CASUAL.zip` with the causal dual-source event table, target returns, per-target summaries, offset QA, checkpoints, report and verdict JSON.

The causal rule was respected: same frozen D035 single-source shock definitions, BTC and ETH both required within <=5 minutes, and tradable signal timestamp moved to the **later/second qualifying source shock**. Development remained 2024-2025. **2026-H1 was not touched.**

## Primary XLMUSD gate

Causal dual events: **973**.
Primary XLMUSD rows with +15m response: **870**.
Mean entry spread: **8.246 bps**.

Frozen XLMUSD metrics:
- mean executable SHORT +15m: **+6.705 bps**;
- median executable SHORT +15m: **0.000 bps**;
- mean control +15m: **-6.786 bps**;
- event-control differential +15m: **+13.490 bps**;
- day-cluster bootstrap raw +15m: **[+1.996,+11.549] bps**;
- day-cluster bootstrap differential +15m: **[+8.793,+18.302] bps**;
- mean executable +30m: **+3.697 bps**;
- year mean executable +15m: **2024 +4.104 bps; 2025 +9.935 bps**.

Frozen advancement gates:
1. n >=200: **PASS**
2. mean executable +15m >=15 bps: **FAIL**
3. median executable +15m >0: **FAIL**
4. raw +15m bootstrap lower >0: **PASS**
5. mean event-control differential +15m >=10 bps: **PASS**
6. differential bootstrap lower >0: **PASS**
7. mean executable +30m >0: **PASS**
8. both 2024 and 2025 executable +15m positive: **PASS**

Final: **6/8 -> E1_DO_NOT_ADVANCE**.

## Interpretation

Moving the signal to the causal second shock removes the earlier look-ahead issue. A real conditional response remains visible: XLMUSD has a positive +15m mean, positive raw bootstrap lower bound, and a strong event-vs-control differential. However the executable magnitude is only **+6.7 bps**, less than half the frozen +15 bps economic hurdle, and the median trade is exactly zero. Therefore the effect is not large enough to justify consuming the untouched 2026 confirmation sample.

The diagnostic source-asset rows are stronger but are not the preregistered primary target and remain same-sample diagnostics:
- ETHUSD: n=871, mean executable +15m **+14.999 bps**, median **+8.310 bps**, differential **+19.038 bps**;
- BTCUSD: n=871, mean executable +15m **+10.359 bps**, median **+6.343 bps**, differential **+11.849 bps**.

These rows must **not** be promoted post hoc into a 2026 confirmation simply because they look better than XLMUSD. Doing so would violate the frozen E1 advancement rule and reintroduce target selection after seeing the results. They may only motivate a future separately preregistered hypothesis on genuinely fresh data if the project later chooses to revisit this mechanism.

## Decision

- **Do not run D035-C1 on 2026-H1.**
- **Do not retune the 5m window, source thresholds, horizon, direction or target on the inspected 2024-2025 sample.**
- Close D035 as an immediate strategy-development branch.
- Preserve the result as evidence that synchronized BTC/ETH deleveraging has a measurable short-horizon cross-market response, but the frozen FundedNext XLM implementation lacks sufficient economic magnitude.
- Proceed to the already-decided META-A1 edge-attribution work on the legacy RSI/Momentum system rather than launching another blind strategy family.
