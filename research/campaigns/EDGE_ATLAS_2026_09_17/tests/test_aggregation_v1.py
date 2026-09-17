#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import data_loader_v1 as dl
UTC=timezone.utc


class AggregationTests(unittest.TestCase):
    def test_m1_to_m5_is_deterministic_and_causal(self):
        base=datetime(2025,1,1,tzinfo=UTC);bars=[]
        for i in range(5):
            ts=base+timedelta(minutes=i);bars.append(dl.Bar(ts,ts+timedelta(minutes=1),10+i,12+i,9+i,11+i,1))
        out=list(dl.aggregate_m1_to_m5(iter(bars)))
        self.assertEqual(len(out),1);m5=out[0]
        self.assertEqual((m5.timestamp,m5.available_at),(base,base+timedelta(minutes=5)))
        self.assertEqual((m5.open,m5.high,m5.low,m5.close,m5.volume),(10,16,9,15,5))
        with self.assertRaises(dl.AdmissionError):dl.require_available_before_decision(m5,base+timedelta(minutes=4,seconds=59))
        dl.require_available_before_decision(m5,base+timedelta(minutes=5))

    def test_rejects_incomplete_or_gapped_bucket(self):
        base=datetime(2025,1,1,tzinfo=UTC)
        incomplete=[dl.Bar(base+timedelta(minutes=i),base+timedelta(minutes=i+1),1,1,1,1,1) for i in range(4)]
        with self.assertRaises(dl.AdmissionError):list(dl.aggregate_m1_to_m5(incomplete))
        gapped=[dl.Bar(base,base+timedelta(minutes=1),1,1,1,1,1),dl.Bar(base+timedelta(minutes=2),base+timedelta(minutes=3),1,1,1,1,1)]
        with self.assertRaises(dl.AdmissionError):list(dl.aggregate_m1_to_m5(gapped))


if __name__ == "__main__":unittest.main()
