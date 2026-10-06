from ai_handoff import (
    build_ai_handoff,
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
Home Assistant health:
  15 devices currently have no healthy state entities.

Core update:
  No known blockers were found.

SYSTEM
----------------------------------------------------------
Core:                       2026.8.3
Supervisor:                 2026.09.3
OS:                         18.2
Config check:               VALID
Updates available:          2
Collector errors:           0

UPDATE READINESS
----------------------------------------------------------
Pending updates:             2
Core: 2026.8.3 -> 2026.9.4
OS: 18.2 -> 18.3
Relevant + unignored:        0

OFFICIAL RELEASE EVIDENCE
----------------------------------------------------------
Upgrade window:              2026.8.3 -> 2026.9.4
Evidence collection:         COMPLETE

COMPATIBILITY COVERAGE
----------------------------------------------------------
Official crossed groups:     8

DYNAMIC UPGRADE CORRELATION
----------------------------------------------------------
Official change groups:      8

CORRELATION VALIDATION
----------------------------------------------------------
Official groups compared:    8

UPGRADE COMPATIBILITY
----------------------------------------------------------
Core rule pack:              2026.9
Rules assessed:              9
No local match:              5
Local match, no affected use: 4
Review required:             0
Manual review:               0

CONFIGURATION
----------------------------------------------------------
Active YAML files:           146
Missing active includes:     0

ENTITY HEALTH
----------------------------------------------------------
Entities:                    2800

AVAILABILITY CONTEXT
----------------------------------------------------------
Whole device unavailable:    15
Ungrouped unavailable:       2

UNAVAILABLE HISTORY CONTEXT
----------------------------------------------------------
History query failures:      0

REVIEW
----------------------------------------------------------
Not provided + active YAML:  0

NOT-PROVIDED HISTORY SAFETY
----------------------------------------------------------
History query failures:      0

NEXT ACTIONS
----------------------------------------------------------
[i] Compatibility rules were assessed.

DETAILED REPORTS
----------------------------------------------------------
Detailed files omitted.
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
            "id": "core_2026_9_flexit_bacnet",
            "area": "Flexit Nordic (BACnet)",
            "change": (
                "Deprecated fireplace mode switch removed."
            ),
            "local_match": False,
            "status": "no_local_match",
            "note": (
                "No local integration-domain evidence "
                "was found."
            ),
        },
        {
            "id": "core_2026_9_llm_tool_names",
            "area": "LLM APIs",
            "change": (
                "LLM tool names are prefixed with the "
                "integration domain."
            ),
            "local_match": True,
            "status": (
                "local_match_no_active_yaml_usage_found"
            ),
            "evidence": {
                "ui_managed_prompt_content_inspected": False,
            },
            "note": (
                "The LLM component is loaded, but no "
                "known unprefixed tool names were found "
                "in active YAML."
            ),
        },
        {
            "id": (
                "core_2026_9_"
                "persistent_notification_updated"
            ),
            "area": "Persistent Notification",
            "change": (
                "Existing notification updates now "
                "report updated instead of added."
            ),
            "local_match": True,
            "status": (
                "local_match_no_affected_usage_found"
            ),
            "evidence": {},
            "note": (
                "No active YAML trigger depending on "
                "the old behaviour was found."
            ),
        },
        {
            "id": "core_2026_9_update_admin_context",
            "area": "Update",
            "change": (
                "Some update actions now require "
                "administrator context."
            ),
            "local_match": True,
            "status": (
                "local_match_no_affected_usage_found"
            ),
            "evidence": {},
            "note": (
                "No affected Update action was found "
                "in script scope."
            ),
        },
        {
            "id": (
                "core_2026_9_vacuum_battery_level"
            ),
            "area": "Vacuum",
            "change": (
                "The deprecated battery_level property "
                "was removed."
            ),
            "local_match": True,
            "status": (
                "local_match_no_affected_custom_usage_found"
            ),
            "evidence": {},
            "note": (
                "A custom vacuum integration is active, "
                "but no battery_level Python name "
                "reference was found in its source."
            ),
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
    output = build_ai_handoff(
        summary_text=SUMMARY_TEXT,
        update_readiness=UPDATE_READINESS,
        compatibility=COMPATIBILITY,
        availability=AVAILABILITY,
        version="test",
        generated_at=(
            "2026-10-06T20:00:00+00:00"
        ),
    )

    require(
        output,
        "# HA Audit AI / LLM Handoff",
    )

    require(
        output,
        "## Core update decision support",
    )

    require(
        output,
        "**Recommendation: PROCEED**",
    )

    require(
        output,
        "HA Audit found no reason to delay",
    )

    require(
        output,
        "Conditional checks / uncertainty",
    )

    require(
        output,
        "custom AI prompts configured",
    )

    require(
        output,
        "## Locally relevant Core compatibility findings",
    )

    require(
        output,
        "### LLM APIs",
    )

    require(
        output,
        "### Persistent Notification",
    )

    require(
        output,
        "### Update",
    )

    require(
        output,
        "### Vacuum",
    )

    require(
        output,
        "No affected active YAML usage detected",
    )

    require(
        output,
        "No affected custom integration usage detected",
    )

    require(
        output,
        "UI-managed prompt/config-entry content was not inspected",
    )

    forbid(
        output,
        "### Flexit Nordic (BACnet)",
    )

    require(
        output,
        "1. **Core update recommendation**",
    )

    require(
        output,
        "2. **Required before updating**",
    )

    require(
        output,
        "3. **Conditional checks / uncertainty**",
    )

    require(
        output,
        "4. **General Home Assistant health**",
    )

    require(
        output,
        "5. **After updating**",
    )

    require(
        output,
        "## HA Audit evidence",
    )

    require(
        output,
        "OFFICIAL RELEASE EVIDENCE",
    )

    require(
        output,
        "UPGRADE COMPATIBILITY",
    )

    require(
        output,
        "NEXT ACTIONS",
    )

    forbid(
        output,
        "\nCOMPATIBILITY COVERAGE\n",
    )

    forbid(
        output,
        "\nDYNAMIC UPGRADE CORRELATION\n",
    )

    forbid(
        output,
        "\nCORRELATION VALIDATION\n",
    )

    forbid(
        output,
        "\nENTITY HEALTH\n",
    )

    forbid(
        output,
        "\nDETAILED REPORTS\n",
    )

    print("")
    print("=" * 62)
    print("HA AUDIT AI HANDOFF TEST")
    print("=" * 62)
    print(
        "Decision support:             PASS"
    )
    print(
        "Proceed guidance:             PASS"
    )
    print(
        "Local compatibility detail:   PASS"
    )
    print(
        "Non-local rules excluded:     PASS"
    )
    print(
        "Conditional uncertainty:      PASS"
    )
    print(
        "Requested analysis order:     PASS"
    )
    print(
        "Selected evidence retained:   PASS"
    )
    print(
        "Verbose sections excluded:    PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
