import builtins
import hashlib
import io
import json
import os
import runpy
from contextlib import redirect_stdout
from pathlib import Path


SUMMARY_PATH = Path(__file__).with_name("summary_report.py")

REPORTS = {
    "/config/audit_snapshot.json": {
        "generated_at": "2026-09-29T09:46:15+01:00",
        "system": {
            "timezone": "Europe/London",
            "core_version": "2026.8.3",
            "supervisor_version": "2026.09.2",
            "os_version": "18.2",
        },
        "updates": {
            "available_count": 2,
            "available": [
                {
                    "entity_id": "update.home_assistant_core_update",
                    "installed_version": "2026.8.3",
                    "latest_version": "2026.9.4",
                },
                {
                    "entity_id": "update.home_assistant_operating_system_update",
                    "installed_version": "18.2",
                    "latest_version": "18.3",
                },
            ],
        },
        "collector_status": {},
        "configuration_check": {
            "status": "ok",
            "data": {
                "result": "valid",
            },
        },
    },
    "/config/quality_audit.json": {},
    "/config/not_provided_reference_audit.json": {},
    "/config/recorder_health_audit.json": {},
    "/config/not_provided_history_audit.json": {},
    "/config/availability_audit.json": {},
    "/config/unavailable_history_audit.json": {},
    "/config/update_readiness_audit.json": {
        "scope": {
            "readiness_verdict_produced": False,
        },
        "updates": {
            "available_count": 2,
            "unavailable_count": 0,
            "in_progress_count": 0,
            "available": [
                {
                    "category": "core",
                    "entity_id": "update.home_assistant_core_update",
                    "installed_version": "2026.8.3",
                    "latest_version": "2026.9.4",
                },
                {
                    "category": "os",
                    "entity_id": "update.home_assistant_operating_system_update",
                    "installed_version": "18.2",
                    "latest_version": "18.3",
                },
            ],
        },
        "repairs": {
            "issue_count": 0,
            "unignored_count": 0,
            "ignored_count": 0,
            "relevant_to_pending_upgrade_count": 0,
            "relevant_unignored_count": 0,
            "relevant_ignored_count": 0,
            "already_crossed_count": 0,
            "beyond_pending_target_count": 0,
        },
        "core_upgrade_window": {
            "pending": True,
            "installed_version": "2026.8.3",
            "target_version": "2026.9.4",
        },
    },
    "/config/upgrade_impact_audit.json": {},
    "/config/upgrade_compatibility_audit.json": {
        "scope": {
            "rule_pack": "home_assistant_core_2026_9",
            "external_fetch_performed": False,
            "readiness_verdict_produced": False,
        },
        "core_upgrade_window": {
            "installed_version": "2026.8.3",
            "target_version": "2026.9.4",
        },
        "coverage": {
            "active_yaml_file_count": 12,
            "active_yaml_read_failures": [],
            "ui_managed_prompt_content_inspected": False,
        },
        "summary": {
            "rule_count": 1,
            "review_required_count": 0,
            "manual_review_count": 0,
            "status_counts": {
                "no_local_match": 1,
            },
        },
    },
    "/config/release_evidence_audit.json": {
        "scope": {
            "external_fetch_performed": True,
            "official_sources_only": True,
        },
        "applicability": {
            "applicable": True,
        },
        "release_range": {
            "status": "complete",
            "complete": True,
            "same_release_family": False,
        },
        "aggregate": {
            "release_families_requested": ["2026.9"],
            "crossed_release_families": ["2026.9"],
            "release_family_count": 1,
            "crossed_release_family_count": 1,
            "release_family_success_count": 1,
            "release_family_partial_count": 0,
            "release_family_failure_count": 0,
            "breaking_change_group_count": 1,
            "breaking_change_group_count_crossed_only": 1,
        },
        "collector_status": {
            "overall": "ok",
        },
        "releases": [
            {
                "collector_status": {
                    "release_notes_fetch": "ok",
                },
                "release_notes": {
                    "backward_incompatible_changes": {
                        "segmentation_status": "structured",
                    },
                },
            },
        ],
    },
    "/config/compatibility_coverage_audit.json": {
        "inputs": {
            "compatibility_rule_count_reported": 1,
        },
        "summary": {
            "coverage_status": "complete",
            "deterministic_reference_status": "complete",
            "official_crossed_group_count": 1,
            "registry_group_count": 1,
            "covered_group_count": 1,
            "partial_group_count": 0,
            "unmapped_group_count": 0,
            "no_reference_group_count": 0,
            "incomplete_reference_group_count": 0,
            "mapped_rule_count": 1,
            "present_linked_rule_count": 1,
            "missing_mapped_rule_count": 0,
            "unlinked_compatibility_rule_count": 0,
        },
        "release_coverage": [
            {
                "release_family": "2026.9",
                "covered_group_count": 1,
                "official_group_count": 1,
                "coverage_status": "covered",
                "reference_status": "complete",
            },
        ],
        "collector_status": {
            "overall": "ok",
        },
    },
    "/config/upgrade_correlation_audit.json": {
        "scope": {
            "evidence_model_version": 2,
            "compatibility_assessed": False,
            "readiness_verdict_produced": False,
            "deterministic_rule_outcomes_used_for_classification": False,
        },
        "summary": {
            "official_crossed_group_count": 1,
            "strong_local_evidence_count": 0,
            "local_surface_evidence_count": 0,
            "partial_local_evidence_count": 0,
            "no_local_evidence_count": 1,
            "insufficient_evidence_count": 0,
            "groups_with_any_local_evidence_count": 0,
        },
        "correlations": [
            {
                "heading": "Example change",
                "correlation_status": "no_local_evidence",
            },
        ],
        "collector_status": {
            "overall": "ok",
        },
    },
    "/config/correlation_validation_audit.json": {
        "scope": {
            "accuracy_score_produced": False,
            "compatibility_assessed": False,
            "readiness_verdict_produced": False,
        },
        "summary": {
            "official_groups_observed": 1,
            "official_groups_compared": 1,
            "groups_with_deterministic_reference": 1,
            "groups_without_deterministic_reference": 0,
            "groups_with_incomplete_deterministic_reference": 0,
            "validation_reference_status": "complete",
            "aligned_count": 1,
            "aligned_local_count": 0,
            "aligned_no_local_count": 1,
            "dynamic_gap_count": 0,
            "deterministic_gap_count": 0,
            "unresolved_count": 0,
            "precision_review_count": 0,
        },
        "precision_reviews": [],
        "collector_status": {
            "overall": "ok",
        },
    },
}

