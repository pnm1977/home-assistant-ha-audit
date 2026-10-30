"""Regression tests for the presentation-only Core readiness evidence trace.

Run from the repository root:
    python3 ha_audit/test_readiness_trace.py
"""

from copy import deepcopy
from unittest import TestCase, main
from unittest.mock import patch

from readiness_guidance import STATE_NO_UPDATE
from readiness_trace import render_readiness_trace
import summary_upgrade


AUTOMATIC = {
    "release_family": "2026.10",
    "heading": "State conditions",
    "rule_id": "core_2026_10_state_conditions",
    "outcome": "no_affected_usage_found",
}
MANUAL = {
    "release_family": "2026.10",
    "heading": "Authentication",
    "source": "explicit_user_confirmation",
    "outcome": "user_checked_no_issue",
    "reviewed_at": "2026-10-29T12:30:00+00:00",
}
UNRESOLVED = {
    "release_family": "2026.10",
    "heading": "Another change",
}


def guidance(*, resolved=None, unresolved=None, reasons=None, status=None,
             reconciliation_status="reconciled"):
    resolved = deepcopy(resolved if resolved is not None else [AUTOMATIC, MANUAL])
    unresolved = deepcopy(unresolved if unresolved is not None else [])
    return {
        "status": status or "NO KNOWN BLOCKERS FOUND",
        "reason_codes": deepcopy(reasons if reasons is not None else []),
        "dynamic_reconciliation": {
            "status": reconciliation_status,
            "original_insufficient_count": len(resolved) + len(unresolved),
            "remaining_insufficient_count": len(unresolved),
            "resolved_groups": resolved,
            "unresolved_groups": unresolved,
        },
    }


def render(context):
    output = []
    render_readiness_trace(output.append, context)
    return "\n".join(output)


class ReadinessTraceTests(TestCase):
    def test_mixed_auto_and_manual_are_identified_separately(self):
        report = render({"core_guidance": guidance()})
        self.assertIn("Reconciled local checks:     1", report)
        self.assertIn("Accepted user confirmations: 1", report)
        self.assertIn("Still unresolved groups:     0", report)
        self.assertIn("State conditions | rule", report)
        self.assertIn("Authentication | confirmed", report)
        self.assertIn("NOT machine-verified", report)
        self.assertIn("Neither is a guarantee", report)

    def test_unresolved_groups_are_preserved(self):
        report = render({"core_guidance": guidance(unresolved=[UNRESOLVED])})
        self.assertIn("Initially uncertain groups:  3", report)
        self.assertIn("Still unresolved groups:     1", report)
        self.assertIn("Another change", report)

    def test_machine_review_required_not_claimed_as_clear(self):
        row = deepcopy(AUTOMATIC)
        row["outcome"] = "review_required"
        report = render({"core_guidance": guidance(resolved=[row])})
        self.assertIn("review required", report)
        self.assertNotIn("Accepted user confirmations: 1", report)

    def test_missing_core_guidance_cannot_be_read_as_clear(self):
        report = render({})
        self.assertIn("UNAVAILABLE; do not infer clearance", report)

    def test_bad_guidance_type_cannot_be_read_as_clear(self):
        report = render({"core_guidance": "PROCEED"})
        self.assertIn("UNAVAILABLE; do not infer clearance", report)

    def test_no_update_does_not_attempt_reconciliation(self):
        report = render({"core_guidance": {"status": STATE_NO_UPDATE}})
        self.assertIn("No Core update is pending", report)
        self.assertNotIn("Still unresolved groups", report)

    def test_missing_reconciliation_is_uncertain(self):
        report = render({"core_guidance": {
            "status": "NO KNOWN BLOCKERS FOUND", "reason_codes": []
        }})
        self.assertIn("UNAVAILABLE / INCONSISTENT", report)
        self.assertIn("do not assume", report.lower())

    def test_unusable_reconciliation_status_is_uncertain(self):
        data = guidance()
        data["dynamic_reconciliation"]["status"] = "incomplete"
        self.assertIn("UNAVAILABLE / INCONSISTENT", render({"core_guidance": data}))

    def test_count_mismatch_is_uncertain(self):
        data = guidance()
        data["dynamic_reconciliation"]["original_insufficient_count"] = 1
        self.assertIn("UNAVAILABLE / INCONSISTENT", render({"core_guidance": data}))

    def test_duplicate_exact_groups_are_uncertain(self):
        data = guidance(unresolved=[{"release_family": AUTOMATIC["release_family"],
                                     "heading": AUTOMATIC["heading"]}])
        self.assertIn("UNAVAILABLE / INCONSISTENT", render({"core_guidance": data}))

    def test_unverified_manual_confirmation_is_rejected(self):
        data = guidance(resolved=[{**MANUAL, "source": "model_guess"}])
        report = render({"core_guidance": data})
        self.assertIn("UNAVAILABLE / INCONSISTENT", report)
        self.assertNotIn("Accepted user confirmations: 1", report)

    def test_manual_timestamp_is_required(self):
        data = guidance(resolved=[{**MANUAL, "reviewed_at": ""}])
        self.assertIn("UNAVAILABLE / INCONSISTENT", render({"core_guidance": data}))

    def test_invalid_reason_codes_are_not_printed_as_evidence(self):
        data = guidance(reasons=["valid_reason", 123])
        self.assertIn("unavailable or inconsistent", render({"core_guidance": data}))

    def test_presentation_does_not_mutate_guidance(self):
        data = guidance(unresolved=[UNRESOLVED], reasons=["not_clear"])
        before = deepcopy(data)
        render({"core_guidance": data})
        self.assertEqual(data, before)

    def test_summary_upgrade_includes_trace_after_existing_sections(self):
        existing = (
            "render_update_readiness",
            "render_official_release_evidence",
            "render_compatibility_coverage",
            "render_dynamic_upgrade_correlation",
            "render_correlation_validation",
            "render_upgrade_compatibility",
        )
        from contextlib import ExitStack
        output = []
        with ExitStack() as stack:
            for name in existing:
                stack.enter_context(patch.object(
                    summary_upgrade,
                    name,
                    side_effect=lambda add, _ctx, n=name: add(n),
                ))
            summary_upgrade.render_upgrade_sections(
                output.append, {"core_guidance": guidance()}
            )
        self.assertEqual(output[:6], list(existing))
        self.assertIn("CORE READINESS EVIDENCE TRACE", output)
        self.assertGreater(output.index("CORE READINESS EVIDENCE TRACE"), 5)


if __name__ == "__main__":
    main()
