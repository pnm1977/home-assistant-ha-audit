from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
)


def _count(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def render_overview(
    add,
    *,
    health_guidance_status,
    health_guidance_reasons,
    collector_error_count,
    missing_include_count,
    missing_entity_count,
    duplicate_automation_id_count,
    referenced_not_provided_count,
    whole_device_unavailable_count,
    ungrouped_unavailable_count,
    core_guidance_status,
    core_assessment_complete,
    os_update_pending,
    config_result,
    core_update_pending,
    core_installed_version,
    core_target_version,
    os_installed_version,
    os_target_version,
    system,
):
    """Render the concise human-facing HA Audit overview."""

    add("")
    add("OVERVIEW")
    add("-" * 58)
    add(
        f"Home Assistant health:       "
        f"{health_guidance_status}"
    )
    add(
        f"Core update:                 "
        f"{core_guidance_status}"
    )
    add(
        "OS update:                   "
        + (
            "UPDATE AVAILABLE"
            if os_update_pending
            else "NO OS UPDATE PENDING"
        )
    )

    if core_guidance_status == STATE_NO_UPDATE:
        core_evidence_label = "NOT APPLICABLE"
    else:
        core_evidence_label = (
            "COMPLETE"
            if core_assessment_complete
            else "INCOMPLETE"
        )

    add(
        f"Core evidence collection:    "
        f"{core_evidence_label}"
    )
    add(
        f"Config check:                "
        f"{str(config_result).upper()}"
    )

    if core_update_pending:
        add(
            f"Core:                        "
            f"{core_installed_version or 'unknown'}"
            " -> "
            f"{core_target_version or 'unknown'}"
        )
    else:
        add(
            f"Core:                        "
            f"{system.get('core_version') or 'unknown'}"
        )

    if os_update_pending:
        add(
            f"OS:                          "
            f"{os_installed_version or 'unknown'}"
            " -> "
            f"{os_target_version or 'unknown'}"
        )
    else:
        add(
            f"OS:                          "
            f"{system.get('os_version') or 'unknown'}"
        )

    add("")
    add("WHY THIS RESULT")
    add("-" * 58)
    add("Home Assistant health:")

    health_reasons = set(
        health_guidance_reasons
        if isinstance(health_guidance_reasons, list)
        else []
    )

    health_lines = []

    if "configuration_check_incomplete" in health_reasons:
        health_lines.append(
            "  Configuration check could not be completed."
        )

    if "audit_collector_error" in health_reasons:
        health_lines.append(
            f"  {_count(collector_error_count)} audit collector(s) "
            "reported an error."
        )

    if "configuration_invalid" in health_reasons:
        health_lines.append(
            "  Home Assistant configuration check is not valid."
        )

    if "missing_active_include" in health_reasons:
        health_lines.append(
            f"  {_count(missing_include_count)} active YAML include "
            "target(s) are missing."
        )

    if "missing_active_entity_reference" in health_reasons:
        health_lines.append(
            f"  {_count(missing_entity_count)} active YAML entity "
            "reference candidate(s) need review."
        )

    if "duplicate_automation_id" in health_reasons:
        health_lines.append(
            f"  {_count(duplicate_automation_id_count)} duplicate "
            "automation ID group(s) need review."
        )

    if "not_provided_referenced_in_yaml" in health_reasons:
        health_lines.append(
            f"  {_count(referenced_not_provided_count)} "
            "not-currently-provided entity/entities are still "
            "referenced in active YAML."
        )

    if "whole_device_unavailable" in health_reasons:
        health_lines.append(
            f"  {_count(whole_device_unavailable_count)} device(s) "
            "currently have no healthy state entities."
        )

    if "ungrouped_unavailable" in health_reasons:
        health_lines.append(
            f"  {_count(ungrouped_unavailable_count)} unavailable "
            "entity/entities are not attached to a device."
        )

    if not health_lines:
        health_lines.append(
            "  No priority health findings were identified by "
            "current checks."
        )

    for line in health_lines:
        add(line)

    add("")
    add("Core update:")

    if core_guidance_status == STATE_CLEAR:
        add(
            "  No known blockers were found in the evidence "
            "HA Audit inspected."
        )
        add(
            "  This is not a guarantee that the update cannot "
            "cause a problem."
        )
    elif core_guidance_status == STATE_REVIEW:
        add(
            "  One or more findings should be reviewed before "
            "installing the Core update."
        )
        add(
            "  See NEXT ACTIONS for the specific evidence."
        )
    elif core_guidance_status == STATE_INCOMPLETE:
        add(
            "  HA Audit could not complete every part of the "
            "Core update assessment."
        )
        add(
            "  Review the evidence sections and NEXT ACTIONS "
            "before updating."
        )
    elif core_guidance_status == STATE_BLOCKER:
        add(
            "  HA Audit found explicit blocker evidence for "
            "this Core update."
        )
        add(
            "  Review NEXT ACTIONS before updating."
        )
    else:
        add(
            "  No pending Home Assistant Core update was found."
        )
