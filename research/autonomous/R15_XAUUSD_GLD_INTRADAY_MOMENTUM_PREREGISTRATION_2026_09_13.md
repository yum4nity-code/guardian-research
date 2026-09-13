# R15 XAUUSD GLD intraday momentum literature replication

Date: 2026-09-13
Status: frozen before execution

R15 near-replicates Xu, Bouri, Saeed & Wen (2020), Resources Policy 69, 101830, DOI 10.1016/j.resourpol.2020.101830. The published GLD result is that the fifth US-session half-hour return positively predicts the last half-hour return (published beta 0.0436, Newey-West t=3.03, R2=0.49%; GLD sample 2004-11-08 to 2019-05-30).

Guardian uses the existing provenance-clean FundedNext XAUUSD M1 history, so this is a cross-instrument near-replication, not an exact GLD reproduction.

Clock mapping uses America/New_York with DST. Boundary prices are exact M1 opens. Predictor r5 = log(P12:00/P11:30). Target r13 = log(P16:00/P15:30). Eligible days are Monday-Friday with all four boundary prices.

Stage 1 overlap recovery: 2017-01-01 through 2019-05-30. Pass: n>=250, regression beta>0, HAC p<=0.05. Only r5->r13 is selectable; other half-hours may not rescue a failure.

Stage 2 independent confirmation: 2019-05-31 through 2024-12-31. Pass: n>=500, beta>0, HAC p<=0.05, and positive beta in at least 4 of full years 2020-2024.

HAC lag is frozen as max(1, floor(4*(n/100)^(2/9))) because the accessible paper description identifies Newey-West but not its exact lag convention.

Only after confirmation, translate the published market-timing rule: sign(r5) determines long/short at 15:30 ET, exit 16:00 ET. Apply downstream round-trip costs E1=0.001 and STRESS=0.002. Economic pass requires positive E1 and STRESS means, positive STRESS net after removing best trade, and largest-positive-trade concentration <=0.35.

Stage 4 pre-OOS is calendar 2025 with n>=100, positive E1/STRESS means, positive H1 and H2 E1 net, positive stress net ex-best, concentration<=0.35.

Use only XAUUSD M1 files 2017-2025 whose SHA256 values match the existing top2 long-history manifest. Never open a 2026 file or row. No retuning, no alternate interval rescue, no 2025 selection, and no live deployment.
