"""Regression protection for generic Core check evidence in readiness guidance.

Run: python -m unittest -v test_generic_readiness_guidance

The generic checks are one evidence source, not a guarantee that upgrading is
safe. Keep the existing dynamic, official and deterministic evidence independent.
"""

import copy
import tempfile
import unittest
from pathlib import Path

from core_compatibility_runner import inspect_upgrade
from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
    classify_generic_compatibility_evidence,
    evaluate_core_update_guidance,
)


INSTALLED = "2026.8.3"
TARGET = "2026.10.4"


def clear_evidence():
    """All *other* readiness sources complete, for isolated precedence tests."""
    return {
        "core_update_pending": True,
        "update_readiness_available": True,
        "core_window_complete": True,
        "collector_error_count": 0,
        "configuration_check_state": "valid",
        "release_evidence_complete": True,
        "compatibility_coverage_usable": True,
        "dynamic_correlation_complete": True,
        "dynamic_correlation_insufficient_count": 0,
        "correlation_validation_usable": True,
        "deterministic_compatibility_required": False,
        "deterministic_compatibility_available": False,
        "deterministic_yaml_failure_count": 0,
        "relevant_unignored_repair_count": 0,
        "compatibility_review_required_count": 0,
        "compatibility_manual_review_count": 0,
    }


def generic_report(*, affected=False):
    findings = ([{
        "file": "automations.yaml",
        "line": 1,
        "reasons": ["attribute_with_for"],
    }] if affected else [])
    return {
        "schema_version": 1,
        "installed_version": INSTALLED,
        "target_version": TARGET,
        "status": "local_checks_completed",
        "selected_rule_count": 1,
        "rules": [{
            "rule_id": "core_2026_10_state_conditions_for",
            "status": "review_required" if affected else "no_affected_usage_found",
            "files_checked": 139,
            "findings": copy.deepcopy(findings),
            "read_failures": [],
        }],
        "findings": copy.deepcopy(findings),
        "read_failures": [],
        "summary": {
            "review_required_count": 1 if affected else 0,
            "incomplete_rule_count": 0,
            "checked_yaml_file_count": 139,
        },
    }


def no_registered_report():
    report = generic_report()
    report.update({
        "status": "no_registered_checks",
        "selected_rule_count": 0,
        "rules": [],
        "findings": [],
        "summary": {
            "review_required_count": 0,
            "incomplete_rule_count": 0,
            "checked_yaml_file_count": 0,
        },
    })
    return report


class EvidenceClassificationTests(unittest.TestCase):
    def classify(self, report):
        return classify_generic_compatibility_evidence(
            report, installed_version=INSTALLED, target_version=TARGET)

    def test_completed_check_without_findings_is_checked_not_safe(self):
        self.assertEqual(self.classify(generic_report()), "checked")

    def test_affected_configuration_requires_review(self):
        self.assertEqual(self.classify(generic_report(affected=True)), "review")

    def test_unregistered_family_not_error_or_clearance(self):
        self.assertEqual(self.classify(no_registered_report()), "not_applicable")

    def test_missing_report_is_incomplete(self):
        self.assertEqual(self.classify(None), "incomplete")

    def test_wrong_target_version_is_stale(self):
        report = generic_report()
        report["target_version"] = "2026.10.1"
        self.assertEqual(self.classify(report), "incomplete")

    def test_wrong_installed_version_is_stale(self):
        report = generic_report()
        report["installed_version"] = "2026.9.4"
        self.assertEqual(self.classify(report), "incomplete")

    def test_missing_requested_versions_are_incomplete(self):
        report = generic_report()
        self.assertEqual(classify_generic_compatibility_evidence(
            report, installed_version=None, target_version=TARGET), "incomplete")
        self.assertEqual(classify_generic_compatibility_evidence(
            report, installed_version=INSTALLED, target_version=None), "incomplete")

    def test_unknown_schema_is_incomplete(self):
        report = generic_report()
        report["schema_version"] = 2
        self.assertEqual(self.classify(report), "incomplete")

    def test_unexpected_report_status_is_incomplete(self):
        report = generic_report()
        report["status"] = "incomplete"
        self.assertEqual(self.classify(report), "incomplete")

    def test_rule_count_mismatch_is_incomplete(self):
        report = generic_report()
        report["selected_rule_count"] = 2
        self.assertEqual(self.classify(report), "incomplete")

    def test_boolean_or_negative_rule_count_rejected(self):
        for bad_count in [True, -1, "1"]:
            with self.subTest(bad_count=bad_count):
                report = generic_report()
                report["selected_rule_count"] = bad_count
                self.assertEqual(self.classify(report), "incomplete")

    def test_top_level_read_failures_not_ignored(self):
        report = generic_report()
        report["read_failures"] = [{"file": "broken.yaml"}]
        self.assertEqual(self.classify(report), "incomplete")

    def test_rule_read_failures_not_ignored(self):
        report = generic_report()
        report["rules"][0]["read_failures"] = [{"file": "broken.yaml"}]
        self.assertEqual(self.classify(report), "incomplete")

    def test_rule_must_have_inspected_yaml(self):
        report = generic_report()
        report["rules"][0]["files_checked"] = 0
        self.assertEqual(self.classify(report), "incomplete")

    def test_rule_cannot_claim_clean_while_having_findings(self):
        report = generic_report(affected=True)
        report["rules"][0]["status"] = "no_affected_usage_found"
        self.assertEqual(self.classify(report), "incomplete")

    def test_review_status_requires_findings(self):
        report = generic_report()
        report["rules"][0]["status"] = "review_required"
        report["summary"]["review_required_count"] = 1
        self.assertEqual(self.classify(report), "incomplete")

    def test_inconsistent_review_count_is_incomplete(self):
        report = generic_report(affected=True)
        report["summary"]["review_required_count"] = 0
        self.assertEqual(self.classify(report), "incomplete")

    def test_reported_incomplete_rule_is_incomplete(self):
        report = generic_report()
        report["summary"]["incomplete_rule_count"] = 1
        self.assertEqual(self.classify(report), "incomplete")

    def test_no_registered_checks_must_not_contain_rules(self):
        report = no_registered_report()
        report["selected_rule_count"] = 1
        report["rules"] = generic_report()["rules"]
        self.assertEqual(self.classify(report), "incomplete")

    def test_zero_selected_with_completed_status_is_not_clean(self):
        report = no_registered_report()
        report["status"] = "local_checks_completed"
        self.assertEqual(self.classify(report), "incomplete")


