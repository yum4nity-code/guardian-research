#!/usr/bin/env python3
from __future__ import annotations

import csv
import tempfile
from datetime import date
from pathlib import Path

import build_xau_m5_discovery_slice_v1_02 as s


def _synthetic_index(root: Path, count: int = 21):
    idx = root / "index.csv"
    rows = []
    for n in range(count):
        d = date(2019, 5, 1 + n)
        p = root / f"{d.isoformat()}.bi5"
        p.write_bytes(b"x")
        rows.append((d, p))
    with idx.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
        w.writeheader()
        for d, p in rows:
            w.writerow({
                "date": d.isoformat(),
                "path": str(p),
                "sha256": "a" * 64,
                "bytes": 1,
            })
    return idx, rows


def test_heartbeat_callback_advances_and_finishes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        idx, rows = _synthetic_index(root, 21)
        callbacks = []

        class M1:
            def __init__(self, e):
                self.epoch = e
                self.open = 2000.0
                self.high = 2001.0
                self.low = 1999.0
                self.close = 2000.5

        day_counter = {"n": 0}

        def fake_decode(d, p, h, n):
            day_counter["n"] += 1
            base = 1556668800 + (day_counter["n"] - 1) * 86400
            return [M1(base + i * 60) for i in range(5)]

        def fake_agg(m1):
            x = m1[0].epoch
            return [(x, 2000.0, 2001.0, 1999.0, 2000.5)], 0

        old = s._canonical_builder_api
        s._canonical_builder_api = lambda: (fake_decode, fake_agg, lambda p: "f" * 64)
        try:
            result = s.build(
                idx,
                root / "m5.csv",
                progress_callback=lambda state: callbacks.append(dict(state)),
            )
        finally:
            s._canonical_builder_api = old

        assert [x["completed"] for x in callbacks] == [1, 10, 20, 21]
        assert all(x["total"] == 21 for x in callbacks)
        assert callbacks[-1]["last_opened_payload_date"] == rows[-1][0].isoformat()
        assert result["source_days"] == 21
        assert result["protected_2026_opened"] is False


def test_builder_never_opens_post_discovery_payload():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        p2019 = root / "2019.bi5"
        p2025 = root / "2025.bi5"
        p2019.write_bytes(b"selected")
        p2025.write_bytes(b"MUST-NOT-BE-OPENED")
        idx = root / "index.csv"
        with idx.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["date", "path", "sha256", "bytes"])
            w.writeheader()
            w.writerow({"date":"2019-06-28","path":str(p2019),"sha256":"a"*64,"bytes":8})
            w.writerow({"date":"2025-01-02","path":str(p2025),"sha256":"b"*64,"bytes":18})

        opened = []

        class M1:
            def __init__(self, e):
                self.epoch=e; self.open=2000.0; self.high=2001.0; self.low=1999.0; self.close=2000.5

        def fake_decode(d,p,h,n):
            opened.append((d,str(p)))
            return [M1(1561680000+i*60) for i in range(5)]

        old=s._canonical_builder_api
        s._canonical_builder_api=lambda:(fake_decode,lambda m:([(1561680000,2000,2001,1999,2000.5)],0),lambda p:"f"*64)
        try:
            result=s.build(idx,root/"m5.csv")
        finally:
            s._canonical_builder_api=old

        assert opened == [(date(2019,6,28),str(p2019))]
        assert result["last_opened_payload_date"] == "2019-06-28"
        assert result["pre_oos_2025_opened"] is False


def test_2026_index_hard_fails():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        p=root/"x.bi5"; p.write_bytes(b"x")
        idx=root/"index.csv"
        with idx.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=["date","path","sha256","bytes"]); w.writeheader()
            w.writerow({"date":"2019-06-28","path":str(p),"sha256":"a"*64,"bytes":1})
            w.writerow({"date":"2026-01-02","path":str(p),"sha256":"a"*64,"bytes":1})
        try:
            s.parse_discovery_rows(idx)
        except RuntimeError as e:
            assert "PROTECTED 2026" in str(e)
        else:
            raise AssertionError("2026 index row did not fail")


def main():
    test_heartbeat_callback_advances_and_finishes()
    test_builder_never_opens_post_discovery_payload()
    test_2026_index_hard_fails()
    print("PASS: discovery-only M5 builder v1.02 heartbeat tests")


if __name__ == "__main__":
    main()
