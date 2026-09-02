# Guardian v11.16.13C — wider BUY1 SL audit

Base: `Guardian_D017_PropFirmAuto_v11_16_13B_MINIMAL_FIX_FROM_TRUE_12.mq5`

The 13B base itself was built from the verified v11.16.12 source (`SHA256 9307f5daf09c243b4997fb59f82a71e5baa85992a5f348fd3bf9e5f841b8122b`).

## Requested change

Keep all 13B fixes and add the wider BUY1 stop experiment without changing the rest of Guardian.

- New `InpRSIBuy1SLBufferATR = 0.50`.
- Auto BUY1 stop: `low episode - 0.50 ATR`.
- Manual RSI-adopted M-BUY1 stop: `low episode - 0.50 ATR`.
- Existing `InpRSISLBufferATR = 0.15` is retained for BUY2 structural stop logic.
- Dollar-risk budget remains unchanged. Existing sizing logic receives the farther BUY1 stop and therefore computes a smaller volume automatically.
- For an oversized manual M-BUY1, existing manual-risk reduction remains responsible for trimming volume back to the cycle budget.

## Explicit non-changes

No changes were made to Momentum signal logic/timeframes, RSI ARM/recross rules, BUY2 divergence/retest rules, TP1 RSI50/BE/trailing, TP2 RSI70/runner, RSI markers/chart objects, notification logic, risk budget percentage, prop-firm guards, or trade lifecycle logic. Journal/HUD content is unchanged except version identification.

## Mechanical diff versus 13B

Only these changes exist:
1. filename/version identifiers;
2. one new BUY1-specific input;
3. M-BUY1 stop reference switched to `InpRSIBuy1SLBufferATR`;
4. auto BUY1 stop reference switched to `InpRSIBuy1SLBufferATR`;
5. validation of the new input.

BUY2 still uses `double structural=g_rsi_second_low-InpRSISLBufferATR*atr;` with `InpRSISLBufferATR = 0.15`.

## Validation still required

MetaEditor/MQL5 compiler is not available in this environment. Compile validation must therefore be done in MetaEditor. First sanity backtest should verify zero shorts in RSI-only mode, normal RSI journal wording, normal markers/HUD, no stale `CRYPTO_COOLDOWN` when consecutive-loss cooldown is zero, and trade counts in the same order of magnitude as the clean baseline.