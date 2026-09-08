# Guardian Challenge Probability Lab

Version: **v1.00 engine / v1.01 canonical post-validation pipeline**

## Purpose

Guardian already evaluates strategy quality with expectancy, PF, stability, costs and bootstrap evidence. This lab answers a different operational question:

> **What is the probability that the realised strategy process reaches a challenge target before a daily or overall drawdown rule is breached?**

The selection objective is **probability of passing**, not expected terminal profit.

## Simulation model

- Takes one or more real trade CSVs with realised outcome in **R**.
- Groups the observed trade process into calendar/challenge days.
- Resamples **contiguous circular moving blocks of days** (default: 5 days), rather than iid-shuffling trades. This preserves observed same-day clustering and short regime persistence.
- Uses common random paths across all risk levels so comparisons are paired and lower-noise.
- Default risk grid: **0.10 / 0.15 / 0.20 / 0.25 / 0.33 / 0.50% per trade**.
- Default sizing basis is initial/reference balance.
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

The engine writes JSON, CSV and Markdown from one run.

## Important DD boundary

With ordinary Guardian trade exports, the lab knows realised `net_r` but usually does **not** know synchronized floating equity inside the trade. Without adverse-excursion data, daily/max-DD probabilities are therefore **atomic/closed-equity estimates** and can understate real floating-equity breaches.

Canonical `adverse_r <= 0` improves intratrade DD checking for each trade, but simultaneous adverse excursions of overlapping positions still require synchronized mark-to-market portfolio data.

This limitation must remain visible in every result; an atomic trade bootstrap must never be presented as an exact prop-firm floating-equity simulator.

## Canonical future export contract

Future OOS/confirmation outputs that may reach the Challenge Lab must follow `CHALLENGE_TRADE_EXPORT_CONTRACT_V1.md`.

Canonical fields include:

- `challenge_day`: prop-firm-normalized `YYYYMMDD` day key using the actual daily-loss reset rule;
- `adverse_r`: individual signed worst adverse excursion in R, always `<= 0`;
- `net_r`, `entry_time`, `exit_time`, `run_stage`, `symbol`.

The run manifest must also record the day basis, R denominator, cost basis and whether synchronized floating equity exists. Legacy files can still be processed only through an explicit lower-fidelity escape hatch.

## Canonical automatic post-validation flow

The canonical entrypoint is now:

`post_validation_pipeline_v1_01.py`

It deliberately leaves historical frozen scorers untouched. Instead it reads:

1. the frozen scorer JSON;
2. a **pre-registered Challenge pipeline policy JSON**;
3. the frozen trade CSV(s);
4. the frozen challenge profile.

The policy freezes **before the result is known**:

- exact accepted scorer verdict(s);
- exact expected confirmation/OOS stage;
- scorer gate key and whether missing gates are ever permitted;
- Monte-Carlo path count;
- deterministic seed;
- complete risk grid;
- SHA256 of the frozen challenge profile.

The template is `challenge_pipeline_policy_template_v1_00.json`. Placeholder values are intentionally rejected by the pipeline.

`post_validation_pipeline_v1_01.py` then:

1. verifies the policy and frozen profile SHA256;
2. requires exact verdict/stage matching;
3. requires every persisted scorer gate to be literally `true` unless the **pre-registered** policy explicitly permits a legacy scorer without gates;
4. writes `challenge_lab_eligibility.json` with scorer/policy/profile SHA256 provenance;
5. calls `post_validation_challenge_gate_v1_00.py`;
6. skips rejected/unconfirmed strategies automatically;
7. for eligible strategies, runs the frozen risk grid and writes `challenge_gate_manifest.json` plus JSON/CSV/Markdown Lab reports.

Default decision policy remains **20,000 paths per risk** on `0.10 / 0.15 / 0.20 / 0.25 / 0.33 / 0.50%`, but those values are now frozen in the campaign policy rather than chosen after seeing results.

`post_validation_pipeline_v1_00.py` remains as a compatibility implementation. v1.01 is the scientific default because it prevents post-result choice of the accepted verdict, stage, risk grid or seed.

## Direct engine use

The engine remains available for development/schema checks:

```powershell
python research\challenge_probability_lab\challenge_probability_lab_v1_00.py `
  --input D:\path\to\trades_compact.csv `
  --stage DEV_2024_2025 `
  --day-column challenge_day `
  --adverse-r-column adverse_r `
  --profile research\challenge_probability_lab\guardian_reference_profile_v1_00.json `
  --paths 20000 `
  --out-prefix D:\MT5_Backtests\reports\challenge_lab\D0XX_DEV_CHALLENGE_LAB_V100
```

Direct engine runs are diagnostics/research infrastructure. Operational risk selection belongs after successful alpha/OOS/confirmation through the preregistered pipeline.

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

When comparing risks, keep the input trades, policy, profile, seed, block length and Monte-Carlo horizon frozen. Do not tune a strategy on the Lab outcome and then call the same history validation.
