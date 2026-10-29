"""Regression contract for reconciling dynamic Core uncertainty with local checks.

The first two tests guard existing behaviour. Tests marked expectedFailure
specify the upcoming integration contract, and must be made normal passing
regressions after the readiness-guidance implementation lands.

Run: python -m unittest -v test_dynamic_correlation_reconciliation

Safety: a check may resolve ONLY a matching official (release family, group)
that dynamic correlation classified as insufficient. A non-match, failed or
stale check must not reduce uncertainty. A positive finding remains reviewable.
"""

import copy
import unittest

import readiness_guidance as guidance
from core_compatibility_rules import select_compatibility_rules

INSTALLED = "2026.8.3"
TARGET = "2026.10.4"
STATE_GROUP = ("2026.10", "State conditions")
AUTH_GROUP = ("2026.10", "Authentication")
RULE_ID = "core_2026_10_state_conditions_for"


def group(family, heading, status="insufficient_evidence"):
    return {
        "release_family": family,
        "heading": heading,
        "correlation_status": status,
    }


def dynamic_report(*rows):
    if not rows:
        rows = (group(*AUTH_GROUP), group(*STATE_GROUP))
    return {
        "scope": {"dynamic_correlation_performed": True,
                  "compatibility_assessed": False},
        "collector_status": {"overall": "ok"},
        "summary": {
            "official_crossed_group_count": len(rows),
            "insufficient_evidence_count": sum(
                x["correlation_status"] == "insufficient_evidence" for x in rows
            ),
        },
        "correlations": list(copy.deepcopy(rows)),
    }


