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


def build_user_summary(
    *,
    summary_text,
    update_readiness,
    compatibility,
    availability,
    version,
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
        f"Core update guidance:         "
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
            "configuration valid"
        )
    else:
        evidence_parts.append(
            f"configuration {config_result.lower()}"
        )

    evidence_parts.append(
        (
            "Core evidence complete"
            if core_evidence_status == "COMPLETE"
            else "Core evidence incomplete"
        )
    )

    evidence_parts.append(
        (
            f"{relevant_unignored_repairs} "
            "relevant unignored Repairs"
        )
    )

    if compatibility_rule_count:
        evidence_parts.append(
            (
                f"{compatibility_rule_count} "
                "compatibility rules checked"
            )
        )

    if local_no_affected_count:
        evidence_parts.append(
            (
                f"{local_no_affected_count} "
                "locally relevant rule(s) checked "
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
        add("General health - separate from Core update:")
        for item in decision[
            "general_health"
        ][:3]:
            add(
                f"  {item}"
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
        decision[
            "caution"
        ]
    )

    add("")
    add("FULL EVIDENCE")
    add("-" * 58)
    add(
        "Full technical evidence and the AI / LLM "
        "handoff were generated separately."
    )
    add(
        "They are intentionally not repeated in "
        "the normal Home Assistant app log."
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

    output = build_user_summary(
        summary_text=summary_text,
        update_readiness=update_readiness,
        compatibility=compatibility,
        availability=availability,
        version=VERSION,
    )

    print(
        output,
        end="",
    )


if __name__ == "__main__":
    main()
