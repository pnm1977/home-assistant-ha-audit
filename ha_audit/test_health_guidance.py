from health_guidance import (
    STATE_ATTENTION,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    evaluate_health_guidance,
)


def base_evidence():
    return {
        "configuration_check_state": "valid",
        "collector_error_count": 0,
        "missing_include_count": 0,
        "missing_entity_count": 0,
        "duplicate_automation_id_count": 0,
        "referenced_not_provided_count": 0,
        "whole_device_unavailable_count": 0,
        "ungrouped_unavailable_count": 0,
    }


def expect_status(
    label,
    evidence,
    expected,
):
    result = evaluate_health_guidance(
        **evidence
    )

    if result["status"] != expected:
        raise AssertionError(
            f"{label}: "
            f"expected {expected!r}, "
            f"got {result['status']!r}"
        )

    return result


def test_clear_path():
    result = expect_status(
        "clear path",
        base_evidence(),
        STATE_CLEAR,
    )

    if not result["assessment_complete"]:
        raise AssertionError(
            "clear path should be complete"
        )


def test_whole_device_attention_path():
    evidence = base_evidence()

    evidence[
        "whole_device_unavailable_count"
    ] = 1

    result = expect_status(
        "whole-device attention path",
        evidence,
        STATE_ATTENTION,
    )

    if (
        "whole_device_unavailable"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "whole-device path should identify "
            "the availability reason"
        )


def test_configuration_attention_path():
    evidence = base_evidence()

    evidence[
        "configuration_check_state"
    ] = "invalid"

    result = expect_status(
        "configuration attention path",
        evidence,
        STATE_ATTENTION,
    )

    if (
        "configuration_invalid"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "invalid configuration should "
            "be identified"
        )


def test_collector_incomplete_path():
    evidence = base_evidence()

    evidence[
        "collector_error_count"
    ] = 1

    result = expect_status(
        "collector incomplete path",
        evidence,
        STATE_INCOMPLETE,
    )

    if result["assessment_complete"]:
        raise AssertionError(
            "collector failure should make "
            "the assessment incomplete"
        )

    if (
        "audit_collector_error"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "collector failure should be "
            "identified"
        )


def test_unknown_config_incomplete_path():
    evidence = base_evidence()

    evidence[
        "configuration_check_state"
    ] = "unknown"

    result = expect_status(
        "unknown config path",
        evidence,
        STATE_INCOMPLETE,
    )

    if (
        "configuration_check_incomplete"
        not in result["reason_codes"]
    ):
        raise AssertionError(
            "unknown configuration check "
            "should be identified"
        )


def main():
    tests = [
        test_clear_path,
        test_whole_device_attention_path,
        test_configuration_attention_path,
        test_collector_incomplete_path,
        test_unknown_config_incomplete_path,
    ]

    for test in tests:
        test()

    print("")
    print("=" * 62)
    print(
        "HA AUDIT HEALTH GUIDANCE TEST"
    )
    print("=" * 62)

    print(
        f"Scenarios tested:            "
        f"{len(tests)}"
    )

    print(
        "Clear path:                  "
        "PASS"
    )

    print(
        "Whole-device attention:      "
        "PASS"
    )

    print(
        "Configuration attention:     "
        "PASS"
    )

    print(
        "Collector incomplete:        "
        "PASS"
    )

    print(
        "Unknown config incomplete:   "
        "PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
