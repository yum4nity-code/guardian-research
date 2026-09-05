# D034 Gold/Oil abnormal-return momentum — prepared

Date: 2026-09-05
Status: SCANNER PREPARED / USER COMPILE + TEST REQUIRED

Preregistration:
`research/campaigns/D034_GOLD_OIL_INTRADAY_ABNORMAL_RETURN_MOMENTUM_PREREGISTRATION_2026_09_05.md`
Commit: `3e3166bf08f03bf958de573f98250f98697dc9d6`

Scanner delivered to user:
`D034_GoldOil_AbnormalReturn_Momentum_FeatureLab_v1_00.mq5`
SHA-256: `842ca596a017229c27857030589c0f5b432e52313364f7f7a27c73890da138fe`

Classification: `ADAPTATION_CAUSAL_CFD_TRANSFER`.

Frozen rule:
- markets: XAU/GOLD and WTI/USOIL/XTI only;
- source family Caporale & Plastun 2021, Strategy 1;
- causal dynamic threshold from prior 252 completed D1 open-to-close returns;
- positive abnormal threshold = mean + 2sd; negative = mean - 2sd;
- GOLD detection hours applied to tester/server clock: positive >=17:00, negative >=19:00;
- OIL: positive >=16:00, negative >=19:00;
- first threshold crossing after the relevant timing hour enters in abnormal-return direction;
- max one entry/day;
- no stop/TP/trailing/Guardian;
- exit last observed executable quote of same calendar day;
- spread embedded via executable BID/ASK;
- signal window 2024-01-01 through 2026-06-30;
- tester should start around 2022-11-01 or earlier and end at least 2026-07-02.

Passive features only: Z60/Z120/Z252, reconstructed RSI14 H1, reconstructed ATR14 H1/D1, 1h/4h/8h/24h returns, prior-day return, current-day range, D1 SMA20/50/200 distances, MFE/MAE. They never filter v1.00.

Scanner output QA before delivery:
- token-aware braces/parens/brackets balances all zero;
- EVENTS header/row = 49/49 columns;
- SUMMARY header/rows = 12/12 columns;
- immediate header flush + runtime FileSize QA;
- ChatGPT has NOT MetaEditor-compiled it.

User execution:
1. compile v1.00;
2. run XAUUSD and the available WTI/USOIL/XTI symbol separately on M1 / `1 minute OHLC`;
3. no input edits;
4. return EVENTS/SUMMARY/RUN_INFO from both markets;
5. decide each market strictly from preregistered gate; do not move timing hours, k, lookback or add filters to rescue the same sample.
