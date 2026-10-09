import json
import os

from upgrade_decision import (
    build_core_update_decision,
)


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

SUMMARY_FILE = "/config/ha_audit_latest.txt"
UPDATE_READINESS_FILE = (
    "/config/update_readiness_audit.json"
)
UPGRADE_COMPATIBILITY_FILE = (
    "/config/upgrade_compatibility_audit.json"
)
AVAILABILITY_FILE = (
    "/config/availability_audit.json"
)
LOG_PRIORITY_FINAL_FILE = (
    "/config/log_priority_final.json"
)


NO_AFFECTED_STATUSES = (
    "local_match_no_active_yaml_usage_found",
    "local_match_no_affected_custom_usage_found",
    "local_match_no_affected_usage_found",
    "local_match_core_integrations_only",
)


def load_json_optional(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)
    except Exception:
        return {}


def load_text(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return handle.read()


def extract_overview(summary_text):
    values = {}
    in_overview = False

    for raw_line in summary_text.splitlines():
        line = raw_line.strip()

        if line == "OVERVIEW":
            in_overview = True
            continue

        if not in_overview:
            continue

        if line == "WHY THIS RESULT":
            break

        if not line or set(line) == {"-"}:
            continue

        if ":" not in line:
            continue

        label, value = line.split(
            ":",
            1,
        )

        values[
            label.strip()
        ] = value.strip()

    return values


def count_local_no_affected(
    compatibility,
):
    summary = compatibility.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        return 0

    status_counts = summary.get(
        "status_counts",
        {},
    )

    if not isinstance(
        status_counts,
        dict,
    ):
        return 0

    return sum(
        int(
            status_counts.get(
                status,
                0,
            )
            or 0
        )
        for status in NO_AFFECTED_STATUSES
    )


def has_local_llm_match(
    compatibility,
):
    results = compatibility.get(
        "results",
        [],
    )

    if not isinstance(
        results,
        list,
    ):
        return False

    for item in results:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if not item.get(
            "local_match",
            False,
        ):
            continue

        rule_id = str(
            item.get(
                "id",
                "",
            )
        ).lower()

        area = str(
            item.get(
                "area",
                "",
            )
        ).lower()

        if (
            "llm" in rule_id
            or "llm" in area
        ):
            return True

    return False


PRIORITY_RANK = {
    "VERY LOW": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "VERY HIGH": 4,
}

ATTENTION_LIMIT = 5


def safe_int(value):
    try:
        return int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def log_priority_available(
    report,
):
    if not isinstance(
        report,
        dict,
    ):
        return False

    scope = report.get(
        "scope",
        {},
    )

    if not isinstance(
        scope,
        dict,
    ):
        return False

    return (
        report.get(
            "status"
        )
        == "ok"
        and scope.get(
            "priority_produced"
        )
        is True
        and isinstance(
            report.get(
                "families"
            ),
            list,
        )
    )


def issue_action_label(
    item,
):
    priority = str(
        item.get(
            "final_priority",
            "",
        )
    ).upper()

    action_path = str(
        item.get(
            "local_action_path",
            "",
        )
    ).upper()

    priority_changed = bool(
        item.get(
            "priority_changed",
            False,
        )
    )

    availability = item.get(
        "availability_correlation",
        {},
    )

    if not isinstance(
        availability,
        dict,
    ):
        availability = {}

    availability_promoted = (
        availability.get(
            "effect"
        )
        == "PROMOTION EVIDENCE"
    )

    if (
        priority
        in (
            "HIGH",
            "MEDIUM",
        )
        and action_path
        == "CLEAR LOCAL ACTION PATH"
    ):
        return "FIX / REVIEW"

    if (
        priority == "HIGH"
        and action_path
        == "LOCAL INVESTIGATION"
    ):
        return "INVESTIGATE"

    if (
        priority_changed
        or availability_promoted
    ):
        return "REVIEW"

    if (
        priority == "MEDIUM"
        and action_path
        == "LOCAL INVESTIGATION"
    ):
        return "INVESTIGATE"

    if priority == "HIGH":
        if action_path in (
            "LIMITED LOCAL CONTROL",
            "PLATFORM / UPSTREAM",
        ):
            return "MONITOR"

        return "REVIEW"

    if priority == "MEDIUM":
        return "MONITOR"

    return "CONTEXT"


def issue_note(
    item,
):
    availability = item.get(
        "availability_correlation",
        {},
    )

    recurrence = item.get(
        "recurrence",
        {},
    )

    if not isinstance(
        availability,
        dict,
    ):
        availability = {}

    if not isinstance(
        recurrence,
        dict,
    ):
        recurrence = {}

    if (
        availability.get(
            "effect"
        )
        == "PROMOTION EVIDENCE"
    ):
        return (
            "Priority raised by direct whole-device "
            "unavailability and Recorder evidence."
        )

    recurrence_class = recurrence.get(
        "class"
    )

    if recurrence_class == "RECURRING 24H+":
        return (
            "Independent new activity has been "
            "observed across at least 24 hours."
        )

    recovery = item.get(
        "recovery_evidence"
    )

    if recovery == "OBSERVED":
        return (
            "Recovery was also observed; monitor "
            "before escalating."
        )

    fallback = item.get(
        "fallback_evidence"
    )

    if fallback == "OBSERVED":
        return (
            "Fallback was observed; local impact "
            "may be reduced."
        )

    action_path = item.get(
        "local_action_path"
    )

    if recurrence_class == "SHORT-WINDOW REPEAT":
        if action_path == "LOCAL INVESTIGATION":
            return (
                "Short-window repeat only; investigate "
                "locally if it is still happening."
            )

        if action_path in (
            "LIMITED LOCAL CONTROL",
            "PLATFORM / UPSTREAM",
        ):
            return (
                "Short-window repeat only; local "
                "control is limited."
            )

        return (
            "Short-window repeat only; durable "
            "recurrence is not yet established."
        )

    if action_path == "LOCAL INVESTIGATION":
        return (
            "Recurrence is not established; investigate "
            "if the behaviour is still occurring."
        )

    if action_path in (
        "LIMITED LOCAL CONTROL",
        "PLATFORM / UPSTREAM",
    ):
        return (
            "Local control is limited; monitor for "
            "continued impact."
        )

    return (
        "Review the detailed evidence if this finding "
        "remains current."
    )


def attention_sort_key(
    item,
):
    priority = str(
        item.get(
            "final_priority",
            "",
        )
    ).upper()

    availability = item.get(
        "availability_correlation",
        {},
    )

    if not isinstance(
        availability,
        dict,
    ):
        availability = {}

    promoted = bool(
        item.get(
            "priority_changed",
            False,
        )
    )

    availability_promoted = (
        availability.get(
            "effect"
        )
        == "PROMOTION EVIDENCE"
    )

    action_rank = {
        "FIX / REVIEW": 4,
        "INVESTIGATE": 3,
        "REVIEW": 2,
        "MONITOR": 1,
        "CONTEXT": 0,
    }.get(
        issue_action_label(
            item
        ),
        0,
    )

    return (
        -PRIORITY_RANK.get(
            priority,
            -1,
        ),
        -int(
            promoted
        ),
        -int(
            availability_promoted
        ),
        -action_rank,
        -safe_int(
            item.get(
                "occurrence_count",
                0,
            )
        ),
        str(
            item.get(
                "title",
                "",
            )
        ).lower(),
    )


def render_system_issues(
    add,
    report,
):
    add("")
    add("SYSTEM ISSUES")
    add("-" * 58)

    if not log_priority_available(
        report
    ):
        add(
            "System Log prioritisation:    UNAVAILABLE"
        )
        add(
            "  Final priority evidence was not produced "
            "for this run."
        )
        return

    families = [
        item
        for item in report.get(
            "families",
            [],
        )
        if isinstance(
            item,
            dict,
        )
    ]

    counts = {
        "VERY HIGH": 0,
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "VERY LOW": 0,
    }

    for item in families:
        priority = str(
            item.get(
                "final_priority",
                "",
            )
        ).upper()

        if priority in counts:
            counts[
                priority
            ] += 1

    summary = report.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        summary = {}

    durable_count = safe_int(
        summary.get(
            "durable_recurrence_evidence_count",
            0,
        )
    )

    short_count = safe_int(
        summary.get(
            "short_window_no_promotion_count",
            0,
        )
    )

    add(
        "Priority: "
        f"HIGH {counts['HIGH']} | "
        f"MEDIUM {counts['MEDIUM']} | "
        f"LOW {counts['LOW']} | "
        f"VERY LOW {counts['VERY LOW']}"
    )

    add(
        f"Durable recurrence (24h+):   "
        f"{durable_count}"
    )

    add(
        f"Short-window repeats:        "
        f"{short_count}"
    )

    attention = [
        item
        for item in families
        if str(
            item.get(
                "final_priority",
                "",
            )
        ).upper()
        in (
            "HIGH",
            "MEDIUM",
        )
    ]

    attention.sort(
        key=attention_sort_key
    )

    shown = attention[
        :ATTENTION_LIMIT
    ]

    add("")

    if shown:
        add(
            f"Attention first "
            f"(showing {len(shown)}):"
        )

        for item in shown:
            label = issue_action_label(
                item
            )

            priority = str(
                item.get(
                    "final_priority",
                    "UNKNOWN",
                )
            ).upper()

            title = (
                item.get(
                    "title"
                )
                or "Unnamed System Log finding"
            )

            add(
                f"  [{label}] {priority} - {title}"
            )

            add(
                f"    {issue_note(item)}"
            )
    else:
        add(
            "No HIGH or MEDIUM System Log findings "
            "need to be surfaced."
        )

    hidden_medium = max(
        0,
        counts[
            "MEDIUM"
        ]
        - sum(
            1
            for item in shown
            if str(
                item.get(
                    "final_priority",
                    "",
                )
            ).upper()
            == "MEDIUM"
        ),
    )

    low_context = (
        counts[
            "LOW"
        ]
        + counts[
            "VERY LOW"
        ]
    )

    add("")

    if hidden_medium:
        add(
            f"Other MEDIUM findings:       "
            f"{hidden_medium}"
        )

    add(
        f"LOW / VERY LOW context:      "
        f"{low_context}"
    )

    if durable_count == 0:
        add(
            "No issue has yet been proven recurring "
            "across 24 hours."
        )
    else:
        add(
            "Durable recurrence is shown only when "
            "independent new activity spans 24+ hours."
        )

    if short_count:
        add(
            "Short-window repeats do not count as "
            "durable recurrence."
        )


def build_user_summary(
    *,
    summary_text,
    update_readiness,
    compatibility,
    availability,
    version,
    log_priority_final=None,
):
    overview = extract_overview(
        summary_text
    )

    health_status = overview.get(
        "Home Assistant health",
        "UNKNOWN",
    )

    core_guidance_status = overview.get(
        "Core update",
        "ASSESSMENT INCOMPLETE",
    )

    os_status = overview.get(
        "OS update",
        "UNKNOWN",
    )

    core_evidence_status = overview.get(
        "Core evidence collection",
        "UNKNOWN",
    )

    config_result = overview.get(
        "Config check",
        "UNKNOWN",
    )

    core_version = overview.get(
        "Core",
    )

    os_version = overview.get(
        "OS",
    )

    repairs = update_readiness.get(
        "repairs",
        {},
    )

    if not isinstance(
        repairs,
        dict,
    ):
        repairs = {}

    relevant_unignored_repairs = int(
        repairs.get(
            "relevant_unignored_count",
            0,
        )
        or 0
    )

    compatibility_summary = compatibility.get(
        "summary",
        {},
    )

    if not isinstance(
        compatibility_summary,
        dict,
    ):
        compatibility_summary = {}

    compatibility_rule_count = int(
        compatibility_summary.get(
            "rule_count",
            0,
        )
        or 0
    )

    compatibility_review_count = int(
        compatibility_summary.get(
            "review_required_count",
            0,
        )
        or 0
    )

    compatibility_manual_count = int(
        compatibility_summary.get(
            "manual_review_count",
            0,
        )
        or 0
    )

    local_no_affected_count = (
        count_local_no_affected(
            compatibility
        )
    )

    compatibility_coverage = compatibility.get(
        "coverage",
        {},
    )

    if not isinstance(
        compatibility_coverage,
        dict,
    ):
        compatibility_coverage = {}

    ui_prompts_inspected = bool(
        compatibility_coverage.get(
            "ui_managed_prompt_content_inspected",
            False,
        )
    )

    availability_summary = availability.get(
        "summary",
        {},
    )

    if not isinstance(
        availability_summary,
        dict,
    ):
        availability_summary = {}

    device_counts = availability_summary.get(
        "device_classification_counts",
        {},
    )

    entity_counts = availability_summary.get(
        "entity_classification_counts",
        {},
    )

    if not isinstance(
        device_counts,
        dict,
    ):
        device_counts = {}

    if not isinstance(
        entity_counts,
        dict,
    ):
        entity_counts = {}

    whole_device_count = int(
        device_counts.get(
            "whole_device_unavailable_unlabelled",
            0,
        )
        or 0
    )

    ungrouped_count = int(
        entity_counts.get(
            "ungrouped_unavailable",
            0,
        )
        or 0
    )

    decision = build_core_update_decision(
        core_guidance_status=(
            core_guidance_status
        ),
        config_result=config_result,
        core_assessment_complete=(
            core_evidence_status
            == "COMPLETE"
        ),
        relevant_unignored_repairs=(
            relevant_unignored_repairs
        ),
        compatibility_rule_count=(
            compatibility_rule_count
        ),
        compatibility_local_no_affected_count=(
            local_no_affected_count
        ),
        compatibility_review_required_count=(
            compatibility_review_count
        ),
        compatibility_manual_review_count=(
            compatibility_manual_count
        ),
        llm_local_match=(
            has_local_llm_match(
                compatibility
            )
        ),
        ui_prompts_inspected=(
            ui_prompts_inspected
        ),
        whole_device_unavailable_count=(
            whole_device_count
        ),
        ungrouped_unavailable_count=(
            ungrouped_count
        ),
    )

    lines = []

    def add(text=""):
        lines.append(text)

    add("=" * 58)
    add(
        f"HA AUDIT v{version} - USER SUMMARY"
    )
    add("=" * 58)

    add("")
    add("STATUS")
    add("-" * 58)
    add(
        f"Home Assistant health:       "
        f"{health_status}"
    )
    add(
        f"Core update guidance:        "
        f"{decision['recommendation']}"
    )
    add(
        f"OS update:                   "
        f"{os_status}"
    )
    add(
        f"Config check:                "
        f"{config_result}"
    )

    if core_version:
        add(
            f"Core:                        "
            f"{core_version}"
        )

    if os_version:
        add(
            f"OS:                          "
            f"{os_version}"
        )

    render_system_issues(
        add,
        log_priority_final,
    )

    add("")
    add("CORE UPDATE - WHAT TO DO")
    add("-" * 58)

    add("Before updating:")
    for item in decision[
        "before_update"
    ][:3]:
        add(
            f"  {item}"
        )

    evidence_parts = []

    if str(
        config_result
    ).upper() == "VALID":
        evidence_parts.append(
            "Configuration valid"
        )
    else:
        evidence_parts.append(
            f"Configuration {config_result.lower()}"
        )

    evidence_parts.append(
        (
            "Core evidence complete"
            if core_evidence_status == "COMPLETE"
            else "Core evidence incomplete"
        )
    )

    if relevant_unignored_repairs:
        evidence_parts.append(
            (
                f"{relevant_unignored_repairs} "
                "unignored Repair issue(s) relevant "
                "to this Core update"
            )
        )
    else:
        evidence_parts.append(
            "No unignored Repairs relevant to "
            "this Core update"
        )

    if compatibility_rule_count:
        evidence_parts.append(
            (
                f"{compatibility_rule_count} "
                "compatibility rules checked"
            )
        )

    if local_no_affected_count:
        rule_word = (
            "rule"
            if local_no_affected_count == 1
            else "rules"
        )

        evidence_parts.append(
            (
                f"{local_no_affected_count} "
                f"locally relevant {rule_word} checked "
                "with no affected use detected"
            )
        )

    if compatibility_review_count:
        evidence_parts.append(
            (
                f"{compatibility_review_count} "
                "rule(s) require review"
            )
        )

    if compatibility_manual_count:
        evidence_parts.append(
            (
                f"{compatibility_manual_count} "
                "rule(s) require manual review"
            )
        )

    add("")
    add("Why:")
    for item in evidence_parts:
        add(
            f"  {item}."
        )

    if decision[
        "conditional_checks"
    ]:
        add("")
        add("Conditional check:")
        for item in decision[
            "conditional_checks"
        ][:2]:
            add(
                f"  {item}"
            )

    if decision[
        "general_health"
    ]:
        add("")
        add(
            "General health - separate from Core update:"
        )

        for item in decision[
            "general_health"
        ][:3]:
            add(
                f"  {item}"
            )

        add(
            f"  {decision['general_health_note']}"
        )

    if decision[
        "after_update"
    ]:
        add("")
        add("After updating:")
        add(
            "  Rerun HA Audit and compare the "
            "new result with this baseline."
        )
        add(
            "  Check for new configuration errors, "
            "Repairs, unavailable entities or "
            "compatibility findings."
        )

    add("")
    add(
        "Evidence-based guidance only; this is not a "
        "guarantee. Detailed evidence and the AI / LLM "
        "handoff were generated separately."
    )
    add("=" * 58)

    return (
        "\n".join(
            lines
        )
        + "\n"
    )


def main():
    summary_text = load_text(
        SUMMARY_FILE
    )

    update_readiness = load_json_optional(
        UPDATE_READINESS_FILE
    )

    compatibility = load_json_optional(
        UPGRADE_COMPATIBILITY_FILE
    )

    availability = load_json_optional(
        AVAILABILITY_FILE
    )

    log_priority_final = load_json_optional(
        LOG_PRIORITY_FINAL_FILE
    )

    output = build_user_summary(
        summary_text=summary_text,
        update_readiness=update_readiness,
        compatibility=compatibility,
        availability=availability,
        log_priority_final=log_priority_final,
        version=VERSION,
    )

    print(
        output,
        end="",
    )


if __name__ == "__main__":
    main()
