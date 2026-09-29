from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
)


def render_overview(
    add,
    *,
    health_guidance_status,
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

    if core_guidance_status == STATE_CLEAR:
        add(
            "No known blockers were found in the evidence "
            "HA Audit inspected."
        )
        add(
            "This is not a guarantee that the update cannot "
            "cause a problem."
        )
    elif core_guidance_status == STATE_REVIEW:
        add(
            "One or more findings should be reviewed before "
            "installing the Core update."
        )
        add(
            "See NEXT ACTIONS for the specific evidence."
        )
    elif core_guidance_status == STATE_INCOMPLETE:
        add(
            "HA Audit could not complete every part of the "
            "Core update assessment."
        )
        add(
            "Review the evidence sections and NEXT ACTIONS "
            "before updating."
        )
    elif core_guidance_status == STATE_BLOCKER:
        add(
            "HA Audit found explicit blocker evidence for "
            "this Core update."
        )
        add(
            "Review NEXT ACTIONS before updating."
        )
    else:
        add(
            "No pending Home Assistant Core update was found."
        )

    add(
        "Core update guidance is conservative evidence-based "
        "guidance, not a safe-to-update guarantee."
    )
