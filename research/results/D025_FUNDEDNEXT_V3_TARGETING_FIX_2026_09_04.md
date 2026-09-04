# D025 FundedNext V3 targeting fix

Date: 2026-09-04

V2 could fail when the correct live MT5 data folder did not persist literal account/server strings in recent logs or bases names.

V3 resolves the target from the **currently running MT5 window title** first. It requires one visible `terminal64.exe` window containing both:
- account `14202634`
- server `FundedNext-Server 2`

It then maps that running executable back to its MT5 data folder through `origin.txt`, and only then delegates to the isolated portable V2 backtest workflow. The later portable clone still has to confirm the expected account/server in its own logs before the backtest is trusted.

This change is targeting/infrastructure only. D025 V0 thresholds and signal logic are unchanged.
