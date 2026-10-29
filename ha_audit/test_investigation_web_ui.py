#!/usr/bin/env python3
"""Regression tests for the existing HA Audit investigation Web UI.

Runs offline with temporary files; never starts the server, calls Home
Assistant, or changes real /config investigation data.

Run with: python3 ha_audit/test_investigation_web_ui.py
"""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import web_ui as ui


FINGERPRINT = "lfp_web_ui_regression"
FAMILY = {
    "stable_fingerprint": FINGERPRINT,
    "family_id": "sonos",
    "title": "Sonos connectivity",
    "final_priority": "HIGH",
    "recurrence": {"class": "RECURRING 24H+"},
}
SWITCH = "switch.backroom_tv_cabinet_r"
SCHEDULE = {
    "schedule": "daily",
    "start_local": "03:00",
    "end_local": "03:05",
    "timezone": "Europe/London",
}


class InvestigationWebUITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (
            "CONTEXT", "ISSUES", "POWER_SNAPSHOT", "MAINTENANCE_SNAPSHOT",
            "RECURRENCE_REPORT", "REPORT", "HANDOFF",
        ):
            original = getattr(ui, name)
            path = self.root / original.name
            patcher = patch.object(ui, name, path)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.issues = {
            "audit_version": "0.8.23",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "families": [FAMILY],
        }
        self._json(ui.ISSUES, self.issues)
        self._json(ui.CONTEXT, ui.initial_context())

    @staticmethod
    def _json(path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def _saved(self, status="Explained", *, power=SWITCH, window=None):
        record = {
            "family_id": FAMILY["family_id"],
            "status": status,
            "note": "Physical connection confirmed.",
            "power_entity_id": power,
            "updated_at_utc": "2026-10-29T11:36:03+00:00",
            "history": [],
        }
        if window is not None:
            record["maintenance_window"] = window
        data = ui.initial_context()
        data["investigations"][FINGERPRINT] = record
        self._json(ui.CONTEXT, data)
        return record

    def _power(self, saved, *, off=4, on=0, unknown=0):
        return {
            "schema_version": 1,
            "generated_at_utc": "2026-10-29T13:25:56+00:00",
            "findings": {FINGERPRINT: {
                "family_id": FAMILY["family_id"],
                "power_entity_id": saved["power_entity_id"],
                "feedback_updated_at_utc": saved["updated_at_utc"],
                "audit_priority": FAMILY["final_priority"],
                "sample_count": off + on + unknown,
                "counts": {"off": off, "on": on, "unknown": unknown},
                "source_status": "ok",
            }},
        }

    def _maintenance(self, saved):
        samples = [
            {"observed_at_utc": "2026-10-21T11:56:19+00:00", "window_match": "outside"},
            {"observed_at_utc": "2026-10-29T03:01:14+00:00", "window_match": "inside"},
        ]
        return {
            "schema_version": 1,
            "generated_at_utc": "2026-10-29T13:25:56+00:00",
            "findings": {FINGERPRINT: {
                "family_id": FAMILY["family_id"],
                "maintenance_window": saved["maintenance_window"],
                "feedback_updated_at_utc": saved["updated_at_utc"],
                "audit_priority": FAMILY["final_priority"],
                "sample_count": 2,
                "counts": {"inside": 1, "outside": 1, "unknown": 0},
                "samples": samples,
                "source_status": "ok",
                "source_occurrence_count": 64,
            }},
        }

    def test_initialisation_is_private_and_does_not_overwrite(self):
        ui.CONTEXT.unlink()
        self.assertIsNone(ui.initialize_context())
        self.assertEqual(ui.load_context()["investigations"], {})
        if __import__("os").name == "posix":
            self.assertEqual(ui.CONTEXT.stat().st_mode & 0o777, 0o600)
        self._saved()
        self.assertIsNone(ui.initialize_context())
        self.assertIn(FINGERPRINT, ui.load_context()["investigations"])

    def test_saves_full_length_notes_and_history(self):
        note = "N" * ui.MAX_NOTE_LENGTH
        code, _ = ui.save_feedback(FINGERPRINT, "Monitoring", note, SWITCH)
        self.assertEqual(code, 200)
        record = ui.load_context()["investigations"][FINGERPRINT]
        self.assertEqual(record["note"], note)
        self.assertEqual(record["power_entity_id"], SWITCH)
        self.assertEqual(len(record["history"]), 1)
        code, _ = ui.save_feedback(FINGERPRINT, "Explained", "New observation", SWITCH)
        self.assertEqual(code, 200)
        self.assertEqual(len(ui.load_context()["investigations"][FINGERPRINT]["history"]), 2)
        self.assertEqual(ui.current_families()[0]["final_priority"], "HIGH")

    def test_rejects_invalid_notes_statuses_switches_and_findings(self):
        checks = [
            ("Explained", "", SWITCH, FINGERPRINT),
            ("Explained", "N" * (ui.MAX_NOTE_LENGTH + 1), SWITCH, FINGERPRINT),
            ("Dismissed", "note", SWITCH, FINGERPRINT),
            ("Explained", "note", "light.not_a_power_switch", FINGERPRINT),
            ("Explained", "note", SWITCH, "unknown_fingerprint"),
        ]
        for status, note, switch, fingerprint in checks:
            with self.subTest(status=status, note_len=len(note), switch=switch, fingerprint=fingerprint):
                code, _ = ui.save_feedback(fingerprint, status, note, switch)
                self.assertEqual(code, 400)
        self.assertEqual(ui.load_context()["investigations"], {})

    def test_daily_weekly_monthly_and_overnight_schedule_validation(self):
        cases = [
            ({}, SCHEDULE),
            ({"frequency": "weekly", "weekdays": ["6", "0"]},
             {**SCHEDULE, "schedule": "weekly", "weekdays": [0, 6]}),
            ({"frequency": "monthly_date", "month_day": "31"},
             {**SCHEDULE, "schedule": "monthly_date", "day_of_month": 31}),
            ({"frequency": "monthly_weekday", "occurrence": "last", "weekday": "6"},
             {**SCHEDULE, "schedule": "monthly_weekday", "occurrence": "last", "weekday": 6}),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                actual, error = ui.validate_maintenance_window(
                    "03:00", "03:05", "Europe/London", **kwargs,
                )
                self.assertIsNone(error)
                self.assertEqual(actual, expected)
        overnight, error = ui.validate_maintenance_window("23:55", "00:10", "Europe/London")
        self.assertIsNone(error)
        self.assertEqual(overnight["end_local"], "00:10")

    def test_invalid_maintenance_schedules_are_rejected(self):
        cases = [
            ("03:00", "03:00", "Europe/London", {}),
            ("25:00", "03:05", "Europe/London", {}),
            ("03:00", "03:05", "???", {}),
            ("03:00", "03:05", "Europe/London", {"frequency": "weekly", "weekdays": []}),
            ("03:00", "03:05", "Europe/London", {"frequency": "weekly", "weekdays": ["0", "0"]}),
            ("03:00", "03:05", "Europe/London", {"frequency": "monthly_date", "month_day": "32"}),
            ("03:00", "03:05", "Europe/London", {"frequency": "monthly_weekday", "occurrence": "fifth", "weekday": "0"}),
        ]
        for start, end, tz, kw in cases:
            with self.subTest(case=(start, end, tz, kw)):
                _, error = ui.validate_maintenance_window(start, end, tz, **kw)
                self.assertIsNotNone(error)

    def test_saving_and_preserving_legacy_maintenance_schedule(self):
        code, _ = ui.save_feedback(FINGERPRINT, "Monitoring", "Check after reboot", "",
                                   "03:00", "03:05", "Europe/London")
        self.assertEqual(code, 200)
        code, _ = ui.save_feedback(FINGERPRINT, "Monitoring", "Still checking", "")
        self.assertEqual(code, 200)
        saved = ui.load_context()["investigations"][FINGERPRINT]
        self.assertEqual(saved["maintenance_window"], SCHEDULE)
        self.assertEqual(len(saved["history"]), 2)

    def test_clearing_schedule_preserves_note_and_power_relationship(self):
        self._saved(window=SCHEDULE)
        code, _ = ui.save_feedback(FINGERPRINT, "Monitoring", "Monitor", SWITCH,
                                   "", "", "", "daily")
        self.assertEqual(code, 200)
        saved = ui.load_context()["investigations"][FINGERPRINT]
        self.assertNotIn("maintenance_window", saved)
        self.assertEqual(saved["power_entity_id"], SWITCH)
        self.assertEqual(saved["note"], "Monitor")

    def test_power_evidence_off_only_and_on_precedence(self):
        saved = self._saved()
        self.assertEqual(ui.power_sample_assessment(FAMILY, saved, self._power(saved)), "off_only")
        self.assertEqual(ui.power_sample_assessment(FAMILY, saved, self._power(saved, off=2, on=1)), "on")
        self.assertEqual(ui.power_sample_assessment(FAMILY, saved, self._power(saved, off=2, unknown=1)), "unknown")
        self.assertEqual(ui.power_sample_assessment(FAMILY, saved, None), "unverified")

    def test_rejects_stale_or_bad_power_evidence(self):
        saved = self._saved()
        snapshot = self._power(saved)
        snapshot["findings"][FINGERPRINT]["feedback_updated_at_utc"] = "older revision"
        self.assertIsNone(ui.evidence_for_current_finding(FAMILY, saved, snapshot))
        snapshot = self._power(saved)
        snapshot["findings"][FINGERPRINT]["counts"]["off"] = 3  # inconsistent count
        self.assertIsNone(ui.evidence_for_current_finding(FAMILY, saved, snapshot))

    def test_rejects_stale_or_bad_maintenance_evidence(self):
        saved = self._saved(window=SCHEDULE)
        evidence = self._maintenance(saved)
        self.assertIsNotNone(ui.matching_maintenance_evidence(FAMILY, saved, evidence))
        saved_different = {**saved, "maintenance_window": {**SCHEDULE, "end_local": "03:10"}}
        self.assertIsNone(ui.matching_maintenance_evidence(FAMILY, saved_different, evidence))
        evidence["findings"][FINGERPRINT]["counts"]["inside"] = 2  # sample mismatch
        self.assertIsNone(ui.matching_maintenance_evidence(FAMILY, saved, evidence))

    def test_maintenance_recommendation_distinguishes_old_and_latest_samples(self):
        saved = self._saved(status="Monitoring", power="", window=SCHEDULE)
        html_text = ui.show_maintenance_summary(FAMILY, saved, self._maintenance(saved))
        self.assertIn("INSIDE 1 · OUTSIDE 1 · UNKNOWN 0", html_text)
        self.assertIn("older OUTSIDE-window evidence remains", html_text)
        self.assertIn("64 (not individually timestamped", html_text)
        self.assertIn("Original priority", html_text)

    def test_fails_closed_when_snapshot_is_older_than_issues(self):
        import os
        saved = self._saved(window=SCHEDULE)
        self._json(ui.POWER_SNAPSHOT, self._power(saved))
        self._json(ui.MAINTENANCE_SNAPSHOT, self._maintenance(saved))
        latest_time = ui.ISSUES.stat().st_mtime
        os.utime(ui.POWER_SNAPSHOT, (latest_time - 20, latest_time - 20))
        os.utime(ui.MAINTENANCE_SNAPSHOT, (latest_time - 20, latest_time - 20))
        self.assertIsNone(ui.last_audit_power_snapshot())
        self.assertIsNone(ui.last_audit_maintenance_snapshot())

    def test_activity_status_requires_same_run_and_exact_fingerprint(self):
        now = datetime.now(timezone.utc)
        self.issues["generated_at"] = now.isoformat()
        self._json(ui.ISSUES, self.issues)
        report = {
            "audit_version": "0.8.23", "status": "ok",
            "generated_at": (now - timedelta(seconds=5)).isoformat(),
            "families": [{"stable_fingerprint": FINGERPRINT, "family_id": "sonos",
                          "seen_in_latest_audit": True, "last_activity_status": "RETAINED EVIDENCE"}],
        }
        self._json(ui.RECURRENCE_REPORT, report)
        self.assertEqual(ui.latest_activity_by_fingerprint(), {FINGERPRINT: "RETAINED EVIDENCE"})
        report["families"][0]["family_id"] = "different_family"
        self._json(ui.RECURRENCE_REPORT, report)
        self.assertEqual(ui.latest_activity_by_fingerprint(), {})
        report["families"][0]["family_id"] = "sonos"
        report["generated_at"] = (now - timedelta(minutes=5)).isoformat()
        self._json(ui.RECURRENCE_REPORT, report)
        self.assertIsNone(ui.latest_activity_by_fingerprint())

    def test_where_to_focus_triage_does_not_edit_saved_status_or_priority(self):
        saved = self._saved(status="Explained")
        with (patch.object(ui, "last_audit_power_snapshot", return_value=self._power(saved)),
              patch.object(ui, "last_audit_maintenance_snapshot", return_value=None),
              patch.object(ui, "latest_activity_by_fingerprint", return_value=None)):
            page = ui.build_focus()
        self.assertIn("Sampled power-off — no immediate action <span class=\"focus-count\">(1)", page)
        self.assertIn("<strong>HIGH</strong> Sonos connectivity", page)
        with (patch.object(ui, "last_audit_power_snapshot", return_value=self._power(saved, off=1, on=1)),
              patch.object(ui, "last_audit_maintenance_snapshot", return_value=None),
              patch.object(ui, "latest_activity_by_fingerprint", return_value=None)):
            page = ui.build_focus()
        self.assertIn("Investigate / continue <span class=\"focus-count\">(1)", page)
        self.assertEqual(ui.load_context()["investigations"][FINGERPRINT]["status"], "Explained")
        self.assertEqual(ui.current_families()[0]["final_priority"], "HIGH")

    def test_web_page_escapes_saved_user_text(self):
        saved = self._saved()
        data = ui.load_context()
        data["investigations"][FINGERPRINT]["note"] = '<script>alert("x")</script>'
        self._json(ui.CONTEXT, data)
        with (patch.object(ui, "last_audit_power_snapshot", return_value=None),
              patch.object(ui, "last_audit_maintenance_snapshot", return_value=None),
              patch.object(ui, "latest_activity_by_fingerprint", return_value=None)):
            page = ui.build_issues()
        self.assertNotIn('<script>alert("x")</script>', page)
        self.assertIn('&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;', page)


if __name__ == "__main__":
    unittest.main(verbosity=2)
