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


LOG_PRIORITY_FINAL = {
    "status": "ok",
    "scope": {
        "priority_produced": True,
    },
    "summary": {
        "final_priority_counts": {
            "VERY HIGH": 0,
            "HIGH": 3,
            "MEDIUM": 5,
            "LOW": 10,
            "VERY LOW": 9,
        },
        "durable_recurrence_evidence_count": 0,
        "short_window_no_promotion_count": 12,
    },
    "families": [
        {
            "stable_fingerprint": "lfp_private_zigbee",
            "family_id": "zigbee_delivery",
            "title": "Zigbee / ZHA delivery failures",
            "occurrence_count": 615,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "HIGH",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_esphome",
            "family_id": "esphome",
            "title": "ESPHome device connectivity",
            "occurrence_count": 61,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "HIGH",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_hue",
            "family_id": "hue_sync",
            "title": "Hue Sync Box connectivity",
            "occurrence_count": 6,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "HIGH",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_missing",
            "family_id": "missing_targets",
            "title": (
                "Referenced entities or devices not "
                "currently available"
            ),
            "occurrence_count": 1,
            "local_action_path": "UNKNOWN",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "MEDIUM",
            "priority_changed": True,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "PROMOTION EVIDENCE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_shelly",
            "family_id": "shelly",
            "title": "Shelly integration data retrieval",
            "occurrence_count": 783,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "MEDIUM",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_apple",
            "family_id": "apple_tv",
            "title": "Apple TV connectivity",
            "occurrence_count": 303,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "MEDIUM",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_vaillant",
            "family_id": "mypyllant",
            "title": "myVAILLANT API / data retrieval",
            "occurrence_count": 15,
            "local_action_path": "LIMITED LOCAL CONTROL",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "MEDIUM",
            "priority_changed": False,
            "recurrence": {
                "class": "SHORT-WINDOW REPEAT",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
        {
            "stable_fingerprint": "lfp_private_robovac",
            "family_id": "robovac",
            "title": "RoboVac connectivity",
            "occurrence_count": 12,
            "local_action_path": "LOCAL INVESTIGATION",
            "recovery_evidence": "NOT OBSERVED",
            "fallback_evidence": "NOT OBSERVED",
            "final_priority": "MEDIUM",
            "priority_changed": False,
            "recurrence": {
                "class": "NOT ESTABLISHED",
            },
            "availability_correlation": {
                "effect": "NO CHANGE",
            },
        },
    ],
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



def check_structured_ai_evidence():
    """Same-run structured data improves the handoff without creating new diagnoses."""
    issue = {
        "family_id": "zigbee_delivery",
        "reader_summary": {
            "observed": "Home Assistant logged a Zigbee delivery failure.",
            "referenced_objects": "Evidence names: automation.hue_switch_bedroom.",
            "uncertainty": "The current impact has not been established.",
        },
        "ownership": "DEVICE / LOCAL NETWORK",
        "local_action_path": "LOCAL INVESTIGATION",
        "availability_context": {"power_expectation": "UNKNOWN"},
        "configuration_links": [
            {
                "link_type": "AUTOMATION_SOURCE",
                "entity_id": "automation.hue_switch_bedroom",
                "alias": "Hue Switch - Bedroom",
                "source": "automations.yaml",
                "line": 7222,
                "causal_link_established": False,
            },
            {
                "link_type": "SCRIPT_SOURCE",
                "entity_id": "script.dim_to_off_kitchen",
                "alias": "Dim to Off - Kitchen",
                "source": "scripts.yaml",
                "line": 732,
                "causal_link_established": False,
            },
        ],
    }
    structured = {
        "audit_version": "test",
        "generated_at": "2026-10-06T20:00:02+00:00",
        "system_issues": [issue],
    }

    def make_result(ai_evidence):
        return build_ai_handoff(
            summary_text=SUMMARY_TEXT,
            update_readiness=UPDATE_READINESS,
            compatibility=COMPATIBILITY,
            availability=AVAILABILITY,
            version="test",
            log_priority_final=LOG_PRIORITY_FINAL,
            ai_evidence=ai_evidence,
            generated_at="2026-10-06T20:00:00+00:00",
        )

    output = make_result(structured)
    require(output, "**Observed:** Home Assistant logged a Zigbee delivery failure.")
    require(output, "**Useful first check:** Check whether the device or integration is meant")
    require(output, "automations.yaml:7222")
    require(output, "scripts.yaml:732")
    require(output, "Where to look (not proven causes)")
    require(output, "The current impact has not been established.")
    forbid(output, "**Structured evidence note:** Matching same-run")

    wrong_version = dict(structured, audit_version="different")
    output = make_result(wrong_version)
    require(output, "Matching same-run AI evidence was not available")
    forbid(output, "automations.yaml:7222")

    stale = dict(structured, generated_at="2026-10-01T20:00:00+00:00")
    output = make_result(stale)
    require(output, "Matching same-run AI evidence was not available")
    forbid(output, "scripts.yaml:732")

    # Unavailable structured evidence must never prevent a regular handoff.
    nearby_previous = dict(structured, generated_at="2026-10-06T19:50:00+00:00")
    output = make_result(nearby_previous)
    require(output, "Matching same-run AI evidence was not available")
    forbid(output, "automations.yaml:7222")

    output = make_result({})
    require(output, "## System issues")
    require(output, "**HIGH — Zigbee / ZHA delivery failures**")
    forbid(output, "automations.yaml:7222")

    # Power labels are not permission to assume a device should be switched on.
    issue_offline = dict(issue, availability_context={"power_expectation": "EXPECTED_OFFLINE"})
    from ai_handoff import first_non_destructive_check
    check = first_non_destructive_check(issue_offline)
    if "Check only if" not in check:
        raise AssertionError("Expected-offline safety language missing")
    print("Same-run structured link and fallback tests: PASS")


def main():
    check_structured_ai_evidence()
    output = build_ai_handoff(
        summary_text=SUMMARY_TEXT,
        update_readiness=UPDATE_READINESS,
        compatibility=COMPATIBILITY,
        availability=AVAILABILITY,
        version="test",
        log_priority_final=LOG_PRIORITY_FINAL,
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
        "## System issues",
    )

    require(
        output,
        (
            "**Priority counts:** HIGH 3; MEDIUM 5; "
            "LOW 10; VERY LOW 9."
        ),
    )

    require(
        output,
        "**Durable recurrence (24h+):** 0.",
    )

    require(
        output,
        (
            "**Short-window repeats:** 12. These do not "
            "count as durable recurrence."
        ),
    )

    require(
        output,
        "**HIGH — Zigbee / ZHA delivery failures**",
    )

    require(
        output,
        "**HIGH — ESPHome device connectivity**",
    )

    require(
        output,
        "**HIGH — Hue Sync Box connectivity**",
    )

    require(
        output,
        (
            "**MEDIUM — Referenced entities or devices "
            "not currently available**"
        ),
    )

    require(
        output,
        "**MEDIUM — Shelly integration data retrieval**",
    )

    require(
        output,
        (
            "Priority raised by direct whole-device "
            "unavailability and Recorder evidence."
        ),
    )

    require(
        output,
        "Other MEDIUM findings omitted: 3.",
    )

    require(
        output,
        (
            "LOW / VERY LOW contextual findings omitted: "
            "19."
        ),
    )

    forbid(
        output,
        "Apple TV connectivity",
    )

    forbid(
        output,
        "lfp_private_",
    )

    forbid(
        output,
        "zigbee_delivery",
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
        "4. **System issues**",
    )

    require(
        output,
        "5. **General Home Assistant health**",
    )

    require(
        output,
        "6. **After updating**",
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
        "System issues handoff:         PASS"
    )
    print(
        "Top-five privacy boundary:     PASS"
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




def test_specific_handoff_render():
    from ai_handoff import first_non_destructive_check, render_structured_context
    issue = {
        "ownership": "USER / LOCAL CONFIGURATION",
        "availability_context": {"power_expectation": "UNKNOWN"},
        "reader_summary": {
            "observed": "TV & Events tried to change the LG TV input while the television was off.",
            "first_check": "Inspect the TV & Events trigger before considering a condition.",
            "uncertainty": "Current user-visible impact is not established.",
        },
        "configuration_links": [
            {"link_type": "AUTOMATION_SOURCE", "alias": "TV & Events", "source": "automations.yaml", "line": 2871}
        ],
        "recurrence_context": {
            "historical_verification_needed": True,
            "reported_log_timestamp_span_hours": 2.0,
        },
    }
    lines = []
    render_structured_context(lines, issue)
    rendered = "\n".join(lines)
    require(rendered, "TV & Events tried to change the LG TV input")
    require(rendered, "Inspect the TV & Events trigger")
    require(rendered, "automations.yaml:2871")
    require(rendered, "Timing caution:")
    require(rendered, "log_recurrence.json")
    offline = dict(issue, availability_context={"power_expectation": "EXPECTED_OFFLINE"})
    result = first_non_destructive_check(offline)
    if "Check only if" not in result:
        raise AssertionError("Specific guidance overrode explicit offline safeguard")
    print("Issue-specific handoff and recurrence transparency: PASS")

if __name__ == "__main__":
    main()
    test_specific_handoff_render()
