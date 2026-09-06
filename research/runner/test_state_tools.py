#!/usr/bin/env python3
"""Small regression suite for the Guardian single-source-of-truth contract."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import state_tools


class GuardianStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = state_tools.load_state()
        self.manifest = state_tools.load_active_manifest(self.state)

    def test_authoritative_state_is_internally_valid(self) -> None:
        self.assertEqual([], state_tools.validate_state(self.state))

    def test_generated_views_are_current(self) -> None:
        self.assertEqual([], state_tools.check_generated(self.state))

    def test_active_experiment_matches_manifest(self) -> None:
        self.assertEqual(
            self.state["research"]["active_experiment"],
            self.manifest["experiment_id"],
        )

    def test_no_codex_dependency_in_generated_queue(self) -> None:
        queue = json.loads(state_tools.QUEUE_PATH.read_text(encoding="utf-8"))
        serialized = json.dumps(queue, ensure_ascii=False).upper()
        self.assertNotIn("WAITING_CODEX", serialized)
        self.assertNotIn('"OWNER": "CODEX"', serialized)

    def test_legacy_autosync_is_never_fallback(self) -> None:
        transport = self.state["transport"]
        self.assertEqual("UNTRUSTED_NEVER_RELIABLY_WORKED", transport["legacy_runtime_status"])
        self.assertEqual("REFERENCE_ONLY_NOT_FALLBACK", transport["legacy_scripts_role"])

    def test_maman_project_is_preserved(self) -> None:
        maman = self.state["non_guardian_projects"]["maman_70_santorin"]
        self.assertTrue(maman["preserve"])
        self.assertTrue((state_tools.ROOT / maman["current_path"]).exists())

    def test_complete_source_must_be_real_repository_file(self) -> None:
        source = self.manifest["source"]
        if source["complete_repository_source"]:
            self.assertTrue(source["canonical_path"])
            self.assertTrue((state_tools.ROOT / source["canonical_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
