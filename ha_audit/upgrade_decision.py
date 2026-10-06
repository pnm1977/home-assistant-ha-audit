from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
)


RECOMMENDATION_NO_UPDATE = (
    "NO CORE UPDATE PENDING"
)

RECOMMENDATION_PROCEED = (
    "PROCEED"
)

RECOMMENDATION_REVIEW = (
    "REVIEW BEFORE UPDATING"
)

RECOMMENDATION_INCOMPLETE = (
    "ASSESSMENT INCOMPLETE"
)

RECOMMENDATION_DELAY = (
    "DELAY - BLOCKER EVIDENCE FOUND"
)


def _normalise_count(value):
    try:
        return max(
            0,
            int(value),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def build_core_update_decision(
    *,
    core_guidance_status,
    config_result,
    core_assessment_complete,
    relevant_unignored_repairs=0,
    compatibility_rule_count=0,
    compatibility_local_no_affected_count=0,
    compatibility_review_required_count=0,
    compatibility_manual_review_count=0,
    llm_local_match=False,
    ui_prompts_inspected=False,
    whole_device_unavailable_count=0,
    ungrouped_unavailable_count=0,
):
    """
    Build plain-English decision-support evidence.

    This helper does not create a new compatibility verdict.

    The existing readiness-guidance state remains authoritative.
    This function explains that result in a more useful form.
    """

    relevant_unignored_repairs = (
        _normalise_count(
            relevant_unignored_repairs
        )
    )

    compatibility_rule_count = (
        _normalise_count(
            compatibility_rule_count
        )
    )

    compatibility_local_no_affected_count = (
        _normalise_count(
            compatibility_local_no_affected_count
        )
    )

    compatibility_review_required_count = (
        _normalise_count(
            compatibility_review_required_count
        )
    )

    compatibility_manual_review_count = (
        _normalise_count(
            compatibility_manual_review_count
        )
    )

    whole_device_unavailable_count = (
        _normalise_count(
            whole_device_unavailable_count
        )
    )

    ungrouped_unavailable_count = (
        _normalise_count(
            ungrouped_unavailable_count
        )
    )

    config_label = str(
        config_result or "unknown"
    ).upper()

    before_update = []
    why = []
    conditional_checks = []
    general_health = []
    after_update = []

    if core_guidance_status == STATE_NO_UPDATE:
        recommendation = (
            RECOMMENDATION_NO_UPDATE
        )

        before_update.append(
            "No Core update decision is required."
        )

    elif core_guidance_status == STATE_BLOCKER:
        recommendation = (
            RECOMMENDATION_DELAY
        )

        before_update.append(
            "Review the blocker evidence before "
            "installing the Core update."
        )

    elif core_guidance_status == STATE_INCOMPLETE:
        recommendation = (
            RECOMMENDATION_INCOMPLETE
        )

        before_update.append(
            "Resolve or review the incomplete "
            "assessment evidence before relying on "
            "HA Audit for the update decision."
        )

    elif core_guidance_status == STATE_REVIEW:
        recommendation = (
            RECOMMENDATION_REVIEW
        )

        if (
            compatibility_review_required_count
        ):
            before_update.append(
                (
                    f"{compatibility_review_required_count} "
                    "compatibility rule(s) require review."
                )
            )

        if compatibility_manual_review_count:
            before_update.append(
                (
                    f"{compatibility_manual_review_count} "
                    "compatibility rule(s) require "
                    "manual review."
                )
            )

        if relevant_unignored_repairs:
            before_update.append(
                (
                    f"{relevant_unignored_repairs} "
                    "unignored Repair issue(s) are "
                    "relevant to the Core upgrade."
                )
            )

        if not before_update:
            before_update.append(
                "Review the update-related findings "
                "identified by HA Audit before updating."
            )

    elif (
        core_guidance_status == STATE_CLEAR
        and core_assessment_complete
    ):
        recommendation = (
            RECOMMENDATION_PROCEED
        )

        before_update.append(
            "HA Audit found no reason to delay "
            "this Core update."
        )

        before_update.append(
            "No general pre-update action is required."
        )

    else:
        recommendation = (
            RECOMMENDATION_INCOMPLETE
        )

        before_update.append(
            "HA Audit could not interpret the Core "
            "update assessment as complete. Review "
            "the evidence before updating."
        )

    if config_label == "VALID":
        why.append(
            "Home Assistant configuration validation "
            "passed."
        )
    else:
        why.append(
            (
                "Home Assistant configuration status: "
                f"{config_label}."
            )
        )

    why.append(
        (
            "Required Core evidence collection "
            + (
                "completed."
                if core_assessment_complete
                else "did not complete."
            )
        )
    )

    if relevant_unignored_repairs:
        why.append(
            (
                f"{relevant_unignored_repairs} "
                "unignored Repair issue(s) are relevant "
                "to the Core upgrade."
            )
        )
    else:
        why.append(
            "No unignored Repairs were identified as "
            "relevant to the Core upgrade."
        )

    if compatibility_rule_count:
        why.append(
            (
                f"{compatibility_rule_count} "
                "Core compatibility rule(s) were "
                "assessed."
            )
        )

    if compatibility_local_no_affected_count:
        why.append(
            (
                f"{compatibility_local_no_affected_count} "
                "locally relevant compatibility "
                "rule(s) were checked with no affected "
                "use detected."
            )
        )

    if compatibility_review_required_count:
        why.append(
            (
                f"{compatibility_review_required_count} "
                "compatibility rule(s) require review."
            )
        )
    else:
        why.append(
            "No compatibility rule currently requires "
            "review."
        )

    if compatibility_manual_review_count:
        why.append(
            (
                f"{compatibility_manual_review_count} "
                "compatibility rule(s) require manual "
                "review."
            )
        )
    else:
        why.append(
            "No compatibility rule currently requires "
            "manual review."
        )

    if (
        llm_local_match
        and not ui_prompts_inspected
    ):
        conditional_checks.append(
            "If you use custom AI prompts configured "
            "in the Home Assistant UI that directly "
            "name Home Assistant tools, review those "
            "prompts before updating. HA Audit cannot "
            "inspect their contents."
        )

    if whole_device_unavailable_count:
        if whole_device_unavailable_count == 1:
            general_health.append(
                "1 device currently has no healthy "
                "state entities."
            )
        else:
            general_health.append(
                (
                    f"{whole_device_unavailable_count} "
                    "devices currently have no healthy "
                    "state entities."
                )
            )

    if ungrouped_unavailable_count:
        if ungrouped_unavailable_count == 1:
            general_health.append(
                "1 unavailable entity is not attached "
                "to a device."
            )
        else:
            general_health.append(
                (
                    f"{ungrouped_unavailable_count} "
                    "unavailable entities are not "
                    "attached to a device."
                )
            )

    if core_guidance_status != STATE_NO_UPDATE:
        after_update.extend(
            [
                (
                    "Rerun HA Audit after the Core "
                    "update."
                ),
                (
                    "Check for new configuration "
                    "errors or Home Assistant Repairs."
                ),
                (
                    "Review newly unavailable or "
                    "recovered entities compared with "
                    "the pre-update audit."
                ),
                (
                    "Review any new compatibility "
                    "finding produced for the updated "
                    "installation."
                ),
            ]
        )

    return {
        "recommendation": recommendation,
        "before_update": before_update,
        "why": why,
        "conditional_checks": conditional_checks,
        "general_health": general_health,
        "general_health_note": (
            "These findings are not currently linked "
            "to the Core update."
        ),
        "after_update": after_update,
        "caution": (
            "This is evidence-based guidance, not a "
            "guarantee that the update cannot cause "
            "a problem."
        ),
    }
