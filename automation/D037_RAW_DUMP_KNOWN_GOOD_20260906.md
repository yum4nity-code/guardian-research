# D037 raw dump — known-good recovery path

Status: **KNOWN GOOD / user-confirmed working** on 2026-09-06.

Use this exact script when Guardian AutoSync has not published local D037 CSVs and a raw recovery upload is needed:

- `automation/Dump_D037_Raw_To_GitHub_v1_01_20260906.ps1`
- Script commit: `a16db0b101bf5628690e041e03a139b9b00db0e8`

Known-good command:

```powershell
cd D:\MT5_Backtests\guardian-research
git pull
powershell -ExecutionPolicy Bypass -File .\automation\Dump_D037_Raw_To_GitHub_v1_01_20260906.ps1
```

Important implementation lesson: native `git` writes normal informational output such as `From https://...` to stderr. PowerShell must not treat stderr output alone as failure. Judge Git success from `$LASTEXITCODE`; keep stdout/stderr handling from v1.01. Do not regress to the v1.00 `2>&1` wrapper behavior.

This recovery script does **not** validate strategy integrity and does **not** rerun backtests. It uploads the local D037 STATS/TRADES files into a separate `backtests/recovery/...` path for remote audit.
