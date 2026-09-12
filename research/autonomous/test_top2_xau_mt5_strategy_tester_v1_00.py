#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent

def check(path: Path, cid: str, buf: str, horizon: str, magic: str):
    s = path.read_text(encoding="utf-8")
    assert f'const string CANDIDATE_ID = "{cid}";' in s
    assert "const int LOOKBACK_BARS = 96;" in s
    assert f"const double BUFFER_ATR = {buf};" in s
    assert f"const int HORIZON_BARS = {horizon};" in s
    assert "const int SESSION_START = 0;" in s
    assert "const int SESSION_END = 8;" in s
    assert f"const long MAGIC = {magic};" in s
    assert "MQLInfoInteger(MQL_TESTER)" in s
    assert "g_trade.Buy" in s
    assert "g_trade.PositionClose" in s
    assert "ACTIVE_START = D'2017.01.01 00:00:00'" in s
    assert "ACTIVE_END = D'2026.08.01 00:00:00'" in s
    assert "g_exit_due=due" in s
    assert "due=entry_time + HORIZON_BARS*300" in s
    assert "b.close>(prior_hi+BUFFER_ATR*g_atr)" in s
    assert "g_atr=((13.0/14.0)*g_atr)+((1.0/14.0)*tr)" in s
    assert "if(g_highs[i]>hi)" in s
    assert "if(g_lows[i]<lo)" in s

def main():
    check(ROOT / "research" / "ea" / "R6B-347_LongHistoryTester_v1_00.mq5", "R6B-347", "0.10", "96", "6347001")
    check(ROOT / "research" / "ea" / "R6B-307_LongHistoryTester_v1_00.mq5", "R6B-307", "0.00", "48", "6307001")
    ps = (HERE / "run_top2_xau_mt5_strategy_tester_v1_00.ps1").read_text(encoding="utf-8")
    assert "Model=1" in ps
    assert "Optimization=0" in ps
    assert "FromDate=2016.12.01" in ps
    assert "ToDate=2026.07.31" in ps
    assert "AllowLiveTrading=0" in ps
    assert "Close that window first" in ps
    assert "Stop-Process -Id $proc.Id" in ps  # only process created by the harness on timeout
    assert "Get-SameTerminalProcess" in ps
    print(json.dumps({"status":"PASS","tests":2,"market_data_accessed":False,"live_action":False,"strategy_tester_commandline":True}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
