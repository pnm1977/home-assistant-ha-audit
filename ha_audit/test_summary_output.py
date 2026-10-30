import builtins
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
    """Protect the current summary contract with a conservative fixture.

    The historical fixture deliberately omits the newer completed generic
    check report and dynamic-reconciliation scope marker. These are evidence
    gaps, not a proven clear update. The summary must fail closed and report
    the reason rather than presenting the old NO KNOWN BLOCKERS headline.

    Check section order and high-value text rather than a whole-file hash:
    adding an explanatory evidence section must not silently break CI.
    """
    summary = run_summary()
    lines = summary.splitlines()

    required_sections = (
        "OVERVIEW",
        "WHY THIS RESULT",
        "SYSTEM",
        "UPDATE READINESS",
        "OFFICIAL RELEASE EVIDENCE",
        "COMPATIBILITY COVERAGE",
        "DYNAMIC UPGRADE CORRELATION",
        "CORRELATION VALIDATION",
        "UPGRADE COMPATIBILITY",
        "CORE READINESS EVIDENCE TRACE",
        "CONFIGURATION",
        "NEXT ACTIONS",
        "DETAILED REPORTS",
    )

    section_positions = []
    for heading in required_sections:
        matches = [i for i, line in enumerate(lines) if line.strip() == heading]
        if len(matches) != 1:
            raise AssertionError(
                f"Expected exactly one {heading!r} heading; found {len(matches)}"
            )
        section_positions.append(matches[0])

    if section_positions != sorted(section_positions):
        raise AssertionError("Summary sections are out of their expected order")

    overview = "\n".join(
        lines[section_positions[0] : section_positions[1]]
    )
    required_overview = (
        "Home Assistant health:       NO PRIORITY ISSUES",
        "Core update:                 ASSESSMENT INCOMPLETE",
        "OS update:                   UPDATE AVAILABLE",
        "Core evidence collection:    INCOMPLETE",
        "Config check:                VALID",
    )
    for expected in required_overview:
        if expected not in overview:
            raise AssertionError(
                f"Missing expected overview text: {expected!r}\n"
                f"Actual overview:\n{overview}"
            )

    if "NO KNOWN BLOCKERS FOUND" in overview or "PROCEED" in overview:
        raise AssertionError("Incomplete fixture was incorrectly presented as cleared")

    trace = "\n".join(
        lines[section_positions[9] : section_positions[10]]
    )
    required_trace = (
        "Core guidance:               ASSESSMENT INCOMPLETE",
        "dynamic_reconciliation_incomplete",
        "generic_compatibility_evidence_incomplete",
        "Uncertainty trace:           UNAVAILABLE / INCONSISTENT",
        "Do not assume that missing trace data means zero unresolved groups.",
    )
    for expected in required_trace:
        if expected not in trace:
            raise AssertionError(
                f"Missing required fail-closed trace text: {expected!r}\n"
                f"Actual trace:\n{trace}"
            )

    required_text = (
        "No priority health findings were identified by current checks.",
        "Core: 2026.8.3 -> 2026.9.4",
        "OS: 18.2 -> 18.3",
    )
    for expected in required_text:
        if expected not in summary:
            raise AssertionError(f"Missing required summary text: {expected!r}")

    print("HA AUDIT SUMMARY OUTPUT REGRESSION TEST")
    print("Fixture:                     Incomplete legacy evidence")
    print("Required section order:      PASS")
    print("Core readiness fail-closed:  PASS")
    print("Evidence trace limitations:  PASS")
    print("RESULT: PASS")


if __name__ == "__main__":
    main()
