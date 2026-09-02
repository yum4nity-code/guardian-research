# RSI BUY1 wider-SL candidate — 2026-09-02

Candidate: Guardian v11.16.14 RSI BUY1 WIDER SL 0.50 ATR.
Base: v11.16.13 MANUAL RSI ROUTING.
Status: research candidate; compile and backtest validation required before any production promotion.

Single strategy change:
- automatic BUY1 and adopted manual M-BUY1 use a structural stop at first oversold-episode low minus 0.50 ATR instead of 0.15 ATR;
- BUY2/common-stop structural buffer remains baseline 0.15 ATR;
- RSI thresholds, divergence/retest conditions, exits and Momentum are unchanged.

Rationale: observed live cases show BUY1 can stop extremely close to the second oversold low before BUY2 has time to validate. A 0.50 ATR first-leg buffer adds 0.35 ATR of breathing room while remaining a controlled first test rather than jumping to 1.0 ATR.

Risk behavior: RSI automatic lot sizing already uses actual entry-to-SL distance, so a wider BUY1 stop automatically produces fewer lots while keeping the dollar cycle-risk budget unchanged, subject to broker lot/margin constraints. Manual M-BUY1 adoption uses the existing risk-reduction path if the manually entered volume is too large for the widened stop.

Proper A/B: v11.16.13 BUY1 buffer 0.15 ATR vs v11.16.14 BUY1 buffer 0.50 ATR, identical symbol/date/settings. Track PF, net, equity DD, trades, BUY1 stopped before TP1, BUY2 armed before SL, BUY2 executed, actual risk and volume.
