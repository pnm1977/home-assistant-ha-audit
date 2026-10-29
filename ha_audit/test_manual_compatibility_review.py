"""Step 134: fail-closed contract for explicit manual Core-change reviews.

These tests do not treat a chat conversation, absent Repair, or generic notes as
verified evidence. They document a narrowly scoped future opt-in input to the
existing readiness reconciler. A confirmation must be explicitly recorded by
the user, bound to an installed/target upgrade window and an exact official
change group. It is not a guarantee that a Core update is safe.

Run: python -m unittest -v test_manual_compatibility_review
"""

import copy
import inspect
import unittest

import readiness_guidance as guidance
from test_dynamic_correlation_reconciliation import (
    AUTH_GROUP,
    INSTALLED,
    TARGET,
    STATE_GROUP,
    dynamic_report,
    generic_report,
    group,
)

REVIEWED_AT = "2026-10-29T17:16:00+00:00"


def manual_report(*, installed=INSTALLED, target=TARGET):
    return {
        "schema_version": 1,
        "installed_version": installed,
        "target_version": target,
        "reviews": [{
            "release_family": AUTH_GROUP[0],
            "official_group": AUTH_GROUP[1],
            "outcome": "user_checked_no_issue",
            "source": "explicit_user_confirmation",
            "confirmed_by_user": True,
            "reviewed_at": REVIEWED_AT,
        }],
    }


def reconcile_with_optional_manual(report, *, dynamic=None, generic=True,
                                   installed=INSTALLED, target=TARGET):
    """Run existing guidance until a manual-review input is implemented.

    Baseline safety checks must pass before production code is modified; the
    three positive contract tests intentionally fail until this is supported.
    """
    kwargs = {
        "installed_version": installed,
        "target_version": target,
    }
    if "manual_review_report" in inspect.signature(
            guidance.reconcile_dynamic_insufficient_evidence).parameters:
        kwargs["manual_review_report"] = report
    return guidance.reconcile_dynamic_insufficient_evidence(
        dynamic if dynamic is not None else dynamic_report(),
        generic_report() if generic else None,
        **kwargs,
    )


class ManualReviewSafetyBaseline(unittest.TestCase):
    def check_auth_remains_unresolved(self, manual):
        outcome = reconcile_with_optional_manual(manual)
        self.assertEqual(outcome["remaining_insufficient_count"], 1)
        self.assertIn({"release_family": AUTH_GROUP[0], "heading": AUTH_GROUP[1]},
                      outcome["unresolved_groups"])

    def test_no_manual_confirmation_retains_auth_uncertainty(self):
        self.check_auth_remains_unresolved(None)

    def test_mismatched_target_does_not_resolve(self):
        self.check_auth_remains_unresolved(manual_report(target="2026.10.1"))

    def test_mismatched_installed_version_does_not_resolve(self):
        self.check_auth_remains_unresolved(manual_report(installed="2026.9.4"))

    def test_wrong_schema_does_not_resolve(self):
        candidate = manual_report()
        candidate["schema_version"] = 2
        self.check_auth_remains_unresolved(candidate)

    def test_missing_explicit_user_confirmation_does_not_resolve(self):
        candidate = manual_report()
        candidate["reviews"][0]["confirmed_by_user"] = False
        self.check_auth_remains_unresolved(candidate)

    def test_inferred_assistant_claim_does_not_resolve(self):
        candidate = manual_report()
        candidate["reviews"][0]["source"] = "assistant_inference"
        self.check_auth_remains_unresolved(candidate)

    def test_missing_review_date_does_not_resolve(self):
        candidate = manual_report()
        candidate["reviews"][0].pop("reviewed_at")
        self.check_auth_remains_unresolved(candidate)

    def test_wrong_official_group_does_not_resolve(self):
        candidate = manual_report()
        candidate["reviews"][0]["official_group"] = "Authentications"
        self.check_auth_remains_unresolved(candidate)

    def test_duplicate_review_cannot_clear_any_group(self):
        candidate = manual_report()
        candidate["reviews"].append(copy.deepcopy(candidate["reviews"][0]))
        self.check_auth_remains_unresolved(candidate)

    @unittest.expectedFailure
    def test_explicit_review_resolves_exact_auth_group_only(self):
        outcome = reconcile_with_optional_manual(manual_report(), generic=False)
        self.assertEqual(outcome["remaining_insufficient_count"], 1)
        self.assertEqual(outcome["unresolved_groups"], [
            {"release_family": STATE_GROUP[0], "heading": STATE_GROUP[1]}
        ])
        self.assertTrue(any(
            entry.get("heading") == "Authentication"
            and entry.get("source") == "explicit_user_confirmation"
            for entry in outcome["resolved_groups"]
        ))

    @unittest.expectedFailure
    def test_manual_auth_plus_automatic_state_resolves_both_with_provenance(self):
        outcome = reconcile_with_optional_manual(manual_report())
        self.assertEqual(outcome["remaining_insufficient_count"], 0)
        self.assertEqual(len(outcome["resolved_groups"]), 2)
        manual = [row for row in outcome["resolved_groups"]
                  if row.get("heading") == "Authentication"]
        self.assertEqual(len(manual), 1)
        self.assertEqual(manual[0]["source"], "explicit_user_confirmation")
        self.assertEqual(manual[0]["outcome"], "user_checked_no_issue")

    @unittest.expectedFailure
    def test_manual_review_does_not_depend_on_a_release_specific_rule_pack(self):
        future_installed, future_target = "2026.12.3", "2027.1.0"
        reviewed = manual_report(installed=future_installed, target=future_target)
        reviewed["reviews"][0]["release_family"] = "2027.1"
        reviewed["reviews"][0]["official_group"] = "Future change"
        future_dynamic = dynamic_report(
            group("2027.1", "Future change"), group("2027.1", "Other change")
        )
        result = reconcile_with_optional_manual(
            reviewed, dynamic=future_dynamic, generic=False,
            installed=future_installed, target=future_target,
        )
        self.assertEqual(result["remaining_insufficient_count"], 1)
        self.assertEqual(result["unresolved_groups"], [
            {"release_family": "2027.1", "heading": "Other change"}
        ])


if __name__ == "__main__":
    unittest.main()
