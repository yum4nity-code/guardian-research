# GEF V101 infrastructure patch — 2026-09-22

## Failure observed

Run reached the frozen discovery gate successfully:
- 3,641 atomic survivors
- 17,417 sparse triples attempted
- 150 triples physically frozen before 2014+ access

The first replication rebuild then failed on:
`D:\MT5_Backtests\DataLake\raw\histdata\BCOUSD\M1\BCOUSD_M1_2009.parquet`

This is an infrastructure/provenance mismatch, not a scientific failure.

## Root cause

V101.0 required every annual M1 file from 2009 onward.

That was stricter than the frozen lineage:
- V83 discovery treated legacy pre-2013 annual files as optional and skipped missing files.
- V92 replication/validation required the later annual files and failed closed when required files were absent.

## Patch

V101.1 now reproduces those semantics:
- missing annual files through 2012: skip and record to console;
- missing annual files from 2013 onward: fail closed;
- selected 2010-2013 states must still match the frozen V85 state cache exactly before replication scoring.

No candidate definition, threshold, FDR gate, target, direction, temporal split, robustness gate or V100 reference changed.

The failed run had already frozen its 150 candidates before opening replication. It loaded one replication market before the missing-file exception, but no replication score was produced and no result was used to change the design.

2023-2025 and 2026 remain forbidden to V101.
