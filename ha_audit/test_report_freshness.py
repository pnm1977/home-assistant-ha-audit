#!/usr/bin/env python3
"""HA Audit report-freshness safety regression tests.

Run: python3 ha_audit/test_report_freshness.py

The tests operate on temporary local files. No Home Assistant API calls, edits
of /config, or Web UI server are involved.

A run-status record is the contract for the forthcoming production fix:
- a failed/incomplete run must not present older generated files as current;
- user investigation context must remain intact;
- a successful, fresh run may display its own reports.

The three expected failures document the known gap in v0.8.23 and will be
converted to normal passing assertions once the production fix is committed.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import web_ui as ui


class ReportFreshnessSafetyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.report = self.root / "ha_audit_latest.txt"
        self.handoff = self.root / "ha_audit_ai_handoff.md"
        self.issues = self.root / "log_priority_final.json"
        self.context = self.root / "investigation_context.json"
        self.run_state = self.root / "ha_audit_run_status.json"
        for name, value in (
            ("REPORT", self.report),
            ("HANDOFF", self.handoff),
            ("ISSUES", self.issues),
            ("CONTEXT", self.context),
            ("RUN_STATE", self.run_state),
        ):
            patcher = patch.object(ui, name, value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.report.write_text("PREVIOUS AUDIT — ALL GOOD", encoding="utf-8")
        self.handoff.write_text("PREVIOUS AI HANDOFF", encoding="utf-8")
        self.issues.write_text(json.dumps({
            "families": [{
                "stable_fingerprint": "lfp_old",
                "title": "Previously recorded finding",
                "final_priority": "HIGH",
            }]
        }), encoding="utf-8")
        self.context.write_text(json.dumps({
            "schema_version": 1,
            "investigations": {"lfp_old": {"status": "Monitoring", "note": "Keep this note"}},
        }), encoding="utf-8")

    def mark_incomplete_run(self):
        self.run_state.write_text(json.dumps({
            "schema_version": 1,
            "status": "incomplete",
            "run_started_at_utc": "2026-10-29T14:40:00+00:00",
            "run_finished_at_utc": "2026-10-29T14:41:00+00:00",
            "summary_status": "failed",
            "handoff_status": "not_generated",
            "issues_status": "not_verified",
        }), encoding="utf-8")

    def test_control_existing_reports_remain_readable_without_marker(self):
        """Retain backwards-compatible report access before any run marker exists."""
        self.assertIn("PREVIOUS AUDIT", ui.read_summary())
        self.assertEqual(ui.read_handoff(), "PREVIOUS AI HANDOFF")

    def test_saved_user_investigations_are_not_deleted(self):
        """A failed collection must not destroy the user's historical notes."""
        self.mark_incomplete_run()
        self.assertEqual(
            ui.load_context()["investigations"]["lfp_old"]["note"],
            "Keep this note",
        )

    @unittest.expectedFailure
    def test_incomplete_run_does_not_label_old_summary_as_latest(self):
        self.mark_incomplete_run()
        result = ui.read_summary()
        self.assertNotIn("PREVIOUS AUDIT — ALL GOOD", result)
        self.assertIn("incomplete", result.lower())

    @unittest.expectedFailure
    def test_incomplete_run_does_not_offer_old_handoff_as_current(self):
        self.mark_incomplete_run()
        self.assertIsNone(ui.read_handoff())

    @unittest.expectedFailure
    def test_incomplete_run_does_not_show_old_findings_as_current(self):
        self.mark_incomplete_run()
        self.assertEqual(ui.current_families(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
