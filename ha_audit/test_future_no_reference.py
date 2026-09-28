import ast
import contextlib
import io
import json
import os
import shutil
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

COVERAGE_SCANNER = (
    BASE_DIR
    / "compatibility_coverage_scan.py"
)

VALIDATION_SCANNER = (
    BASE_DIR
    / "correlation_validation_scan.py"
)

SUMMARY_REPORT = (
    BASE_DIR
    / "summary_report.py"
)


# ------------------------------------------------------------
# Test helpers
# ------------------------------------------------------------

def write_json(
    path,
    value,
):
    path.write_text(
        json.dumps(
            value,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_json(path):
    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def expect_equal(
    label,
    actual,
    expected,
):
    if actual != expected:
        raise AssertionError(
            f"{label}: "
            f"expected {expected!r}, "
            f"got {actual!r}"
        )


def expect_contains(
    label,
    text,
    expected,
):
    if expected not in text:
        raise AssertionError(
            f"{label}: "
            f"expected text not found:\n"
            f"{expected}"
        )


def expect_not_contains(
    label,
    text,
    unexpected,
):
    if unexpected in text:
        raise AssertionError(
            f"{label}: "
            f"unexpected text found:\n"
            f"{unexpected}"
        )


def previous_release_family(
    release_family,
):
    year_text, month_text = (
        release_family.split(
            ".",
            1,
        )
    )

    year = int(
        year_text
    )

    month = int(
        month_text
    )

    month -= 1

    if month == 0:
        year -= 1
        month = 12

    return (
        f"{year}.{month}"
    )


def extract_registry_families(
    source_text,
):
    """
    Read RULE_GROUP_REGISTRY from the production coverage
    scanner without importing or executing that scanner.

    This lets the test automatically choose a release family
    that genuinely has no deterministic registry.
    """

    tree = ast.parse(
        source_text
    )

    for node in tree.body:

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        for target in node.targets:

            if (
                isinstance(
                    target,
                    ast.Name,
                )
                and target.id
                == "RULE_GROUP_REGISTRY"
            ):

                value = ast.literal_eval(
                    node.value
                )

                if isinstance(
                    value,
                    dict,
                ):
                    return set(
                        str(key)
                        for key
                        in value
                    )

    raise RuntimeError(
        "Could not find RULE_GROUP_REGISTRY "
        "in compatibility_coverage_scan.py"
    )


def choose_unregistered_family(
    registry_families,
):
    """
    Start with 2026.10 because that is the first future-family
    scenario this architecture was designed to handle.

    If a deterministic registry is later added for 2026.10,
    automatically move forward until an unregistered family is
    found. This keeps the test useful in future.
    """

    year = 2026
    month = 10

    for _ in range(
        120
    ):

        release_family = (
            f"{year}.{month}"
        )

        if (
            release_family
            not in registry_families
        ):
            return release_family

        month += 1

        if month == 13:
            year += 1
            month = 1

    raise RuntimeError(
        "Could not find an unregistered "
        "release family for the test."
    )


def run_script_isolated(
    script_path,
    temp_dir,
):
    """
    Execute a production HA Audit script using an in-memory
    copy whose /config paths point to the temporary test
    directory.

    The production file itself is never edited.

    The real /config directory is never used by this test.
    """

    source = script_path.read_text(
        encoding="utf-8",
    )

    temp_prefix = (
        temp_dir.as_posix().rstrip("/")
        + "/"
    )

    redirected_source = source.replace(
        '"/config/',
        f'"{temp_prefix}',
    )

    redirected_source = (
        redirected_source.replace(
            "'/config/",
            f"'{temp_prefix}",
        )
    )

    if (
        '"/config/'
        in redirected_source
        or "'/config/"
        in redirected_source
    ):
        raise RuntimeError(
            f"Safety check failed for "
            f"{script_path.name}: "
            "a hard-coded /config path remains "
            "after redirection."
        )

    namespace = {
        "__name__":
            "__main__",

        "__file__":
            str(
                script_path
            ),
    }

    previous_version = (
        os.environ.get(
            "HA_AUDIT_VERSION"
        )
    )

    os.environ[
        "HA_AUDIT_VERSION"
    ] = (
        "future-no-reference-test"
    )

    output = io.StringIO()

    try:

        with contextlib.redirect_stdout(
            output
        ):

            exec(
                compile(
                    redirected_source,
                    str(
                        script_path
                    ),
                    "exec",
                ),
                namespace,
                namespace,
            )

    finally:

        if previous_version is None:

            os.environ.pop(
                "HA_AUDIT_VERSION",
                None,
            )

        else:

            os.environ[
                "HA_AUDIT_VERSION"
            ] = previous_version

    return output.getvalue()


# ------------------------------------------------------------
# Synthetic future-release fixtures
# ------------------------------------------------------------

def build_release_evidence(
    release_family,
):
    release_url = (
        "https://example.invalid/"
        f"synthetic-home-assistant-"
        f"{release_family}"
    )

    groups = [
        {
            "release_family":
                release_family,

            "heading":
                "Synthetic Change A",

            "crossed_from_installed":
                True,

            "release_notes_url":
                release_url,
        },

        {
            "release_family":
                release_family,

            "heading":
                "Synthetic Change B",

            "crossed_from_installed":
                True,

            "release_notes_url":
                release_url,
        },

        {
            "release_family":
                release_family,

            "heading":
                "Synthetic Change C",

            "crossed_from_installed":
                True,

            "release_notes_url":
                release_url,
        },
    ]

    return {
        "audit_version":
            "future-no-reference-test",

        "scope": {
            "external_fetch_performed":
                True,

            "official_sources_only":
                True,
        },

        "applicability": {
            "applicable":
                True,
        },

        "release_range": {
            "status":
                "crosses_release_families",

            "complete":
                True,

            "same_release_family":
                False,
        },

        "aggregate": {
            "release_families_requested": [
                release_family,
            ],

            "crossed_release_families": [
                release_family,
            ],

            "release_family_count":
                1,

            "crossed_release_family_count":
                1,

            "release_family_success_count":
                1,

            "release_family_partial_count":
                0,

            "release_family_failure_count":
                0,

            "breaking_change_group_count":
                3,

            "breaking_change_group_count_crossed_only":
                3,

            "breaking_change_groups":
                groups,
        },

        "collector_status": {
            "overall":
                "ok",
        },

        "releases": [
            {
                "collector_status": {
                    "release_notes_fetch":
                        "ok",
                },

                "release_notes": {
                    "backward_incompatible_changes": {
                        "segmentation_status":
                            "structured",
                    },
                },
            },
        ],
    }


def build_upgrade_compatibility(
    installed_version,
    target_version,
):
    return {
        "audit_version":
            "future-no-reference-test",

        "scope": {
            "rule_pack":
                None,

            "external_fetch_performed":
                False,

            "readiness_verdict_produced":
                False,
        },

        "core_upgrade_window": {
            "pending":
                True,

            "installed_version":
                installed_version,

            "target_version":
                target_version,
        },

        "coverage": {
            "active_yaml_file_count":
                0,

            "active_yaml_read_failures":
                [],

            "ui_managed_prompt_content_inspected":
                False,
        },

        "summary": {
            "rule_count":
                0,

            "review_required_count":
                0,

            "manual_review_count":
                0,

            "status_counts":
                {},
        },

        "results":
            [],

        "collector_status": {
            "overall":
                "ok",
        },
    }


def build_dynamic_correlation(
    release_family,
):
    release_url = (
        "https://example.invalid/"
        f"synthetic-home-assistant-"
        f"{release_family}"
    )

    return {
        "audit_version":
            "future-no-reference-test",

        "scope": {
            "evidence_model_version":
                2,

            "compatibility_assessed":
                False,

            "readiness_verdict_produced":
                False,

            "deterministic_rule_outcomes_used_for_classification":
                False,
        },

        "summary": {
            "official_crossed_group_count":
                3,

            "strong_local_evidence_count":
                1,

            "local_surface_evidence_count":
                1,

            "partial_local_evidence_count":
                0,

            "no_local_evidence_count":
                1,

            "insufficient_evidence_count":
                0,

            "groups_with_any_local_evidence_count":
                2,
        },

        "correlations": [
            {
                "release_family":
                    release_family,

                "heading":
                    "Synthetic Change A",

                "release_notes_url":
                    release_url,

                "correlation_status":
                    "strong_local_evidence",

                "interpretation":
                    "Synthetic specific evidence.",
            },

            {
                "release_family":
                    release_family,

                "heading":
                    "Synthetic Change B",

                "release_notes_url":
                    release_url,

                "correlation_status":
                    "local_surface_evidence",

                "interpretation":
                    "Synthetic local-surface evidence.",
            },

            {
                "release_family":
                    release_family,

                "heading":
                    "Synthetic Change C",

                "release_notes_url":
                    release_url,

                "correlation_status":
                    "no_local_evidence",

                "interpretation":
                    "Synthetic no-local evidence.",
            },
        ],

        "collector_status": {
            "overall":
                "ok",
        },
    }


def build_audit_snapshot(
    installed_version,
):
    return {
        "generated_at":
            "2026-10-01T10:00:00+00:00",

        "system": {
            "core_version":
                installed_version,

            "supervisor_version":
                "test",

            "os_version":
                "test",

            "timezone":
                "Europe/London",
        },

        "inventory": {
            "state_entities":
                100,
        },

        "entities": {
            "unavailable": {
                "count":
                    0,
            },

            "unknown": {
                "count":
                    0,
            },

            "not_currently_provided": {
                "count":
                    0,
            },
        },

        "changes_since_previous":
            {},

        "updates": {
            "available_count":
                1,
        },

        "collector_status":
            {},

        "configuration_check": {
            "status":
                "ok",

            "data": {
                "result":
                    "valid",
            },
        },
    }


def build_quality_audit():
    return {
        "configuration_tree": {
            "active_yaml_count":
                1,

            "missing_include_count":
                0,

            "orphan_candidate_count":
                0,
        },

        "automations":
            {},

        "scripts":
            {},

        "entity_references": {
            "missing_count":
                0,
        },
    }


def build_reference_audit():
    return {
        "summary": {
            "referenced_in_active_yaml":
                0,

            "template_no_active_yaml_reference":
                0,
        },
    }


def build_update_readiness(
    installed_version,
    target_version,
):
    return {
        "scope": {
            "readiness_verdict_produced":
                False,
        },

        "updates": {
            "available_count":
                1,

            "unavailable_count":
                0,

            "in_progress_count":
                0,

            "available": [
                {
                    "category":
                        "core",

                    "title":
                        "Home Assistant Core",

                    "installed_version":
                        installed_version,

                    "latest_version":
                        target_version,
                },
            ],
        },

        "repairs": {
            "issue_count":
                0,

            "unignored_count":
                0,

            "ignored_count":
                0,

            "relevant_to_pending_upgrade_count":
                0,

            "relevant_unignored_count":
                0,

            "relevant_ignored_count":
                0,

            "already_crossed_count":
                0,

            "beyond_pending_target_count":
                0,
        },

        "core_upgrade_window": {
            "pending":
                True,

            "installed_version":
                installed_version,

            "target_version":
                target_version,
        },
    }


# ------------------------------------------------------------
# Assertions
# ------------------------------------------------------------

def check_coverage(
    report,
):
    summary = report.get(
        "summary",
        {},
    )

    collector = report.get(
        "collector_status",
        {},
    )

    expect_equal(
        "coverage status",
        summary.get(
            "coverage_status"
        ),
        "no_reference",
    )

    expect_equal(
        "deterministic reference status",
        summary.get(
            "deterministic_reference_status"
        ),
        "not_available",
    )

    expect_equal(
        "official group count",
        summary.get(
            "official_crossed_group_count"
        ),
        3,
    )

    expect_equal(
        "registry-backed group count",
        summary.get(
            "registry_group_count"
        ),
        0,
    )

    expect_equal(
        "covered group count",
        summary.get(
            "covered_group_count"
        ),
        0,
    )

    expect_equal(
        "no-reference group count",
        summary.get(
            "no_reference_group_count"
        ),
        3,
    )

    expect_equal(
        "incomplete reference group count",
        summary.get(
            "incomplete_reference_group_count"
        ),
        0,
    )

    expect_equal(
        "coverage collector health",
        collector.get(
            "overall"
        ),
        "ok",
    )

    expect_equal(
        "compatibility input requirement",
        collector.get(
            "upgrade_compatibility_input"
        ),
        "not_required",
    )

    expect_equal(
        "rule discovery requirement",
        collector.get(
            "rule_id_discovery"
        ),
        "not_required",
    )


def check_validation(
    report,
):
    summary = report.get(
        "summary",
        {},
    )

    collector = report.get(
        "collector_status",
        {},
    )

    expect_equal(
        "validation reference status",
        summary.get(
            "validation_reference_status"
        ),
        "no_reference",
    )

    expect_equal(
        "official groups observed",
        summary.get(
            "official_groups_observed"
        ),
        3,
    )

    expect_equal(
        "official groups compared",
        summary.get(
            "official_groups_compared"
        ),
        0,
    )

    expect_equal(
        "groups with deterministic reference",
        summary.get(
            "groups_with_deterministic_reference"
        ),
        0,
    )

    expect_equal(
        "groups without deterministic reference",
        summary.get(
            "groups_without_deterministic_reference"
        ),
        3,
    )

    expect_equal(
        "incomplete deterministic references",
        summary.get(
            "groups_with_incomplete_deterministic_reference"
        ),
        0,
    )

    expect_equal(
        "no-reference relationships",
        summary.get(
            "no_reference_count"
        ),
        3,
    )

    expect_equal(
        "validation collector health",
        collector.get(
            "overall"
        ),
        "ok",
    )

    expect_equal(
        "validation reference availability",
        collector.get(
            "deterministic_reference_availability"
        ),
        "no_reference",
    )


def check_summary(
    text,
):
    required = [
        "Deterministic reference:     NOT AVAILABLE",
        "Compatibility coverage:      NO REFERENCE",
        "Dynamic correlation:         COMPLETE",
        "Correlation validation:      NO REFERENCE",
        "Official release evidence:    COMPLETE",
        "Readiness verdict:           NOT PRODUCED",
        "Reference status:             NOT AVAILABLE",
        "Coverage/reference state:     NO REFERENCE",
        "Collector health:             OK",
        "Reference validation:          NO REFERENCE",
        (
            "[i] No deterministic reference is available "
            "for this Core upgrade window."
        ),
        (
            "This is a supported dynamic-only state, "
            "not a scanner failure."
        ),
    ]

    for expected in required:

        expect_contains(
            "summary output",
            text,
            expected,
        )

    forbidden = [
        (
            "[!] Deterministic reference coverage is "
            "no reference."
        ),
        (
            "[!] Correlation reference validation is "
            "no reference."
        ),
    ]

    for unexpected in forbidden:

        expect_not_contains(
            "summary output",
            text,
            unexpected,
        )


# ------------------------------------------------------------
# Main test
# ------------------------------------------------------------

def main():

    for path in (
        COVERAGE_SCANNER,
        VALIDATION_SCANNER,
        SUMMARY_REPORT,
    ):

        if not path.is_file():
            raise FileNotFoundError(
                f"Required production file not found: "
                f"{path}"
            )

    coverage_source = (
        COVERAGE_SCANNER.read_text(
            encoding="utf-8",
        )
    )

    registry_families = (
        extract_registry_families(
            coverage_source
        )
    )

    release_family = (
        choose_unregistered_family(
            registry_families
        )
    )

    installed_family = (
        previous_release_family(
            release_family
        )
    )

    installed_version = (
        f"{installed_family}.4"
    )

    target_version = (
        f"{release_family}.2"
    )

    temp_path = Path(
        tempfile.mkdtemp(
            prefix=(
                "ha_audit_"
                "future_no_reference_"
            )
        )
    )

    scanner_output = {}

    try:

        write_json(
            temp_path
            / "release_evidence_audit.json",
            build_release_evidence(
                release_family
            ),
        )

        write_json(
            temp_path
            / "upgrade_compatibility_audit.json",
            build_upgrade_compatibility(
                installed_version,
                target_version,
            ),
        )

        write_json(
            temp_path
            / "upgrade_correlation_audit.json",
            build_dynamic_correlation(
                release_family
            ),
        )

        write_json(
            temp_path
            / "audit_snapshot.json",
            build_audit_snapshot(
                installed_version
            ),
        )

        write_json(
            temp_path
            / "quality_audit.json",
            build_quality_audit(),
        )

        write_json(
            temp_path
            / "not_provided_reference_audit.json",
            build_reference_audit(),
        )

        write_json(
            temp_path
            / "update_readiness_audit.json",
            build_update_readiness(
                installed_version,
                target_version,
            ),
        )

        scanner_output[
            "coverage"
        ] = run_script_isolated(
            COVERAGE_SCANNER,
            temp_path,
        )

        coverage_report = load_json(
            temp_path
            / "compatibility_coverage_audit.json"
        )

        check_coverage(
            coverage_report
        )

        scanner_output[
            "validation"
        ] = run_script_isolated(
            VALIDATION_SCANNER,
            temp_path,
        )

        validation_report = load_json(
            temp_path
            / "correlation_validation_audit.json"
        )

        check_validation(
            validation_report
        )

        scanner_output[
            "summary"
        ] = run_script_isolated(
            SUMMARY_REPORT,
            temp_path,
        )

        summary_text = (
            temp_path
            / "ha_audit_latest.txt"
        ).read_text(
            encoding="utf-8",
        )

        check_summary(
            summary_text
        )

    except Exception:

        print("")
        print(
            "FUTURE NO-REFERENCE TEST: FAILED"
        )

        print(
            "Temporary test data has been preserved at:"
        )

        print(
            f"  {temp_path}"
        )

        print("")

        for (
            name,
            output,
        ) in scanner_output.items():

            print(
                f"--- {name} output ---"
            )

            print(
                output
            )

        raise

    else:

        print("")
        print(
            "=" * 62
        )

        print(
            "HA AUDIT FUTURE NO-REFERENCE TEST"
        )

        print(
            "=" * 62
        )

        print(
            f"Synthetic release family:     "
            f"{release_family}"
        )

        print(
            f"Upgrade window:               "
            f"{installed_version} -> "
            f"{target_version}"
        )

        print("")

        print(
            "Coverage/reference state:     "
            "NO REFERENCE"
        )

        print(
            "Deterministic reference:      "
            "NOT AVAILABLE"
        )

        print(
            "Coverage collector health:    "
            "OK"
        )

        print("")

        print(
            "Dynamic correlation:          "
            "COMPLETE"
        )

        print(
            "Correlation validation:       "
            "NO REFERENCE"
        )

        print(
            "Validation collector health:  "
            "OK"
        )

        print("")

        print(
            "Readiness verdict:            "
            "NOT PRODUCED"
        )

        print("")

        print(
            "Production files modified:    "
            "NO"
        )

        print(
            "Real /config used:            "
            "NO"
        )

        print("")

        print(
            "RESULT: PASS"
        )

        print(
            "=" * 62
        )

        shutil.rmtree(
            temp_path
        )


if __name__ == "__main__":
    main()