EXPECTED_SHA256 = "a7da1569c1c4b2c22198a953d8fbcd305072a0772a20372f0ab325773a8a9be4"
EXPECTED_LINE_COUNT = 257


class NonClosingStringIO(io.StringIO):
    def close(self):
        pass


def run_summary():
    real_open = builtins.open
    output_file = NonClosingStringIO()

    def fake_open(path, mode="r", *args, **kwargs):
        path = os.fspath(path)

        if (
            path == "/config/ha_audit_latest.txt"
            and "w" in mode
        ):
            output_file.seek(0)
            output_file.truncate(0)
            return output_file

        if path in REPORTS and "r" in mode:
            return io.StringIO(
                json.dumps(REPORTS[path])
            )

        return real_open(
            path,
            mode,
            *args,
            **kwargs,
        )

    previous_version = os.environ.get(
        "HA_AUDIT_VERSION"
    )
    os.environ["HA_AUDIT_VERSION"] = "test"
    builtins.open = fake_open

    try:
        with redirect_stdout(io.StringIO()):
            runpy.run_path(
                str(SUMMARY_PATH),
                run_name="__main__",
            )
    finally:
        builtins.open = real_open

        if previous_version is None:
            os.environ.pop(
                "HA_AUDIT_VERSION",
                None,
            )
        else:
            os.environ[
                "HA_AUDIT_VERSION"
            ] = previous_version

    return output_file.getvalue()


def main():
    summary = run_summary()
    digest = hashlib.sha256(
        summary.encode("utf-8")
    ).hexdigest()
    line_count = len(
        summary.splitlines()
    )

    required_text = (
        "OVERVIEW",
        "Home Assistant health:       NO PRIORITY ISSUES",
        "Core update:                 NO KNOWN BLOCKERS FOUND",
        "OS update:                   UPDATE AVAILABLE",
        "Core evidence collection:    COMPLETE",
        "OFFICIAL RELEASE EVIDENCE",
        "COMPATIBILITY COVERAGE",
        "DYNAMIC UPGRADE CORRELATION",
        "CORRELATION VALIDATION",
        "UPGRADE COMPATIBILITY",
        "NEXT ACTIONS",
        "DETAILED REPORTS",
    )

    missing = [
        text
        for text in required_text
        if text not in summary
    ]

    if missing:
        raise AssertionError(
            "Missing expected summary text: "
            + ", ".join(missing)
        )

    if line_count != EXPECTED_LINE_COUNT:
        raise AssertionError(
            "Summary line count changed: "
            f"expected {EXPECTED_LINE_COUNT}, "
            f"got {line_count}"
        )

    if digest != EXPECTED_SHA256:
        raise AssertionError(
            "Summary output changed: "
            f"expected SHA-256 {EXPECTED_SHA256}, "
            f"got {digest}"
        )

    print("")
    print("=" * 62)
    print("HA AUDIT SUMMARY OUTPUT REGRESSION TEST")
    print("=" * 62)
    print("Fixture:                     Core + OS update")
    print("Core evidence path:          COMPLETE")
    print("Expected summary lines:      PASS")
    print("Required sections:           PASS")
    print("Exact output fingerprint:    PASS")
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
