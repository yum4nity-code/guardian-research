# V111-C1 XAGUSD — FTMO Execution Audit

Date: 2026-09-23
Status: FROZEN BEFORE FTMO EXECUTION RESULT

## Frozen source result

Source locked OOS run:
- candidate: V111 C1
- XAGUSD H11 SHORT
- horizon: 60 minutes
- 2023-2025 only
- n = 705
- mean = +1.1896855761203053 bp
- V2 existence = POSITIVE_UNCERTAIN
- 2026 accessed = false

No signal parameter may be changed.

## Alignment

The HistData source uses raw vendor timestamp +5h and a right-labelled / left-closed 5-minute series.

FTMO clock alignment is not assumed from another market.

Scan integer offsets -8h through +8h and choose the offset only by:
1. >=90% two-leg M1 coverage;
2. minimum median absolute source-vs-FTMO two-leg price difference.

PnL must not be used to select the clock offset.

For price alignment, the source value at a right-labelled H11/H12 boundary corresponds to the final M1 close immediately before the boundary.

## Execution convention

After the alignment offset is frozen from price proximity:
- entry: first FTMO tick at or after mapped H11 boundary;
- exit: first FTMO tick at or after mapped H12 boundary;
- SHORT execution: sell at BID, cover at ASK.

M1 open plus recorded spread may be used only as fallback if tick history is unavailable.

## Interpretation

Report:
- coverage;
- source-vs-FTMO BID-return correlation;
- FTMO BID gross mean;
- observed entry and exit spreads;
- executable BID/ASK mean;
- yearly means;
- trim diagnostics;
- extra-cost grid.

No swap is required for a 60-minute trade unless the mapped window actually crosses broker rollover.
Commission and additional slippage are not invented; use the extra-cost grid as sensitivity if exact historical commission is unavailable.

If executable expectancy is <= 0 after observed BID/ASK, exact frozen C1 is execution-rejected on FTMO.
If >0, retain for commission/slippage and portfolio testing.

2026 remains hard-blocked.
