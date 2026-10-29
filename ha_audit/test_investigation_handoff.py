#!/usr/bin/env python3
"""Regression tests for the existing investigation AI-handoff stage.

Run: python3 ha_audit/test_investigation_handoff.py
No Home Assistant calls, existing reports, or persistent user settings are changed.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import investigation_handoff as handoff


SHEL = "lfp_shelly_example"
SON = "lfp_sonos_example"


def family(fingerprint, family_id, name):
    return {
        "stable_fingerprint": fingerprint,
        "family_id": family_id,
        "title": name,
        "final_priority": "HIGH",
    }


def saved(status, note="User has investigated this issue.", **kwargs):
    return {
        "status": status,
        "note": note,
        "updated_at_utc": "2026-10-29T13:05:00+00:00",
        "history": [{"note": note}],
        **kwargs,
    }


def maintenance_window():
    return {
        "schedule": "daily",
        "start_local": "03:00",
        "end_local": "03:05",
        "timezone": "Europe/London",
    }


def data():
    return (
        {"schema_version": 1, "investigations": {
            SON: saved("Explained", power_entity_id="switch.backroom_tv_cabinet_r"),
            SHEL: saved("Monitoring", title="Shelly integration data retrieval",
                        maintenance_window=maintenance_window()),
        }},
        {"families": [
            family(SON, "sonos", "Sonos connectivity"),
            family(SHEL, "shelly", "Shelly integration data retrieval"),
        ]},
    )


class InvestigationHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_full_notes_are_kept_and_marked_user_reported(self):
        context, findings = data()
        long_note = "An investigation note with supporting details. " * 22
        self.assertGreater(len(long_note), 500)
        self.assertLess(len(long_note), 4000)
        context["investigations"][SON]["note"] = long_note
        appendix = handoff.make_appendix(context, findings)
        self.assertIn(long_note.strip(), appendix)
        self.assertIn("user-reported context", appendix)
        self.assertIn("original audit priorities remain unchanged", appendix.lower())
        self.assertIn("Current finding; audit priority: HIGH", appendix)

    def test_missing_or_invalid_feedback_does_not_create_appendix(self):
        context, findings = data()
        context["schema_version"] = 99
        self.assertEqual(handoff.make_appendix(context, findings), "")
        context["schema_version"] = 1
        context["investigations"][SON]["status"] = "Not-a-real-status"
        context["investigations"][SHEL]["note"] = " "
        self.assertEqual(handoff.make_appendix(context, findings), "")

    def test_historical_findings_remain_labelled_historical(self):
        context, findings = data()
        findings["families"] = [family(SON, "sonos", "Sonos connectivity")]
        appendix = handoff.make_appendix(context, findings)
        self.assertIn("Historical finding; not in current result", appendix)
        self.assertIn("Current finding; audit priority: HIGH", appendix)
        self.assertLess(appendix.index("### Sonos connectivity"),
                        appendix.index("### Shelly integration data retrieval"))

    def test_handoff_appendix_replaces_instead_of_duplicating(self):
        document = self.folder / "handoff.md"
        document.write_text("# HA Audit AI / LLM Handoff\n\nOriginal output.\n", encoding="utf-8")
        context, findings = data()
        first = handoff.make_appendix(context, findings)
        self.assertTrue(handoff.update_handoff(document, first))
        context["investigations"][SON]["note"] = "Replacement explanation"
        second = handoff.make_appendix(context, findings)
        self.assertTrue(handoff.update_handoff(document, second))
        output = document.read_text(encoding="utf-8")
        self.assertEqual(output.count(handoff.START_MARKER), 1)
        self.assertEqual(output.count(handoff.END_MARKER), 1)
        self.assertIn("Original output.", output)
        self.assertIn("Replacement explanation", output)
        self.assertNotIn("User has investigated this issue.",
                         output.split("### Sonos connectivity", 1)[1].split("### Shelly", 1)[0])

    def test_incomplete_existing_appendix_is_not_overwritten(self):
        document = self.folder / "handoff.md"
        original = "# Handoff\n" + handoff.START_MARKER + "\nIncomplete\n"
        document.write_text(original, encoding="utf-8")
        self.assertFalse(handoff.update_handoff(document, "new appendix"))
        self.assertEqual(document.read_text(encoding="utf-8"), original)

    def test_power_evidence_does_not_change_priority_or_status(self):
        context, findings = data()
        before = json.dumps((context, findings), sort_keys=True)
        checker_response = {"status": "ok", "samples": [
            {"observed_at_utc": "2026-10-29T11:18:45+00:00", "power_state": "off", "evidence": "Recorder off"},
            {"observed_at_utc": "2026-10-29T11:18:48+00:00", "power_state": "on", "evidence": "Recorder on"},
        ]}
        with patch.object(handoff, "check_power_state", return_value=checker_response) as mocked:
            result = handoff.gather_power_evidence(context, findings)
        mocked.assert_called_once_with("sonos", "switch.backroom_tv_cabinet_r")
        row = result["findings"][SON]
        self.assertEqual(row["counts"], {"off": 1, "on": 1, "unknown": 0})
        self.assertEqual(row["audit_priority"], "HIGH")
        self.assertEqual(row["user_status"], "Explained")
        self.assertEqual(row["interpretation"], "Needs investigation")
        self.assertFalse(result["changes_audit_priorities"])
        self.assertEqual(json.dumps((context, findings), sort_keys=True), before)

    def test_power_checker_failure_keeps_evidence_unknown(self):
        context, findings = data()
        with patch.object(handoff, "check_power_state", side_effect=RuntimeError("offline")):
            result = handoff.gather_power_evidence(context, findings)
        row = result["findings"][SON]
        self.assertEqual(row["sample_count"], 0)
        self.assertEqual(row["interpretation"], "Insufficient evidence")
        self.assertEqual(row["source_status"], "unavailable")

    def test_maintenance_evidence_keeps_outside_samples_visible(self):
        context, findings = data()
        response = {"status": "ok", "source_occurrence_count": 64, "samples": [
            {"observed_at_utc": "2026-10-21T11:56:19+00:00",
             "observed_at_local": "2026-10-21T12:56:19+01:00", "window_match": "outside"},
            {"observed_at_utc": "2026-10-29T03:01:14+00:00",
             "observed_at_local": "2026-10-29T03:01:14+00:00", "window_match": "inside"},
        ]}
        with patch.object(handoff, "check_maintenance_window", return_value=response) as mocked:
            result = handoff.gather_maintenance_evidence(context, findings)
        mocked.assert_called_once_with("shelly", maintenance_window())
        row = result["findings"][SHEL]
        self.assertEqual(row["counts"], {"inside": 1, "outside": 1, "unknown": 0})
        self.assertEqual(row["source_occurrence_count"], 64)
        self.assertEqual(row["sample_count"], 2)
        self.assertEqual(row["user_status"], "Monitoring")
        self.assertEqual(row["audit_priority"], "HIGH")
        self.assertIn("outside", row["recommendation"].lower())
        self.assertFalse(result["changes_audit_priorities"])

    def test_maintenance_failure_does_not_claim_matching_window(self):
        context, findings = data()
        with patch.object(handoff, "check_maintenance_window", side_effect=ValueError("bad schedule")):
            result = handoff.gather_maintenance_evidence(context, findings)
        row = result["findings"][SHEL]
        self.assertEqual(row["counts"]["inside"], 0)
        self.assertEqual(row["source_status"], "unavailable")
        self.assertIn("do not assume", row["recommendation"].lower())

    def test_atomic_evidence_snapshots_do_not_change_existing_feedback(self):
        power_path = self.folder / "power.json"
        maintenance_path = self.folder / "maintenance.json"
        context_path = self.folder / "context.json"
        context_path.write_text("{\"user_notes\":\"keep\"}", encoding="utf-8")
        original = context_path.read_bytes()
        report = {"changes_audit_priorities": False, "findings": {}}
        with patch.object(handoff, "EVIDENCE_FILE", power_path), patch.object(
                handoff, "MAINTENANCE_EVIDENCE_FILE", maintenance_path):
            self.assertTrue(handoff.save_evidence_snapshot(report))
            self.assertTrue(handoff.save_maintenance_snapshot(report))
        self.assertEqual(json.loads(power_path.read_text(encoding="utf-8")), report)
        self.assertEqual(json.loads(maintenance_path.read_text(encoding="utf-8")), report)
        self.assertEqual(context_path.read_bytes(), original)
        if os.name == "posix":
            self.assertEqual(power_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(maintenance_path.stat().st_mode & 0o777, 0o600)

    def test_main_with_no_saved_feedback_keeps_existing_handoff_unchanged(self):
        context_path = self.folder / "missing_context.json"
        handoff_path = self.folder / "handoff.md"
        handoff_path.write_text("# Existing handoff\n", encoding="utf-8")
        with patch.object(handoff, "CONTEXT_FILE", context_path), patch.object(
                handoff, "HANDOFF_FILE", handoff_path):
            handoff.main()
        self.assertEqual(handoff_path.read_text(encoding="utf-8"), "# Existing handoff\n")

    def test_complete_handoff_includes_both_evidence_types_without_mutating_inputs(self):
        context, findings = data()
        context_path = self.folder / "investigations.json"
        findings_path = self.folder / "findings.json"
        handoff_path = self.folder / "handoff.md"
        power_path = self.folder / "power.json"
        maintenance_path = self.folder / "maintenance.json"
        context_path.write_text(json.dumps(context), encoding="utf-8")
        findings_path.write_text(json.dumps(findings), encoding="utf-8")
        handoff_path.write_text("# Summary\n\nUnmodified technical priority.\n", encoding="utf-8")
        context_before = context_path.read_bytes()
        findings_before = findings_path.read_bytes()
        power_return = {"status": "ok", "samples": [{
            "observed_at_utc": "2026-10-29T11:18:52+00:00", "power_state": "off",
            "evidence": "Recorder at timestamp",
        }]}
        maintenance_return = {"status": "ok", "source_occurrence_count": 64, "samples": [{
            "observed_at_utc": "2026-10-29T03:01:14+00:00",
            "observed_at_local": "2026-10-29T03:01:14+00:00",
            "window_match": "inside",
        }]}
        with patch.multiple(handoff, CONTEXT_FILE=context_path, FINDINGS_FILE=findings_path,
                            HANDOFF_FILE=handoff_path, EVIDENCE_FILE=power_path,
                            MAINTENANCE_EVIDENCE_FILE=maintenance_path), patch.object(
                                handoff, "check_power_state", return_value=power_return), patch.object(
                                handoff, "check_maintenance_window", return_value=maintenance_return):
            handoff.main()
        content = handoff_path.read_text(encoding="utf-8")
        self.assertIn("Unmodified technical priority.", content)
        self.assertIn("Original audit priority unchanged", content)
        self.assertIn("OFF 1, ON 0, UNKNOWN 0", content)
        self.assertIn("INSIDE 1, OUTSIDE 0, UNKNOWN 0", content)
        self.assertEqual(content.count(handoff.START_MARKER), 1)
        self.assertEqual(context_path.read_bytes(), context_before)
        self.assertEqual(findings_path.read_bytes(), findings_before)
        self.assertTrue(power_path.is_file())
        self.assertTrue(maintenance_path.is_file())


if __name__ == "__main__":
    unittest.main()
