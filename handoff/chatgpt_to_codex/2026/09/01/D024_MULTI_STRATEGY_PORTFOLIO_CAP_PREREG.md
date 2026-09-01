# D024 — Multi-strategy portfolio overlap / position-cap study

STATUT: PREREGISTERED / BLOCKED UNTIL MULTIPLE STRATEGIES HAVE VALID TRADE LOGS

## Question

Do not treat `max positions per symbol = 1/2/3/4` as a permanent doctrine. Test whether a hard ticket-count cap adds value once Guardian already enforces an account-level open-risk budget.

The scientific question is narrow: with exactly the same frozen strategy signals/trades, does capping concurrent positions per symbol at 1, 2, 3 or 4 improve portfolio risk/return versus allowing unlimited same-symbol positions subject only to the existing account open-risk cap?

## Frozen policies

Hold the account open-risk cap fixed at **1.00%** for this experiment so the only portfolio-policy variable is the same-symbol position-count cap.

Compare exactly these five policies:

- `MAX1`: max 1 concurrent position per symbol.
- `MAX2`: max 2 concurrent positions per symbol.
- `MAX3`: max 3 concurrent positions per symbol.
- `MAX4`: max 4 concurrent positions per symbol.
- `RISK_ONLY`: no same-symbol count cap; only the fixed 1.00% account open-risk cap.

No optimization or intermediate caps after outcomes are opened.

Each strategy keeps its own frozen requested risk. A new trade is rejected if accepting it breaches the policy cap or the 1.00% account open-risk cap. No dynamic resizing in D024 V0.

Signals are processed by actual entry timestamp. Exact timestamp ties use a performance-blind deterministic order: `strategy_id`, then `trade_id`, lexicographically. Same-symbol opposite-direction trades are allowed and reported, not silently netted or blocked.

## Two-stage design

### D024A — overlap diagnostic

Can run from standardized realized trade logs once at least two independently validated strategies have compatible logs.

Required canonical columns:

`strategy_id, trade_id, symbol, entry_time, exit_time, direction, risk_pct, pnl_r`

Outputs compare acceptance/rejection, realized PnL, closed-trade PF, closed-equity diagnostic DD, worst closed-PnL day, symbol-cap rejections, account-risk rejections and opposite-direction overlap.

Important: D024A is **diagnostic only**. Trade-level realized logs cannot reconstruct floating P/L between entry and exit, therefore D024A must never claim FTMO drawdown safety or select the production cap.

### D024B — final portfolio validation

A production decision is forbidden until synchronized mark-to-market/equity data exist for the candidate strategy portfolio. D024B must replay the same five frozen policies on a common time grid and measure at minimum:

- total net return;
- maximum floating equity drawdown;
- worst FTMO-style daily loss including floating P/L and costs;
- maximum simultaneous open risk;
- same-symbol and common-currency concentration;
- frequency and PnL of overlapping strategies;
- opposite-direction overlap cost;
- marginal contribution of the 2nd/3rd/4th same-symbol position;
- strategy-level contribution and concentration;
- monthly stability.

The final policy must be chosen for robust risk-adjusted behavior, not simply highest net profit. If MAX2/MAX3/MAX4/RISK_ONLY are materially equivalent, prefer the simpler/lower-exposure policy. If hard caps add no robust protection beyond the risk budget, production may use `RISK_ONLY` with a separate purely technical emergency ticket ceiling.

## Prepared engine

ChatGPT already implemented D024A as:

`d024a_multistrategy_overlap_diagnostic.py`

SHA256: `92f12a9a22c4aa0a326dad9adb1b5c70465c4c03ec8022e3c17af9e5ddf88e84`

It has passed Python syntax validation and a synthetic overlap test covering MAX1/MAX2/MAX3/MAX4/RISK_ONLY, account-risk rejection and opposite same-symbol overlap.

## Do not do

- Do not change the 1.00% account open-risk cap inside D024 V0; that is a different experiment.
- Do not select a cap from D024A alone.
- Do not retune individual strategies during the portfolio-policy test.
- Do not open locked OOS to choose the cap.
- Do not automatically block same-symbol strategies simply because they overlap.
- Do not automatically net opposite strategies in the research replay.
- Do not spend Codex quota rewriting D024A.

## Activation condition

Leave D024 blocked until at least two independently validated strategies have standardized compatible trade logs. Run D024A first. D024B becomes eligible only when synchronized mark-to-market data are available for the relevant validated strategy set.
