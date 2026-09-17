#!/usr/bin/env python3
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import data_loader_v1 as dl
UTC=timezone.utc


def bar(minute,available_delta=5,op=10):
    ts=datetime(2025,1,1,0,minute,tzinfo=UTC)
    return dl.Bar(ts,ts+timedelta(minutes=available_delta),op,op+1,op-1,op+.5,1)


class CausalityTests(unittest.TestCase):
    def test_rejects_post_decision_availability(self):
        with self.assertRaises(dl.AdmissionError):dl.require_available_before_decision(bar(0),datetime(2025,1,1,0,4,tzinfo=UTC))
        dl.require_available_before_decision(bar(0),datetime(2025,1,1,0,5,tzinfo=UTC))

    def test_first_open_at_or_after_signal_close(self):
        bars=[bar(0,op=10),bar(5,op=11),bar(10,op=12)]
        ts,op=dl.first_open_at_or_after(bars,datetime(2025,1,1,0,5,tzinfo=UTC))
        self.assertEqual((ts,op),(datetime(2025,1,1,0,5,tzinfo=UTC),11))
        with self.assertRaises(dl.AdmissionError):dl.first_open_at_or_after([bar(5),bar(0)],datetime(2025,1,1,0,10,tzinfo=UTC))

    def test_strict_partitions(self):
        self.assertEqual(dl.partition_for(datetime(2022,12,31,tzinfo=UTC),"XAU"),"discovery")
        self.assertEqual(dl.partition_for(datetime(2023,1,1,tzinfo=UTC),"XAU"),"confirmation")
        self.assertEqual(dl.partition_for(datetime(2025,1,1,tzinfo=UTC),"XAU"),"pre_oos")
        self.assertEqual(dl.partition_for(datetime(2024,1,1,tzinfo=UTC),"CRYPTO_SPOT"),"discovery")
        self.assertEqual(dl.partition_for(datetime(2025,1,1,tzinfo=UTC),"CRYPTO_SPOT"),"confirmation")
        with self.assertRaises(dl.AdmissionError):dl.partition_for(datetime(2026,1,1,tzinfo=UTC),"XAU")

    def test_cost_profiles_are_separate(self):
        nominal=dl.CostProfile("nominal",1,1,1);stress=dl.CostProfile("stress",2,2,2)
        dl.validate_cost_profiles(nominal,stress)
        with self.assertRaises(dl.AdmissionError):dl.validate_cost_profiles(nominal,dl.CostProfile("stress",.5,2,2))


if __name__ == "__main__":unittest.main()
