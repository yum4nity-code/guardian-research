#!/usr/bin/env python3
"""Regression checks for stage-generic post-decision analytics."""

from __future__ import annotations

import unittest

import guardian_research
import rich_score_v2


class ConfirmationRichV2Tests(unittest.TestCase):
    def test_confirmation_is_a_scored_stage_in_unified_cli_contract(self) -> None:
        self.assertIn("development", guardian_research.SCORED_STAGES)
        self.assertIn("confirmation", guardian_research.SCORED_STAGES)

    def test_rich_v2_supports_confirmation_without_changing_smoke_role(self) -> None:
        self.assertEqual({"development", "confirmation"}, rich_score_v2.SUPPORTED_STAGES)
        self.assertNotIn("smoke", rich_score_v2.SUPPORTED_STAGES)


if __name__ == "__main__":
    unittest.main()
