from __future__ import annotations

import unittest

from collector_v1_healthfix import stable_health_signature


class HealthSignatureTests(unittest.TestCase):
    def test_ok_age_is_ignored(self):
        a = stable_health_signature(
            "OK", "spot:ok:2518ms;perpetual:ok:2346ms;liq_ws:connected"
        )
        b = stable_health_signature(
            "OK", "spot:ok:7518ms;perpetual:ok:7346ms;liq_ws:connected"
        )
        self.assertEqual(a, b)

    def test_stale_age_is_ignored_but_state_change_is_not(self):
        ok = stable_health_signature(
            "OK", "spot:ok:2518ms;perpetual:ok:2346ms;liq_ws:connected"
        )
        stale1 = stable_health_signature(
            "STALE", "spot:stale:25000ms;perpetual:ok:5000ms;liq_ws:connected"
        )
        stale2 = stable_health_signature(
            "STALE", "spot:stale:40000ms;perpetual:ok:9000ms;liq_ws:connected"
        )
        self.assertNotEqual(ok, stale1)
        self.assertEqual(stale1, stale2)

    def test_ws_transition_is_preserved(self):
        up = stable_health_signature(
            "OK", "spot:ok:1000ms;perpetual:ok:1000ms;liq_ws:connected"
        )
        down = stable_health_signature(
            "PARTIAL", "spot:ok:1000ms;perpetual:ok:1000ms;liq_ws:down"
        )
        self.assertNotEqual(up, down)


if __name__ == "__main__":
    unittest.main()
