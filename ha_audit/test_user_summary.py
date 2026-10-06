from user_summary import (
    build_user_summary,
)


SUMMARY_TEXT = """
==========================================================
HA AUDIT vtest - CURRENT RUN SUMMARY
==========================================================

OVERVIEW
----------------------------------------------------------
Home Assistant health:       NEEDS ATTENTION
Core update:                 NO KNOWN BLOCKERS FOUND
OS update:                   UPDATE AVAILABLE
Core evidence collection:    COMPLETE
Config check:                VALID
Core:                        2026.8.3 -> 2026.9.4
OS:                          18.2 -> 18.3

WHY THIS RESULT
----------------------------------------------------------
"""


UPDATE_READINESS = {
    "repairs": {
        "relevant_unignored_count": 0,
    },
}


COMPATIBILITY = {
    "coverage": {
        "ui_managed_prompt_content_inspected": False,
    },
    "summary": {
        "rule_count": 9,
        "review_required_count": 0,
        "manual_review_count": 0,
        "status_counts": {
            "no_local_match": 5,
            "local_match_no_active_yaml_usage_found": 1,
            "local_match_no_affected_custom_usage_found": 1,
            "local_match_no_affected_usage_found": 2,
        },
    },
    "results": [
        {
            "id": "core_2026_9_llm_tool_names",
            "area": "LLM APIs",
            "local_match": True,
        },
        {
            "id": "core_2026_9_vacuum_battery_level",
            "area": "Vacuum",
            "local_match": True,
        },
    ],
}


AVAILABILITY = {
    "summary": {
        "device_classification_counts": {
            "whole_device_unavailable_unlabelled": 15,
        },
        "entity_classification_counts": {
            "ungrouped_unavailable": 2,
        },
    },
}


def require(
    output,
    expected,
):
    if expected not in output:
        raise AssertionError(
            f"Expected text not found: {expected}"
        )


def forbid(
    output,
    unexpected,
):
    if unexpected in output:
        raise AssertionError(
            f"Unexpected text found: {unexpected}"
        )


def main():
    output = build_user_summary(
        summary_text=SUMMARY_TEXT,
        update_readiness=UPDATE_READINESS,
        compatibility=COMPATIBILITY,
        availability=AVAILABILITY,
        version="test",
    )

    require(
        output,
        "HA AUDIT vtest - USER SUMMARY",
    )

    require(
        output,
        "NO AUDIT-DETECTED REASON TO DELAY",
    )

    require(
        output,
        "No specific pre-update action",
    )

    require(
        output,
        "9 compatibility rules checked",
    )

    require(
        output,
        "4 locally relevant rule(s)",
    )

    require(
        output,
        "UI-managed LLM prompt content",
    )

    require(
        output,
        "15 device(s) currently have no healthy",
    )

    require(
        output,
        "separate from Core update",
    )

    require(
        output,
        "Rerun HA Audit",
    )

    require(
        output,
        "intentionally not repeated",
    )

    forbid(
        output,
        "OFFICIAL RELEASE EVIDENCE",
    )

    forbid(
        output,
        "DYNAMIC UPGRADE CORRELATION",
    )

    line_count = len(
        output.splitlines()
    )

    if line_count > 40:
        raise AssertionError(
            "User summary became too verbose: "
            f"{line_count} lines"
        )

    print("")
    print("=" * 62)
    print("HA AUDIT USER SUMMARY TEST")
    print("=" * 62)
    print(
        "Plain-English recommendation: PASS"
    )
    print(
        "Compatibility explanation:    PASS"
    )
    print(
        "Conditional uncertainty:      PASS"
    )
    print(
        "Health/update separation:     PASS"
    )
    print(
        "Post-update guidance:         PASS"
    )
    print(
        "Technical sections excluded: PASS"
    )
    print(
        "Maximum 40 lines:             PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
