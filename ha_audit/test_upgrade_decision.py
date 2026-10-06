from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
)

from upgrade_decision import (
    RECOMMENDATION_DELAY,
    RECOMMENDATION_INCOMPLETE,
    RECOMMENDATION_NO_UPDATE,
    RECOMMENDATION_PROCEED,
    RECOMMENDATION_REVIEW,
    build_core_update_decision,
)


def assert_contains(
    values,
    expected,
):
    if not any(
        expected in value
        for value in values
    ):
        raise AssertionError(
            f"Expected text not found: {expected}"
        )


def test_clear_realistic_case():
    result = build_core_update_decision(
        core_guidance_status=STATE_CLEAR,
        config_result="valid",
        core_assessment_complete=True,
        relevant_unignored_repairs=0,
        compatibility_rule_count=9,
        compatibility_local_no_affected_count=4,
        compatibility_review_required_count=0,
        compatibility_manual_review_count=0,
        llm_local_match=True,
        ui_prompts_inspected=False,
        whole_device_unavailable_count=15,
        ungrouped_unavailable_count=2,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_PROCEED
    ):
        raise AssertionError(
            "Clear case should recommend PROCEED."
        )

    assert_contains(
        result["before_update"],
        "no reason to delay",
    )

    assert_contains(
        result["before_update"],
        "No general pre-update action",
    )

    assert_contains(
        result["why"],
        "9 Core compatibility rule",
    )

    assert_contains(
        result["why"],
        "4 locally relevant",
    )

    assert_contains(
        result["conditional_checks"],
        "custom AI prompts configured",
    )

    assert_contains(
        result["general_health"],
        "15 devices currently have no healthy",
    )

    assert_contains(
        result["after_update"],
        "Rerun HA Audit",
    )


def test_review_case():
    result = build_core_update_decision(
        core_guidance_status=STATE_REVIEW,
        config_result="valid",
        core_assessment_complete=True,
        relevant_unignored_repairs=1,
        compatibility_rule_count=9,
        compatibility_review_required_count=2,
        compatibility_manual_review_count=1,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_REVIEW
    ):
        raise AssertionError(
            "Review case should require review."
        )

    assert_contains(
        result["before_update"],
        "2 compatibility rule(s)",
    )

    assert_contains(
        result["before_update"],
        "1 unignored Repair",
    )


def test_incomplete_case():
    result = build_core_update_decision(
        core_guidance_status=STATE_INCOMPLETE,
        config_result="unknown",
        core_assessment_complete=False,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_INCOMPLETE
    ):
        raise AssertionError(
            "Incomplete case should remain "
            "incomplete."
        )

    assert_contains(
        result["before_update"],
        "incomplete",
    )


def test_blocker_case():
    result = build_core_update_decision(
        core_guidance_status=STATE_BLOCKER,
        config_result="valid",
        core_assessment_complete=True,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_DELAY
    ):
        raise AssertionError(
            "Blocker case should recommend delay."
        )

    assert_contains(
        result["before_update"],
        "blocker evidence",
    )


def test_no_update_case():
    result = build_core_update_decision(
        core_guidance_status=STATE_NO_UPDATE,
        config_result="valid",
        core_assessment_complete=True,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_NO_UPDATE
    ):
        raise AssertionError(
            "No-update case should be "
            "not applicable."
        )

    if result["after_update"]:
        raise AssertionError(
            "No-update case should not create "
            "post-update actions."
        )


def test_unexpected_state_is_not_clear():
    result = build_core_update_decision(
        core_guidance_status="UNKNOWN STATE",
        config_result="valid",
        core_assessment_complete=True,
    )

    if (
        result["recommendation"]
        != RECOMMENDATION_INCOMPLETE
    ):
        raise AssertionError(
            "Unexpected guidance state must not "
            "be treated as safe to proceed."
        )


def main():
    test_clear_realistic_case()
    test_review_case()
    test_incomplete_case()
    test_blocker_case()
    test_no_update_case()
    test_unexpected_state_is_not_clear()

    print("")
    print("=" * 62)
    print("HA AUDIT UPGRADE DECISION TEST")
    print("=" * 62)

    print(
        "Clear / proceed guidance:     PASS"
    )
    print(
        "Review guidance:             PASS"
    )
    print(
        "Incomplete guidance:         PASS"
    )
    print(
        "Blocker guidance:            PASS"
    )
    print(
        "No-update guidance:          PASS"
    )
    print(
        "Unexpected-state safety:     PASS"
    )
    print(
        "Conditional uncertainty:     PASS"
    )
    print(
        "General-health separation:   PASS"
    )
    print(
        "Post-update guidance:        PASS"
    )

    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