class ReadinessIntegrationTests(unittest.TestCase):
    def guidance(self, report=None, **updates):
        inputs = clear_evidence()
        inputs.update({
            "generic_check_report": report,
            "generic_installed_version": INSTALLED,
            "generic_target_version": TARGET,
        })
        inputs.update(updates)
        return evaluate_core_update_guidance(**inputs)

    def test_generic_clean_keeps_other_evidence_decision(self):
        result = self.guidance(generic_report())
        self.assertEqual(result["status"], STATE_CLEAR)
        self.assertEqual(result["reason_codes"], [])

    def test_generic_review_results_in_review_required(self):
        result = self.guidance(generic_report(affected=True))
        self.assertEqual(result["status"], STATE_REVIEW)
        self.assertIn("generic_compatibility_review_required", result["reason_codes"])

    def test_generic_error_prevents_completed_assessment(self):
        report = generic_report()
        report["read_failures"] = [{"file": "automations.yaml"}]
        result = self.guidance(report)
        self.assertEqual(result["status"], STATE_INCOMPLETE)
        self.assertFalse(result["assessment_complete"])
        self.assertIn("generic_compatibility_evidence_incomplete", result["reason_codes"])

    def test_clean_generic_evidence_cannot_override_dynamic_uncertainty(self):
        result = self.guidance(generic_report(), dynamic_correlation_insufficient_count=2)
        self.assertEqual(result["status"], STATE_INCOMPLETE)
        self.assertIn("dynamic_correlation_insufficient_evidence", result["reason_codes"])

    def test_generic_review_cannot_override_dynamic_uncertainty(self):
        result = self.guidance(generic_report(affected=True), dynamic_correlation_insufficient_count=2)
        self.assertEqual(result["status"], STATE_INCOMPLETE)
        self.assertIn("generic_compatibility_review_required", result["reason_codes"])
        self.assertIn("dynamic_correlation_insufficient_evidence", result["reason_codes"])

    def test_no_registered_rules_cannot_clear_other_uncertainty(self):
        result = self.guidance(no_registered_report(), dynamic_correlation_complete=False)
        self.assertEqual(result["status"], STATE_INCOMPLETE)
        self.assertIn("dynamic_correlation_incomplete", result["reason_codes"])

    def test_not_registered_rules_do_not_impose_new_blocker(self):
        result = self.guidance(no_registered_report())
        self.assertEqual(result["status"], STATE_CLEAR)
        self.assertEqual(result["reason_codes"], [])

    def test_absent_generic_report_preserves_existing_behaviour(self):
        result = self.guidance(None)
        self.assertEqual(result["status"], STATE_CLEAR)
        self.assertEqual(result["reason_codes"], [])

    def test_no_core_update_has_precedence(self):
        report = generic_report(affected=True)
        result = self.guidance(report, core_update_pending=False)
        self.assertEqual(result["status"], STATE_NO_UPDATE)

    def test_known_blocker_has_precedence(self):
        result = self.guidance(generic_report(), known_blocker_count=1)
        self.assertEqual(result["status"], STATE_BLOCKER)

    def test_stale_versions_are_incomplete_at_guidance_boundary(self):
        result = self.guidance(generic_report(), generic_target_version="2026.11.1")
        self.assertEqual(result["status"], STATE_INCOMPLETE)
        self.assertIn("generic_compatibility_evidence_incomplete", result["reason_codes"])


class ActualRunnerContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.file = self.root / "automations.yaml"
        self.quality = {"configuration_tree": {"active_yaml": ["automations.yaml"]}}

    def runner_report(self, yaml):
        self.file.write_text(yaml, encoding="utf-8")
        return inspect_upgrade(INSTALLED, TARGET, self.quality, self.root)

    def test_real_runner_clear_report_is_recognised(self):
        report = self.runner_report(
            '- condition: state\n  entity_id: binary_sensor.door\n'
            '  state: "on"\n  for: "00:00:10"\n')
        self.assertEqual(report["status"], "local_checks_completed")
        self.assertEqual(classify_generic_compatibility_evidence(
            report, installed_version=INSTALLED, target_version=TARGET), "checked")

    def test_real_runner_review_report_is_recognised(self):
        report = self.runner_report(
            '- condition: state\n  entity_id: binary_sensor.door\n'
            '  state: "on"\n  attribute: value\n  for: "00:00:10"\n')
        self.assertEqual(report["status"], "local_checks_completed")
        self.assertEqual(classify_generic_compatibility_evidence(
            report, installed_version=INSTALLED, target_version=TARGET), "review")

    def test_real_runner_yaml_failure_cannot_pass_as_checked(self):
        report = self.runner_report('- condition: state\n  for: [unterminated\n')
        self.assertEqual(report["status"], "incomplete")
        self.assertEqual(classify_generic_compatibility_evidence(
            report, installed_version=INSTALLED, target_version=TARGET), "incomplete")


if __name__ == "__main__":
    unittest.main()
