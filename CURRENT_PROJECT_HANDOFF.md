# Guardian Research — CURRENT PROJECT HANDOFF

**Canonical current state: 2026-09-22**

## Closed / frozen lineages
- V100 forward/shadow frozen; 2026 protected.
- Rates standalone closed after V103 forensic 0/5.
- CFTC standalone closed after V105 report-level forensic 0/7.
- ALFRED V107 closed operationally without alpha conclusion.
- Treasury V109 closed at discovery: 15,870 finite tests, 0 frozen after BH q<=0.05. No 2014+ market returns spent.

## V110 — ACTIVE

Pure UTC intraday/calendar structure. No external source provenance.

Statistical unit:
- one exact top-of-hour event.

Frozen cell universe:
- UTC hour;
- UTC hour × weekday;
- UTC hour × month position START/MID/END;
- UTC hour × quarter-end window.

Matched controls:
- hour vs all other hours;
- hour×weekday vs same hour other weekdays;
- hour×month-position vs same hour other month-position buckets;
- hour×quarter-end vs same hour outside quarter-end.

Discovery tests candidate-minus-control effect and requires the oriented candidate trade itself to be profitable.

Targets:
30 / 60 / 120 / 240 minutes.

Temporal firewall:
2010-2013 discovery -> freeze -> 2014-2017 replication -> robustness -> freeze -> 2018-2022 validation -> STOP.

No 2023-2025.
No 2026.

Run:
powershell -ExecutionPolicy Bypass -File D:\MT5_Backtests\guardian-research\automation\Run-GuardianEdgeFactoryV110.ps1 -Root D:\MT5_Backtests
