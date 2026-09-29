from readiness_guidance import (
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
    evaluate_core_update_guidance,
)


def base_evidence():
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
        "deterministic_compatibility_required": True,
        "deterministic_compatibility_available": True,
        "deterministic_yaml_failure_count": 0,
        "relevant_unignored_repair_count": 0,
        "compatibility_review_required_count": 0,
        "compatibility_manual_review_count": 0,
    }


def expect_status(
    label,
    evidence,
    expected,
):
    result = evaluate_core_update_guidance(
        **evidence
    )

    if result["status"] != expected:
        raise AssertionError(
            f"{label}: "
            f"expected {expected!r}, "
            f"got {result['status']!r}"
        )

    return result


def test_complete_reference_path():
    result = expect_status(
        "complete reference path",
        base_evidence(),
        STATE_CLEAR,
    )

    if not result["assessment_complete"]:
        raise AssertionError(
            "complete reference path "
            "should be complete"
        )


def test_future_no_reference_path():
    evidence = base_evidence()

    evidence[
        "deterministic_compatibility_required"
    ] = False

    evidence[
        "deterministic_compatibility_available"
    ] = False

    result = expect_status(
        "future no-reference path",
        evidence,
        STATE_CLEAR,
    )

    if not result["assessment_complete"]:
        raise AssertionError(
            "future no-reference path "
            "should be complete"
        )


def test_review_path():
    evidence = base_evidence()

    evidence[
        "relevant_unignored_repair_count"
    ] = 1

    result = expect_status(
        "review path",
        evidence,
        STATE_REVIEW,
    )

    if (
        "relevant_unignored_repair"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "review path should identify "
            "the Repair reason"
        )


def test_incomplete_path():
    evidence = base_evidence()

    evidence[
        "release_evidence_complete"
    ] = False

    result = expect_status(
        "incomplete path",
        evidence,
        STATE_INCOMPLETE,
    )

    if result["assessment_complete"]:
        raise AssertionError(
            "incomplete path should not "
            "be complete"
        )

    if (
        "official_release_evidence_incomplete"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "incomplete path should identify "
            "release evidence"
        )


def test_no_update_path():
    evidence = base_evidence()

    evidence[
        "core_update_pending"
    ] = False

    result = expect_status(
        "no Core update path",
        evidence,
        STATE_NO_UPDATE,
    )

    if not result["assessment_complete"]:
        raise AssertionError(
            "no-update path should be complete"
        )


def main():
    tests = [
        test_complete_reference_path,
        test_future_no_reference_path,
        test_review_path,
        test_incomplete_path,
        test_no_update_path,
    ]

    for test in tests:
        test()

    print("")
    print("=" * 62)
    print(
        "HA AUDIT READINESS GUIDANCE TEST"
    )
    print("=" * 62)

    print(
        f"Scenarios tested:            "
        f"{len(tests)}"
    )

    print(
        "Complete reference path:     "
        "PASS"
    )

    print(
        "Future no-reference path:    "
        "PASS"
    )

    print(
        "Review-required path:        "
        "PASS"
    )

    print(
        "Incomplete evidence path:    "
        "PASS"
    )

    print(
        "No Core update path:         "
        "PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
