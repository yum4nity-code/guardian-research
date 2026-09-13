#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import lzma
import math
import struct
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

dl = load("r15dl", HERE / "r15_dukascopy_xauusd_boundary_export_v1_00.py")
eng = load("r15eng", HERE / "r15_xauusd_gld_intraday_momentum_v1_01.py")

def ok(v, msg):
    if not v:
        raise AssertionError(msg)

def test_url_and_protection():
    u = dl.day_url(date(2019, 5, 1))
    ok("/2019/04/01/" in u, f"zero-based month mapping wrong: {u}")
    try:
        dl.day_url(date(2026, 1, 1))
    except RuntimeError:
        pass
    else:
        raise AssertionError("2026 URL guard missing")

def rec(sec, op):
    return struct.pack(">IIIIIf", sec, op, op, op, op, 1.0)

def test_dst_clock_decode():
    # 2025-06-02 New York is UTC-4.
    raw = b"".join([
        rec(15*3600 + 30*60, 1000),
        rec(16*3600, 1010),
        rec(19*3600 + 30*60, 1020),
        rec(20*3600, 1030),
    ])
    rows = dl.decode_day(date(2025, 6, 2), lzma.compress(raw))
    got = {(x["hm"], x["open_raw"]) for x in rows}
    ok(got == {("11:30",1000),("12:00",1010),("15:30",1020),("16:00",1030)}, f"DST mapping wrong: {got}")

def test_winter_clock_decode():
    # 2025-01-06 New York is UTC-5.
    raw = b"".join([
        rec(16*3600 + 30*60, 2000),
        rec(17*3600, 2010),
        rec(20*3600 + 30*60, 2020),
        rec(21*3600, 2030),
    ])
    rows = dl.decode_day(date(2025, 1, 6), lzma.compress(raw))
    got = {(x["hm"], x["open_raw"]) for x in rows}
    ok(got == {("11:30",2000),("12:00",2010),("15:30",2020),("16:00",2030)}, f"winter mapping wrong: {got}")

def test_full_paper_window():
    ok(eng.REPL0 == pd.Timestamp("2004-11-08", tz="UTC"), "paper start drift")
    ok(eng.REPL1 == pd.Timestamp("2019-05-31", tz="UTC"), "paper end drift")
    ok(eng.CONF1 == pd.Timestamp("2025-01-01", tz="UTC"), "confirmation end drift")
    ok(eng.PRE1 == pd.Timestamp("2026-01-01", tz="UTC"), "protected boundary drift")

def test_hac_recovers_positive_beta():
    x = [((i % 17) - 8) / 1000 for i in range(1000)]
    y = [0.0001 + 0.2*v + 0.00001*math.sin(i) for i, v in enumerate(x)]
    r = eng.hac_reg(x, y)
    ok(r["beta"] is not None and r["beta"] > 0.19, f"beta wrong: {r}")
    ok(r["p"] <= 0.05, f"positive relation not significant: {r}")

def test_manifest_hash_and_returns():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        csv = td / "b.csv"
        rows = []
        for d in pd.bdate_range("2018-01-02", periods=300):
            rows.append({
                "date_ny": d.date().isoformat(),
                "p_1130_raw": 100000,
                "p_1200_raw": 100100,
                "p_1530_raw": 100000,
                "p_1600_raw": 100050,
            })
        pd.DataFrame(rows).to_csv(csv, index=False)
        h = hashlib.sha256(csv.read_bytes()).hexdigest()
        manifest = td / "m.json"
        manifest.write_text(json.dumps({
            "status": "PASS",
            "protected_2026_opened": False,
            "boundary_csv_sha256": h,
        }), encoding="utf-8")
        z = eng.load_boundaries(manifest, csv)
        ok(len(z) == 300, "boundary load count wrong")
        ok((z["r5"] > 0).all(), "r5 construction wrong")
        ok((z["r13"] > 0).all(), "r13 construction wrong")

def test_no_2026_dataset():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        csv = td / "b.csv"
        pd.DataFrame([{
            "date_ny": "2026-01-02",
            "p_1130_raw": 100,
            "p_1200_raw": 101,
            "p_1530_raw": 100,
            "p_1600_raw": 101,
        }]).to_csv(csv, index=False)
        h = hashlib.sha256(csv.read_bytes()).hexdigest()
        manifest = td / "m.json"
        manifest.write_text(json.dumps({
            "status": "PASS",
            "protected_2026_opened": False,
            "boundary_csv_sha256": h,
        }), encoding="utf-8")
        try:
            eng.load_boundaries(manifest, csv)
        except RuntimeError:
            pass
        else:
            raise AssertionError("2026 dataset row was accepted")

def main():
    for fn in [
        test_url_and_protection,
        test_dst_clock_decode,
        test_winter_clock_decode,
        test_full_paper_window,
        test_hac_recovers_positive_beta,
        test_manifest_hash_and_returns,
        test_no_2026_dataset,
    ]:
        fn()
    print('{"status":"PASS","tests":"R15 v1.01 Dukascopy source/parser/clock/stat/protection preflight"}')

if __name__ == "__main__":
    main()
