#!/usr/bin/env python3
import csv
import hashlib
import lzma
import struct
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import data_loader_v1 as dl
import preflight_v1 as pf


HEADERS = dl.BINANCE_COLUMNS


def write_csv(path: Path, rows, headers=HEADERS):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader(); writer.writerows(rows)


def row(ts):
    return {"time": ts, "open": "10", "high": "11", "low": "9", "close": "10.5", "volume": "2", "quote_volume": "20", "trades": "2", "taker_buy_base": "1", "taker_buy_quote": "10"}


class LoaderTests(unittest.TestCase):
    def test_rejects_2026_row(self):
        with tempfile.TemporaryDirectory(dir="D:\\MT5_Backtests") as td:
            p=Path(td)/"spot.csv"; write_csv(p,[row("2025-12-31T23:55:00Z"),row("2026-01-01T00:00:00Z")])
            with self.assertRaises(dl.AdmissionError):list(dl.iter_binance_spot_m5(p,dl.sha256(p),datetime(2025,12,31,23,55,tzinfo=timezone.utc),dl.PROTECTED_START))

    def test_rejects_wrong_hash(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            p=Path(td)/"spot.csv";write_csv(p,[row("2025-01-01T00:00:00Z")])
            with self.assertRaises(dl.AdmissionError):list(dl.iter_binance_spot_m5(p,"0"*64,datetime(2025,1,1,tzinfo=timezone.utc),dl.PROTECTED_START))

    def test_rejects_timezone_and_bad_cadence_and_duplicates(self):
        cases=[
            [row("2025-01-01T00:00:00" )],
            [row("2025-01-01T00:00:00Z"),row("2025-01-01T00:06:00Z")],
            [row("2025-01-01T00:00:00Z"),row("2025-01-01T00:00:00Z")],
            [row("2025-01-01T00:05:00Z"),row("2025-01-01T00:00:00Z")],
        ]
        for rows in cases:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory(dir=ROOT) as td:
                p=Path(td)/"spot.csv";write_csv(p,rows)
                with self.assertRaises(dl.AdmissionError):list(dl.iter_binance_spot_m5(p,dl.sha256(p),datetime(2025,1,1,tzinfo=timezone.utc),dl.PROTECTED_START))

    def test_rejects_oi_funding_derivative_schema(self):
        for forbidden in ("oi","open_interest","funding","derivative","perpetual"):
            with self.subTest(forbidden=forbidden), tempfile.TemporaryDirectory(dir=ROOT) as td:
                p=Path(td)/"spot.csv";headers=HEADERS+(forbidden,);r=row("2025-01-01T00:00:00Z");r[forbidden]="1";write_csv(p,[r],headers)
                with self.assertRaises(dl.AdmissionError):list(dl.iter_binance_spot_m5(p,dl.sha256(p),datetime(2025,1,1,tzinfo=timezone.utc),dl.PROTECTED_START))

    def test_rejects_r30_and_bad_m1_cadence(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            r30=Path(td)/"r30_xauusd_m1.csv"
            with self.assertRaises(dl.AdmissionError):list(dl.decode_dukascopy_m1_day({"path":str(r30),"date":"2025-01-01","bytes":"1","sha256":"0"*64}))
            p=Path(td)/"day.bi5";raw=b"".join(struct.pack(">5If",s,1000,1100,900,1050,1.0) for s in (0,120));p.write_bytes(lzma.compress(raw))
            meta={"path":str(p),"date":"2025-01-01","bytes":str(p.stat().st_size),"sha256":dl.sha256(p)}
            with self.assertRaises(dl.AdmissionError):list(dl.decode_dukascopy_m1_day(meta,expected_records=2))

    def test_dukascopy_bi5_field_order_is_open_close_low_high(self):
        with tempfile.TemporaryDirectory(dir="D:\\MT5_Backtests") as td:
            p=Path(td)/"day.bi5"
            raw=b"".join(struct.pack(">5If",s,1150000,1150921,1150000,1150971,1.0) for s in (0,60))
            p.write_bytes(lzma.compress(raw))
            meta={"path":str(p),"date":"2017-01-02","bytes":str(p.stat().st_size),"sha256":dl.sha256(p)}
            bars=list(dl.decode_dukascopy_m1_day(meta,expected_records=2))
            self.assertEqual((bars[0].open,bars[0].high,bars[0].low,bars[0].close),(1150.0,1150.971,1150.0,1150.921))

    def test_dukascopy_index_rejects_weekday_gap(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            p=Path(td)/"index.csv"
            with p.open("w",newline="",encoding="utf-8") as f:
                w=csv.DictWriter(f,fieldnames=("date","path","sha256","bytes"));w.writeheader()
                w.writerow({"date":"2025-01-01","path":str(Path(td)/"a.bi5"),"sha256":"1"*64,"bytes":"1"})
                w.writerow({"date":"2025-01-03","path":str(Path(td)/"b.bi5"),"sha256":"2"*64,"bytes":"1"})
            with self.assertRaises(dl.AdmissionError):list(dl.load_dukascopy_index(p,dl.sha256(p)))

    def test_preflight_rejects_empty_manifest_and_populates_rejection(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            p=Path(td)/"manifest.json";p.write_text('{"schema_version":1,"campaign_id":"EDGE-ATLAS-2026-09-17","verdict":"READY_FOR_READ_ONLY_CHEAP_FAIL","global_rules":{},"datasets":[]}',encoding="utf-8")
            result=pf.run_preflight(p,expected_manifest_sha256=pf.canonical_manifest_sha256(p))
            self.assertEqual(result["status"],"BLOCKED_DATA")
            self.assertEqual(result["files_rejected"][0]["path"],str(p))
            self.assertTrue(result["rejection_causes"])

    def test_preflight_has_no_metadata_only_bypass(self):
        import inspect
        self.assertNotIn("metadata",str(inspect.signature(pf.run_preflight)))
        source=inspect.getsource(pf.run_preflight)
        self.assertIn('result["files_inspected"] += 1',source)


if __name__ == "__main__":unittest.main()
