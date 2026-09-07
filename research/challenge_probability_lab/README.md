# Guardian Challenge Probability Lab

Version: **v1.00**

## Purpose

Guardian already evaluates strategy quality with expectancy, PF, stability, costs and bootstrap evidence. This lab answers a different operational question:

> **What is the probability that the realised strategy process reaches a challenge target before a daily or overall drawdown rule is breached?**

The selection objective is **probability of passing**, not expected terminal profit.

## Simulation model

- Takes one or more real trade CSVs with realised outcome in **R**.
- Groups the observed trade process into calendar days.
- Resamples **contiguous circular moving blocks of days** (default: 5 days), rather than iid-shuffling trades. This preserves observed same-day clustering and short regime persistence.
- Uses common random paths across all risk levels so comparisons are paired and lower-noise.
- Default risk grid: **0.10 / 0.15 / 0.20 / 0.25 / 0.33 / 0.50% per trade**.
- Default sizing basis is initial/reference balance, matching Guardian's `g_detected_base_cap` risk convention.
- Tests target, daily-DD and max-DD boundaries after every atomic trade outcome.
- Reports timeouts explicitly at the configured Monte-Carlo horizon.

## Outputs per risk

- pass probability + Wilson 95% CI;
- daily-DD violation probability;
- max-DD violation probability;
- any-DD violation probability;
- timeout probability;
- median/P25/P75/P90 calendar days to pass;
- median and P90 trades to pass;
- median, P90, P95, P99 and worst-observed maximum drawdown;
- risk selected specifically to maximize pass probability.

The CLI writes JSON, CSV and Markdown from one run.

## Important DD boundary

With ordinary Guardian `TRADES.csv`, the lab knows the realised `net_r` but usually **does not know synchronized floating equity inside the trade**. Therefore, without an adverse-excursion column, daily/max-DD probabilities are **atomic/closed-equity estimates** and can understate real floating-equity breaches.

If the source export contains a signed worst adverse excursion in R (for example `mae_r_signed <= 0`), pass it with `--adverse-r-column`. That improves each atomic trade's intratrade DD check, but simultaneous adverse excursions of overlapping positions still require synchronized mark-to-market portfolio data.

This limitation must remain visible in every result; it is not legitimate to call an atomic trade bootstrap an exact prop-firm floating-equity simulator.

## Input compatibility

The loader accepts comma, semicolon or tab-delimited CSV. It auto-detects Guardian-style `net_r` and `entry_time`. You can override both. If a source contains an already normalized prop-firm/challenge day key, pass it with `--day-column`; otherwise the exported timestamp date defines the day block.

Example with a standard compact Guardian result:

```powershell
python research\challenge_probability_lab\challenge_probability_lab_v1_00.py `
  --input D:\path\to\trades_compact.csv `
  --stage DEV_2024_2025 `
  --day-column day_key `
  --profile research\challenge_probability_lab\guardian_reference_profile_v1_00.json `
  --paths 20000 `
  --out-prefix D:\MT5_Backtests\reports\challenge_lab\D0XX_DEV_CHALLENGE_LAB_V100
```

For a portfolio, repeat `--input` for every compatible strategy/symbol file. Trades sharing an observed date remain in the same day block, preserving observed cross-sleeve clustering when the source histories are synchronized.

## Challenge profiles

Rules are configuration, not alpha. Keep them separate from the strategy:

- `profit_target_pct`
- `daily_loss_pct`
- `max_loss_pct`
- `max_loss_anchor`: `initial` or `trailing_eod`
- `risk_basis`: `initial` or `current`
- `max_days`
- `block_days`

The included reference profile is intentionally generic. **Verify the actual active prop-firm programme/rules before operational use.**

## Scientific use

Use the Lab only after the underlying trade log itself is acceptable evidence. A high simulated pass probability cannot rescue a strategy that failed its alpha/OOS gates; leverage changes the path, not the expectancy.

When comparing risks, keep the input trades, seed, block length, challenge profile and Monte-Carlo horizon frozen. Do not tune a strategy on the Lab outcome and then call the same history validation.
