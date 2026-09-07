#!/usr/bin/env python3
from __future__ import annotations
import unittest
import management_benchmark_offline as m


class ManagementBenchmarkOfflineTests(unittest.TestCase):
    def test_frozen_dataset_universe_and_total_rows(self):
        self.assertEqual({"D038", "D039", "D040", "D045"}, set(m.FROZEN_DATASETS))
        self.assertEqual(1803, sum(int(x["rows"]) for x in m.FROZEN_DATASETS.values()))
        self.assertTrue(all(x["stage"] == "development" for x in m.FROZEN_DATASETS.values()))

    def test_short_identifier_normalization(self):
        self.assertEqual("D038", m._canonical_short("d038"))
        self.assertEqual("D038", m._canonical_short("038"))

    def test_non_frozen_dataset_is_refused_before_manifest_access(self):
        with self.assertRaises(m.OfflineBenchmarkSafetyError):
            m.archived_context("D041")


if __name__ == "__main__":
    unittest.main()