def generic_report(*, affected=False):
    findings = ([{"file": "automations.yaml", "line": 17,
                  "reasons": ["attribute_with_for"]}] if affected else [])
    return {
        "schema_version": 1,
        "installed_version": INSTALLED,
        "target_version": TARGET,
        "status": "local_checks_completed",
        "selected_rule_count": 1,
        "rules": [{
            "rule_id": RULE_ID,
            "introduced_in": "2026.10",
            "official_group": "State conditions",
            "policy_applied_from": "2026.10.2",
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


def base_guidance_inputs():
    return {
        "core_update_pending": True,
        "update_readiness_available": True,
        "core_window_complete": True,
        "collector_error_count": 0,
        "configuration_check_state": "valid",
        "release_evidence_complete": True,
        "compatibility_coverage_usable": True,
        "dynamic_correlation_complete": True,
        "dynamic_correlation_insufficient_count": 2,
        "correlation_validation_usable": True,
        "deterministic_compatibility_required": False,
        "deterministic_compatibility_available": False,
        "deterministic_yaml_failure_count": 0,
        "relevant_unignored_repair_count": 0,
        "compatibility_review_required_count": 0,
        "compatibility_manual_review_count": 0,
        "generic_check_report": generic_report(),
        "generic_installed_version": INSTALLED,
        "generic_target_version": TARGET,
    }


class ExistingSafetyBaseline(unittest.TestCase):
    def test_live_shape_has_two_distinct_unassessed_groups(self):
        report = dynamic_report()
        self.assertEqual(report["summary"]["insufficient_evidence_count"], 2)
        self.assertEqual(
            {(r["release_family"], r["heading"]) for r in report["correlations"]},
            {AUTH_GROUP, STATE_GROUP},
        )

    def test_rule_is_registered_for_this_upgrade(self):
        selection = select_compatibility_rules(INSTALLED, TARGET)
        rules = selection["selected_rules"]
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["rule_id"], RULE_ID)
        self.assertEqual((rules[0]["introduced_in"], rules[0]["official_group"]),
                         STATE_GROUP)

    def test_existing_readiness_does_not_ignore_two_unresolved_groups(self):
        result = guidance.evaluate_core_update_guidance(**base_guidance_inputs())
        self.assertEqual(result["status"], guidance.STATE_INCOMPLETE)
        self.assertIn("dynamic_correlation_insufficient_evidence", result["reason_codes"])


class ReconciliationContract(unittest.TestCase):
    """These intentionally fail until the generic reconciliation is implemented."""

    def reconcile(self, dynamic=None, generic=None):
        return guidance.reconcile_dynamic_insufficient_evidence(
            dynamic_report() if dynamic is None else dynamic,
            generic_report() if generic is None else generic,
            installed_version=INSTALLED,
            target_version=TARGET,
        )

    @unittest.expectedFailure
    def test_only_exactly_matching_state_conditions_is_resolved(self):
        result = self.reconcile()
        self.assertEqual(result["status"], "reconciled")
        self.assertEqual(result["original_insufficient_count"], 2)
        self.assertEqual(result["remaining_insufficient_count"], 1)
        self.assertEqual(result["unresolved_groups"], [{
            "release_family": AUTH_GROUP[0], "heading": AUTH_GROUP[1]
        }])
        self.assertEqual(result["resolved_groups"], [{
            "release_family": STATE_GROUP[0], "heading": STATE_GROUP[1],
            "rule_id": RULE_ID,
            "outcome": "no_affected_usage_found",
        }])

    @unittest.expectedFailure
    def test_affected_local_configuration_is_not_hidden(self):
        result = self.reconcile(generic=generic_report(affected=True))
        self.assertEqual(result["remaining_insufficient_count"], 1)
        self.assertEqual(result["resolved_groups"][0]["outcome"], "review_required")

    @unittest.expectedFailure
    def test_same_heading_different_release_is_not_resolved(self):
        rows = [group(*AUTH_GROUP), group("2027.1", "State conditions")]
        result = self.reconcile(dynamic=dynamic_report(*rows))
        self.assertEqual(result["remaining_insufficient_count"], 2)
        self.assertEqual(result["resolved_groups"], [])

    @unittest.expectedFailure
    def test_similar_heading_is_not_treated_as_exact_match(self):
        rows = [group(*AUTH_GROUP), group("2026.10", "State condition")]
        result = self.reconcile(dynamic=dynamic_report(*rows))
        self.assertEqual(result["remaining_insufficient_count"], 2)
        self.assertEqual(result["resolved_groups"], [])

    @unittest.expectedFailure
    def test_unregistered_rule_id_cannot_resolve_official_group(self):
        fake = generic_report()
        fake["rules"][0]["rule_id"] = "unregistered_fake_check"
        result = self.reconcile(generic=fake)
        self.assertNotEqual(result["status"], "reconciled")
        self.assertEqual(result["remaining_insufficient_count"], 2)

    @unittest.expectedFailure
    def test_mismatched_upgrade_window_cannot_resolve(self):
        stale = generic_report()
        stale["target_version"] = "2026.10.1"
        result = self.reconcile(generic=stale)
        self.assertNotEqual(result["status"], "reconciled")
        self.assertEqual(result["remaining_insufficient_count"], 2)

    @unittest.expectedFailure
    def test_failed_local_check_cannot_resolve(self):
        incomplete = generic_report()
        incomplete["rules"][0]["read_failures"] = [{"file": "automations.yaml"}]
        result = self.reconcile(generic=incomplete)
        self.assertNotEqual(result["status"], "reconciled")
        self.assertEqual(result["remaining_insufficient_count"], 2)

    @unittest.expectedFailure
    def test_inconsistent_dynamic_count_fails_closed(self):
        inconsistent = dynamic_report()
        inconsistent["summary"]["insufficient_evidence_count"] = 0
        result = self.reconcile(dynamic=inconsistent)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["remaining_insufficient_count"], 2)

    @unittest.expectedFailure
    def test_duplicate_official_group_cannot_silently_clear_both(self):
        rows = [group(*AUTH_GROUP), group(*STATE_GROUP), group(*STATE_GROUP)]
        result = self.reconcile(dynamic=dynamic_report(*rows))
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["remaining_insufficient_count"], 3)

    @unittest.expectedFailure
    def test_guidance_remains_incomplete_when_authentication_is_unresolved(self):
        inputs = base_guidance_inputs()
        inputs["dynamic_correlation_report"] = dynamic_report()
        result = guidance.evaluate_core_update_guidance(**inputs)
        self.assertEqual(result["status"], guidance.STATE_INCOMPLETE)
        self.assertIn("dynamic_correlation_insufficient_evidence", result["reason_codes"])
        # The resolved group and remaining count must be exposed for review.
        self.assertEqual(result["dynamic_reconciliation"]["remaining_insufficient_count"], 1)

    @unittest.expectedFailure
    def test_fully_resolved_dynamic_uncertainty_only_with_matching_evidence(self):
        inputs = base_guidance_inputs()
        inputs["dynamic_correlation_insufficient_count"] = 1
        inputs["dynamic_correlation_report"] = dynamic_report(group(*STATE_GROUP))
        result = guidance.evaluate_core_update_guidance(**inputs)
        self.assertEqual(result["dynamic_reconciliation"]["remaining_insufficient_count"], 0)
        self.assertEqual(result["status"], guidance.STATE_CLEAR)


if __name__ == "__main__":
    unittest.main()
