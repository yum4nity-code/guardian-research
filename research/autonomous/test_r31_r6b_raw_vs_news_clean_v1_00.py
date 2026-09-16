#!/usr/bin/env python3
from __future__ import annotations
import r31_r6b_raw_vs_news_clean_v1_00 as m

def t(entry, net, when):
    return {
        "entry_time":when,
        "entry_open":entry,
        "profiles":{"E1":{"net":net},"STRESS":{"net":net}},
    }

def test_frozen_defs():
    assert m.CANDIDATES["R6B-347"]["lookback_bars"]==96
    assert m.CANDIDATES["R6B-347"]["buffer_atr"]==0.1
    assert m.CANDIDATES["R6B-347"]["horizon_bars"]==96
    assert m.CANDIDATES["R6B-347"]["session_start"]==0
    assert m.CANDIDATES["R6B-347"]["session_end"]==8
    assert m.CANDIDATES["R6B-347"]["direction"]==1
    assert m.CANDIDATES["R6B-307"]["lookback_bars"]==96
    assert m.CANDIDATES["R6B-307"]["buffer_atr"]==0.0
    assert m.CANDIDATES["R6B-307"]["horizon_bars"]==48

def test_capital():
    xs=[t(100,10,"2024-01-01T00:00:00+00:00"),t(100,-5,"2024-01-02T00:00:00+00:00")]
    x=m.capital(xs,"E1",10000)
    assert abs(x["ending"]-10450)<1e-9
    assert abs(x["return_pct"]-4.5)<1e-9

def test_hash_pins():
    assert m.EXPECTED["xauusd_m1_2024_2025_raw.csv"]=="f98a395961b27ca9dcb34cffa4ef8dd93720adb70292abf7bc96108667232445"
    assert m.EXPECTED["xauusd_m5_2024_2025_raw.csv"]=="ba54c9b29755eac4284cb872805148736be529e954533c028e7f826bb444ce66"
    assert m.EXPECTED["xauusd_m5_2024_2025_news_clean.csv"]=="972ecaf6c3cadf7136363f396d7a29e7a6246646b575fad5c3e677036004b503"

def main():
    test_frozen_defs()
    test_capital()
    test_hash_pins()
    print("PASS: R31 raw-vs-news-clean tests")

if __name__=="__main__":
    main()
