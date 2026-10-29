#!/usr/bin/env python3
"""Integration regression tests for saved manual reviews in summary_report.py.

Exercise the actual report-loader and Core-guidance assignment expressions from
summary_report.py against the real Web UI persistence and readiness reconciler.
The rest of summary_report.py performs many unrelated live-report operations;
executing only these real top-level statements keeps tests offline and safe.

No Home Assistant access, network requests or changes outside temporary files.
Run: python3 ha_audit/test_manual_compatibility_summary_integration.py
"""

from __future__ import annotations

import ast
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import readiness_guidance as guidance
import web_ui as ui
from test_dynamic_correlation_reconciliation import (
    AUTH_GROUP, INSTALLED, TARGET, STATE_GROUP, base_guidance_inputs,
    dynamic_report, generic_report, group,
)


_SOURCE = Path(__file__).with_name("summary_report.py")


def report_assignments() -> object:
    """Compile exactly the relevant production assignments, not a test copy."""
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"), filename=str(_SOURCE))
    wanted = ("saved_context", "manual_compatibility_reviews", "core_guidance")
    selected = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in wanted:
                    if target.id in selected:
                        raise AssertionError(f"Duplicate production assignment: {target.id}")
                    selected[target.id] = node
    if set(selected) != set(wanted):
        raise AssertionError(f"Summary integration is missing: {set(wanted) - set(selected)}")
    body = [copy.deepcopy(selected[name]) for name in wanted]
    return compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])),
                   str(_SOURCE), "exec")


PRODUCTION_ASSIGNMENTS = report_assignments()


class ManualSummaryIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in ("CORE_READINESS", "CORE_CORRELATION", "RUN_STATE", "CONTEXT", "REPORT"):
            p = patch.object(ui, name, self.root / getattr(ui, name).name)
            p.start()
            self.addCleanup(p.stop)
        self.write(ui.CONTEXT, ui.initial_context())
        self.write(ui.CORE_READINESS, {
            "core_upgrade_window": {
                "pending": True,
                "installed_version": INSTALLED,
                "target_version": TARGET,
            }
        })
        self.write(ui.CORE_CORRELATION, {
            "scope": {"dynamic_correlation_performed": True},
            "summary": {"insufficient_evidence_count": 2,
                        "official_crossed_group_count": 2},
            "correlations": [
                group(*AUTH_GROUP),
                group(*STATE_GROUP),
            ],
        })

    @staticmethod
    def write(path, obj):
        path.write_text(json.dumps(obj), encoding="utf-8")

    def evaluate(self, *, correlation=None, checks=None, overrides=None):
        """Run production wiring, with only unrelated report inputs simulated."""
        base = base_guidance_inputs()
        base.update(overrides or {})
        arguments = {
            "core_update_pending": base["core_update_pending"],
            "update_readiness_available": base["update_readiness_available"],
            "core_window_complete": base["core_window_complete"],
            "collector_errors": ["error"] * base["collector_error_count"],
            "config_result": base["configuration_check_state"],
            "release_collection_complete": base["release_evidence_complete"],
            "coverage_usable": base["compatibility_coverage_usable"],
            "correlation_complete": base["dynamic_correlation_complete"],
            "correlation_insufficient_count": base["dynamic_correlation_insufficient_count"],
            "validation_usable": base["correlation_validation_usable"],
            "deterministic_compatibility_required": base["deterministic_compatibility_required"],
            "compatibility_assessed": base["deterministic_compatibility_available"],
            "compatibility_yaml_failures": ["read error"] * base["deterministic_yaml_failure_count"],
            "readiness_relevant_unignored_count": base["relevant_unignored_repair_count"],
            "compatibility_review_required_count": base["compatibility_review_required_count"],
            "compatibility_manual_review_count": base["compatibility_manual_review_count"],
            "generic_core_checks": generic_report() if checks is None else checks,
            "core_installed_version": INSTALLED,
            "core_target_version": TARGET,
            "upgrade_correlation_report": dynamic_report() if correlation is None else correlation,
            "INVESTIGATION_CONTEXT_FILE": str(ui.CONTEXT),
            "load_json_optional": self.optional_json,
            "evaluate_core_update_guidance": guidance.evaluate_core_update_guidance,
        }
        exec(PRODUCTION_ASSIGNMENTS, arguments)
        return arguments["core_guidance"], arguments["manual_compatibility_reviews"]

    @staticmethod
    def optional_json(path):
        try:
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        except (OSError, ValueError):
            return {}

    def confirm_auth(self):
        status, message = ui.save_manual_core_review(*AUTH_GROUP, "confirmed")
        self.assertEqual(status, 200, message)

    def assert_incomplete(self, decision):
        self.assertEqual(decision["status"], guidance.STATE_INCOMPLETE)
        self.assertIn("dynamic_correlation_insufficient_evidence", decision["reason_codes"])
        self.assertEqual(decision["dynamic_reconciliation"]["remaining_insufficient_count"], 1)
        self.assertIn({"release_family": AUTH_GROUP[0], "heading": AUTH_GROUP[1]},
                      decision["dynamic_reconciliation"]["unresolved_groups"])

    def test_missing_confirmation_does_not_clear_authentication(self):
        decision, manual = self.evaluate()
        self.assertIsNone(manual)
        self.assert_incomplete(decision)

    def test_explicit_ui_confirmation_flows_through_production_summary(self):
        self.confirm_auth()
        decision, manual = self.evaluate()
        self.assertEqual(manual["target_version"], TARGET)
        self.assertEqual(decision["status"], guidance.STATE_CLEAR)
        self.assertEqual(decision["dynamic_reconciliation"]["remaining_insufficient_count"], 0)
        resolved = decision["dynamic_reconciliation"]["resolved_groups"]
        self.assertEqual(len(resolved), 2)
        self.assertEqual(
            {row["heading"]: row.get("source", "generic_rule") for row in resolved},
            {"Authentication": "explicit_user_confirmation", "State conditions": "generic_rule"},
        )

    def test_revoked_confirmation_restores_incomplete_status(self):
        self.confirm_auth()
        status, message = ui.save_manual_core_review(*AUTH_GROUP, "remove")
        self.assertEqual(status, 200, message)
        decision, manual = self.evaluate()
        self.assertEqual(manual["reviews"], [])
        self.assert_incomplete(decision)

    def test_confirmed_review_preserves_existing_investigation_notes(self):
        existing = ui.initial_context()
        existing["investigations"]["sonos"] = {"status": "Explained", "note": "User check"}
        existing["scheduled_events"] = [{"name": "maintenance"}]
        self.write(ui.CONTEXT, existing)
        self.confirm_auth()
        decision, _ = self.evaluate()
        self.assertEqual(decision["status"], guidance.STATE_CLEAR)
        updated = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        self.assertEqual(updated["investigations"], existing["investigations"])
        self.assertEqual(updated["scheduled_events"], existing["scheduled_events"])

    def test_confirmation_for_wrong_target_is_not_reused(self):
        self.confirm_auth()
        existing = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        existing["manual_compatibility_review"]["target_version"] = "2026.10.1"
        self.write(ui.CONTEXT, existing)
        decision, manual = self.evaluate()
        self.assertIsNotNone(manual)
        self.assert_incomplete(decision)

    def test_confirmation_for_wrong_installed_is_not_reused(self):
        self.confirm_auth()
        existing = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        existing["manual_compatibility_review"]["installed_version"] = "2026.9.4"
        self.write(ui.CONTEXT, existing)
        decision, _ = self.evaluate()
        self.assert_incomplete(decision)

    def test_no_user_provenance_cannot_clear_uncertainty(self):
        self.confirm_auth()
        existing = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        existing["manual_compatibility_review"]["reviews"][0]["source"] = "assistant_inference"
        self.write(ui.CONTEXT, existing)
        decision, _ = self.evaluate()
        self.assert_incomplete(decision)

    def test_user_unticked_confirmation_cannot_clear_uncertainty(self):
        self.confirm_auth()
        existing = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        existing["manual_compatibility_review"]["reviews"][0]["confirmed_by_user"] = False
        self.write(ui.CONTEXT, existing)
        decision, _ = self.evaluate()
        self.assert_incomplete(decision)

    def test_corrupted_or_missing_context_does_not_clear_uncertainty(self):
        for action in ("corrupt", "missing"):
            with self.subTest(action=action):
                if action == "corrupt":
                    ui.CONTEXT.write_text("bad JSON", encoding="utf-8")
                else:
                    ui.CONTEXT.unlink(missing_ok=True)
                decision, manual = self.evaluate()
                self.assertIsNone(manual)
                self.assert_incomplete(decision)

    def test_invalid_context_schema_does_not_clear_uncertainty(self):
        self.confirm_auth()
        existing = json.loads(ui.CONTEXT.read_text(encoding="utf-8"))
        existing["schema_version"] = 999
        self.write(ui.CONTEXT, existing)
        decision, manual = self.evaluate()
        self.assertIsNone(manual)
        self.assert_incomplete(decision)

    def test_manual_confirmation_cannot_hide_other_unassessed_change(self):
        self.confirm_auth()
        correlated = dynamic_report(group(*AUTH_GROUP), group(*STATE_GROUP),
                                    group("2026.9", "Unreviewed change"))
        decision, _ = self.evaluate(
            correlation=correlated,
            overrides={"dynamic_correlation_insufficient_count": 3},
        )
        self.assertEqual(decision["status"], guidance.STATE_INCOMPLETE)
        self.assertEqual(decision["dynamic_reconciliation"]["remaining_insufficient_count"], 1)
        self.assertEqual(decision["dynamic_reconciliation"]["unresolved_groups"],
                         [{"release_family": "2026.9", "heading": "Unreviewed change"}])

    def test_manual_confirmation_does_not_override_independent_evidence_failure(self):
        self.confirm_auth()
        decision, _ = self.evaluate(overrides={"release_evidence_complete": False})
        self.assertEqual(decision["status"], guidance.STATE_INCOMPLETE)
        self.assertIn("official_release_evidence_incomplete", decision["reason_codes"])

    def test_manual_confirmation_does_not_override_repair_needing_review(self):
        self.confirm_auth()
        decision, _ = self.evaluate(overrides={"relevant_unignored_repair_count": 1})
        self.assertEqual(decision["status"], guidance.STATE_REVIEW)
        self.assertIn("relevant_unignored_repair", decision["reason_codes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
