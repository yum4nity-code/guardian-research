import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

CAMPAIGN = Path(__file__).parents[1]
sys.path.insert(0, str(CAMPAIGN))

from data_loader_v1 import AdmissionError, Bar
from ea01_cheap_fail_v1 import evaluate_bars


def bar(ts, op, hi, lo, close):
    return Bar(ts, ts + timedelta(minutes=5), op, hi, lo, close, 1.0)


class EA01EngineTests(unittest.TestCase):
    def test_next_open_two_variants_and_three_bar_exit(self):
        start = datetime(2017, 1, 2, tzinfo=timezone.utc)
        bars = [bar(start + timedelta(minutes=5*i), 100, 100.5, 99.5, 100) for i in range(20)]
        for close in (101, 102, 103):
            ts = start + timedelta(minutes=5*len(bars))
            bars.append(bar(ts, close - 0.2, close + 0.4, close - 0.6, close))
        entry_ts = start + timedelta(minutes=5*len(bars))
        bars.extend([bar(entry_ts, 103.0, 103.4, 102.6, 103.1),
                     bar(entry_ts + timedelta(minutes=5), 103.1, 103.4, 102.7, 103.0),
                     bar(entry_ts + timedelta(minutes=10), 103.0, 103.3, 102.8, 103.2)])
        metrics, trades = evaluate_bars(bars)
        target = [t for t in trades if t.entry_time == entry_ts.isoformat()]
        self.assertEqual({t.variant for t in target}, {"reversal", "continuation"})
        self.assertTrue(all(t.exit_reason == "TIME_3_BARS" for t in target))
        self.assertEqual({t.exit_time for t in target}, {(entry_ts + timedelta(minutes=15)).isoformat()})
        self.assertEqual(set(metrics), {"reversal", "continuation"})

    def test_stop_has_priority_on_third_bar(self):
        start = datetime(2017, 2, 1, tzinfo=timezone.utc)
        bars = [bar(start + timedelta(minutes=5*i), 100, 101, 99, 100) for i in range(20)]
        for close in (101, 102, 103):
            ts = start + timedelta(minutes=5*len(bars))
            bars.append(bar(ts, close, close + .5, close - .5, close))
        entry = start + timedelta(minutes=5*len(bars))
        bars.extend([bar(entry, 103, 103.2, 102.8, 103),
                     bar(entry+timedelta(minutes=5), 103, 103.2, 102.8, 103),
                     bar(entry+timedelta(minutes=10), 103, 110, 96, 103)])
        _, trades = evaluate_bars(bars)
        target = [t for t in trades if t.entry_time == entry.isoformat()]
        self.assertEqual(len(target), 2)
        self.assertTrue(all(t.exit_reason == "STOP" for t in target))

    def test_rejects_bar_outside_discovery(self):
        ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
        with self.assertRaises(AdmissionError):
            evaluate_bars([bar(ts, 1, 1, 1, 1)])


if __name__ == "__main__":
    unittest.main()
