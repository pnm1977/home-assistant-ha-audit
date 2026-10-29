#!/usr/bin/env python3
"""Permanent regression tests for explicit manual Core-change reviews in the UI.

All inputs are synthetic and stored in a temporary directory. The tests neither
start the web server nor modify /config, Home Assistant, or the user's saved
investigations. A saved review is a scoped *user assertion*, not a safety verdict.

Run: python -m unittest -v test_manual_compatibility_web_ui
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import web_ui as ui


INSTALLED = "2026.8.3"
TARGET = "2026.10.4"
AUTH = ("2026.10", "Authentication")
STATE = ("2026.10", "State conditions")


class ManualCompatibilityWebUITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for name in ("CORE_READINESS", "CORE_CORRELATION", "RUN_STATE", "CONTEXT", "REPORT"):
            patcher = patch.object(ui, name, self.root / getattr(ui, name).name)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.write_json(ui.CONTEXT, ui.initial_context())
        self.write_json(ui.CORE_READINESS, {
            "core_upgrade_window": {
                "pending": True,
                "installed_version": INSTALLED,
                "target_version": TARGET,
            },
        })
        self.write_json(ui.CORE_CORRELATION, {
            "scope": {"dynamic_correlation_performed": True},
            "summary": {
                "insufficient_evidence_count": 2,
                "official_crossed_group_count": 3,
            },
            "correlations": [
                {"release_family": AUTH[0], "heading": AUTH[1],
                 "correlation_status": "insufficient_evidence"},
                {"release_family": STATE[0], "heading": STATE[1],
                 "correlation_status": "insufficient_evidence"},
                {"release_family": "2026.9", "heading": "KNX",
                 "correlation_status": "no_local_evidence"},
            ],
        })

    @staticmethod
    def write_json(path: Path, value: dict) -> None:
        path.write_text(json.dumps(value), encoding="utf-8")

    def read_json(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def review(self, group=AUTH, decision="confirmed"):
        return ui.save_manual_core_review(group[0], group[1], decision)

    def test_shows_only_insufficient_official_groups_and_upgrade_window(self):
        page = ui.build_manual_core_review()
        self.assertIn("Authentication", page)
        self.assertIn("State conditions", page)
        self.assertNotIn("KNX", page)
        self.assertIn(INSTALLED, page)
        self.assertIn(TARGET, page)
        self.assertIn('name="confirmed" value="yes" required', page)

    def test_explicit_confirmation_is_saved_with_correct_schema_and_identity(self):
        status, message = self.review()
        self.assertEqual(status, 200, message)
        saved = ui.load_context()["manual_compatibility_review"]
        self.assertEqual(saved["schema_version"], 1)
        self.assertEqual((saved["installed_version"], saved["target_version"]),
                         (INSTALLED, TARGET))
        self.assertEqual(len(saved["reviews"]), 1)
        record = saved["reviews"][0]
        self.assertEqual((record["release_family"], record["official_group"]), AUTH)
        self.assertEqual(record["source"], "explicit_user_confirmation")
        self.assertEqual(record["outcome"], "user_checked_no_issue")
        self.assertIs(record["confirmed_by_user"], True)
        self.assertTrue(record["reviewed_at"])
        self.assertIn("Revoke my confirmation", ui.build_manual_core_review())

    def test_confirmation_must_be_explicit_and_is_not_default(self):
        html = ui.build_manual_core_review()
        self.assertNotIn("Revoke my confirmation", html)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_revocation_removes_only_selected_confirmation(self):
        self.assertEqual(self.review(AUTH)[0], 200)
        self.assertEqual(self.review(STATE)[0], 200)
        self.assertEqual(self.review(AUTH, "remove")[0], 200)
        records = ui.load_context()["manual_compatibility_review"]["reviews"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["official_group"], STATE[1])
        page = ui.build_manual_core_review()
        self.assertIn("Revoke my confirmation", page)
        self.assertIn("Save my confirmation", page)

    def test_rejects_unrelated_or_non_insufficient_change_group(self):
        for group in (("2026.9", "KNX"), ("2027.1", "Authentication"),
                      (AUTH[0], "Unknown change")):
            with self.subTest(group=group):
                self.assertEqual(self.review(group)[0], 400)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_rejects_unsupported_decisions(self):
        self.assertEqual(self.review(decision="ignore")[0], 400)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_saves_do_not_overwrite_investigation_notes_or_schedules(self):
        data = ui.initial_context()
        data["investigations"]["example"] = {
            "status": "Explained", "note": "Physical connection confirmed", "history": [1],
        }
        data["scheduled_events"] = [{"name": "Maintenance"}]
        self.write_json(ui.CONTEXT, data)
        self.assertEqual(self.review()[0], 200)
        after = ui.load_context()
        self.assertEqual(after["investigations"], data["investigations"])
        self.assertEqual(after["scheduled_events"], data["scheduled_events"])

    def test_new_target_version_does_not_inherit_confirmation(self):
        self.assertEqual(self.review()[0], 200)
        readiness = self.read_json(ui.CORE_READINESS)
        readiness["core_upgrade_window"]["target_version"] = "2026.11.1"
        self.write_json(ui.CORE_READINESS, readiness)
        self.assertNotIn("Revoke my confirmation", ui.build_manual_core_review())
        self.assertEqual(self.review()[0], 200)
        saved = ui.load_context()["manual_compatibility_review"]
        self.assertEqual(saved["target_version"], "2026.11.1")

    def test_inconsistent_official_summary_rejects_changes(self):
        correlation = self.read_json(ui.CORE_CORRELATION)
        correlation["summary"]["insufficient_evidence_count"] = 3
        self.write_json(ui.CORE_CORRELATION, correlation)
        self.assertEqual(self.review()[0], 409)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_duplicate_official_group_rejects_changes(self):
        correlation = self.read_json(ui.CORE_CORRELATION)
        correlation["correlations"].append(dict(correlation["correlations"][0]))
        correlation["summary"]["insufficient_evidence_count"] = 3
        correlation["summary"]["official_crossed_group_count"] = 4
        self.write_json(ui.CORE_CORRELATION, correlation)
        self.assertEqual(self.review()[0], 409)

    def test_missing_or_unreadable_evidence_rejects_changes(self):
        ui.CORE_CORRELATION.unlink()
        self.assertEqual(self.review()[0], 409)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_no_pending_core_upgrade_rejects_confirmation(self):
        readiness = self.read_json(ui.CORE_READINESS)
        readiness["core_upgrade_window"]["pending"] = False
        self.write_json(ui.CORE_READINESS, readiness)
        self.assertEqual(self.review()[0], 409)
        self.assertNotIn("manual_compatibility_review", ui.load_context())

    def test_failed_write_preserves_existing_data(self):
        self.assertEqual(self.review()[0], 200)
        before = ui.CONTEXT.read_bytes()
        with patch.object(ui, "atomic_save", side_effect=OSError("simulated disk error")):
            status, _ = self.review(decision="remove")
        self.assertEqual(status, 503)
        self.assertEqual(ui.CONTEXT.read_bytes(), before)

    def test_failed_latest_audit_disables_review(self):
        self.write_json(ui.RUN_STATE, {"status": "incomplete"})
        self.assertIsNone(ui.current_manual_review_scope())
        self.assertEqual(self.review()[0], 409)
        self.assertIn("No current, verified Core-change report", ui.build_manual_core_review())

    def test_stale_correlation_rejected_even_with_complete_audit(self):
        ui.REPORT.write_text("Fresh report", encoding="utf-8")
        started = datetime.now(timezone.utc) - timedelta(seconds=10)
        self.write_json(ui.RUN_STATE, {
            "status": "complete", "summary_status": "ok",
            "run_started_at_utc": started.isoformat(),
        })
        stale = started.timestamp() - 60
        os.utime(ui.CORE_CORRELATION, (stale, stale))
        self.assertIsNone(ui.current_manual_review_scope())
        self.assertEqual(self.review()[0], 409)

    def test_official_names_are_html_escaped(self):
        correlation = self.read_json(ui.CORE_CORRELATION)
        label = '<img src=x onerror="alert(1)">'
        correlation["correlations"][0]["heading"] = label
        self.write_json(ui.CORE_CORRELATION, correlation)
        rendered = ui.build_manual_core_review()
        self.assertNotIn(label, rendered)
        self.assertIn("&lt;img", rendered)
        self.assertIn("&quot;alert(1)&quot;", rendered)


if __name__ == "__main__":
    unittest.main()
