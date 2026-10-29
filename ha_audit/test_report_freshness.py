#!/usr/bin/env python3
"""HA Audit report-freshness safety regression tests.

Run: python3 ha_audit/test_report_freshness.py

The tests operate on temporary local files. No Home Assistant API calls, edits
of /config, or Web UI server are involved.

A run-status record is the contract for the forthcoming production fix:
- a failed/incomplete run must not present older generated files as current;
- user investigation context must remain intact;
- a successful, fresh run may display its own reports.

These tests enforce the completed v0.8.23 report-freshness correction.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
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

    def test_incomplete_run_does_not_label_old_summary_as_latest(self):
        self.mark_incomplete_run()
        result = ui.read_summary()
        self.assertNotIn("PREVIOUS AUDIT — ALL GOOD", result)
        self.assertIn("incomplete", result.lower())

    def test_incomplete_run_does_not_offer_old_handoff_as_current(self):
        self.mark_incomplete_run()
        self.assertIsNone(ui.read_handoff())

    def test_incomplete_run_does_not_show_old_findings_as_current(self):
        self.mark_incomplete_run()
        self.assertEqual(ui.current_families(), [])

    def test_running_audit_does_not_serve_prior_reports(self):
        self.run_state.write_text(json.dumps({
            "schema_version": 1,
            "status": "running",
            "run_started_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary_status": "not_generated",
            "handoff_status": "not_generated",
            "issues_status": "not_verified",
        }), encoding="utf-8")
        self.assertIn("incomplete", ui.read_summary().lower())
        self.assertIsNone(ui.read_handoff())
        self.assertEqual(ui.current_families(), [])

    def test_complete_run_allows_fresh_reports(self):
        started = datetime.now(timezone.utc) - timedelta(minutes=1)
        self.run_state.write_text(json.dumps({
            "schema_version": 1,
            "status": "complete",
            "run_started_at_utc": started.isoformat(),
            "run_finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "summary_status": "ok",
            "handoff_status": "ok",
            "issues_status": "ok",
        }), encoding="utf-8")
        self.assertIn("PREVIOUS AUDIT", ui.read_summary())
        self.assertEqual(ui.read_handoff(), "PREVIOUS AI HANDOFF")
        self.assertEqual(len(ui.current_families()), 1)

    def test_completed_marker_cannot_authorize_stale_summary(self):
        started = datetime.now(timezone.utc)
        self.run_state.write_text(json.dumps({
            "schema_version": 1,
            "status": "complete",
            "run_started_at_utc": started.isoformat(),
            "summary_status": "ok",
            "handoff_status": "ok",
            "issues_status": "ok",
        }), encoding="utf-8")
        stale = (started - timedelta(minutes=5)).timestamp()
        os.utime(self.report, (stale, stale))
        self.assertNotIn("PREVIOUS AUDIT — ALL GOOD", ui.read_summary())
        self.assertIn("not verified", ui.read_summary().lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
