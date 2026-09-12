#!/usr/bin/env python3
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
PREREG=ROOT/'research/autonomous/TOP2_XAU_MT5_CANONICAL_REPLAY_REPAIR_PREREGISTRATION_2026_09_12.md'
GEN=ROOT/'research/autonomous/prepare_top2_canonical_schedule_replay_v1_00.py'
EA=ROOT/'research/ea/Top2_CanonicalScheduleReplayTester_v1_00.mq5'
RUN=ROOT/'research/autonomous/run_top2_canonical_schedule_replay_v1_00.ps1'


def need(text,*parts):
    for p in parts:
        if p not in text: raise RuntimeError(f'missing invariant: {p}')


def main():
    for p in (PREREG,GEN,EA,RUN):
        if not p.exists(): raise RuntimeError(f'missing file: {p}')
    g=GEN.read_text(encoding='utf-8'); e=EA.read_text(encoding='utf-8'); r=RUN.read_text(encoding='utf-8'); p=PREREG.read_text(encoding='utf-8')
    need(p,'R6B-347','R6B-307','2026 is forbidden','972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503','f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445')
    need(g,"CANDIDATES=(\"R6B-347\",\"R6B-307\")","forbidden schedule boundary","r6.evaluate_year")
    need(e,'MQLInfoInteger(MQL_TESTER)',"e>=D'2026.01.01 00:00:00'","x>=D'2026.01.01 00:00:00'",'R6B-347','R6B-307','LoadSchedule()')
    if 'ProcessClosedM5' in e or 'CopyRates(_Symbol,PERIOD_M5' in e: raise RuntimeError('replay EA must not recompute R6 signal from tester M5 bars')
    need(r,'FromDate=2024.01.01','ToDate=2025.12.31','Optimization=0','AllowLiveTrading=0','prepare_top2_canonical_schedule_replay_v1_00.py')
    if re.search(r'ToDate=2026|FromDate=2026',r): raise RuntimeError('protected 2026 tester window forbidden')
    print('PASS canonical replay cold preflight')
    return 0

if __name__=='__main__': raise SystemExit(main())
