import json
import os
from datetime import datetime, timezone

from upgrade_decision import (
    build_core_update_decision,
)

from user_summary import (
    ATTENTION_LIMIT,
    attention_sort_key,
    count_local_no_affected,
    extract_overview,
    has_local_llm_match,
    issue_action_label,
    issue_note,
    log_priority_available,
)


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

SUMMARY_FILE = (
    "/config/ha_audit_latest.txt"
)

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

OUTPUT_FILE = (
    "/config/ha_audit_ai_handoff.md"
)


SELECTED_SECTIONS = (
    "OVERVIEW",
    "WHY THIS RESULT",
    "SYSTEM",
    "UPDATE READINESS",
    "OFFICIAL RELEASE EVIDENCE",
    "UPGRADE COMPATIBILITY",
    "CONFIGURATION",
    "AVAILABILITY CONTEXT",
    "UNAVAILABLE HISTORY CONTEXT",
    "REVIEW",
    "NOT-PROVIDED HISTORY SAFETY",
    "NEXT ACTIONS",
)


KNOWN_SECTIONS = {
    "OVERVIEW",
    "WHY THIS RESULT",
    "SYSTEM",
    "UPDATE READINESS",
    "OFFICIAL RELEASE EVIDENCE",
    "COMPATIBILITY COVERAGE",
    "DYNAMIC UPGRADE CORRELATION",
    "CORRELATION VALIDATION",
    "UPGRADE COMPATIBILITY",
    "CONFIGURATION",
    "ENTITY HEALTH",
    "AVAILABILITY CONTEXT",
    "UNAVAILABLE HISTORY CONTEXT",
    "REVIEW",
    "NOT-PROVIDED HISTORY SAFETY",
    "NEXT ACTIONS",
    "DETAILED REPORTS",
}


STATUS_LABELS = {
    (
        "local_match_no_active_yaml_usage_found"
    ): (
        "No affected active YAML usage detected"
    ),
    (
        "local_match_no_affected_custom_usage_found"
    ): (
        "No affected custom integration usage detected"
    ),
    (
        "local_match_no_affected_usage_found"
    ): (
        "No affected usage detected"
    ),
    (
        "local_match_core_integrations_only"
    ): (
        "No affected custom usage detected"
    ),
    "review_required": (
        "Review required"
    ),
    "manual_review": (
        "Manual review required"
    ),
}


def load_json_optional(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(
                handle
            )
    except Exception:
        return {}


def load_text(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return handle.read()


def extract_selected_sections(
    summary_text,
):
    found = {}
    current_heading = None
    current_lines = []

    def save_current():
        if (
            current_heading
            and current_lines
            and current_heading
            not in found
        ):
            found[
                current_heading
            ] = "\n".join(
                current_lines
            ).strip()

    for raw_line in summary_text.splitlines():
        stripped = raw_line.strip()

        if stripped in KNOWN_SECTIONS:
            save_current()

            current_heading = stripped
            current_lines = [
                raw_line
            ]
            continue

        if current_heading:
            current_lines.append(
                raw_line
            )

    save_current()

    selected = []

    for heading in SELECTED_SECTIONS:
        text = found.get(
            heading
        )

        if text:
            selected.append(
                text
            )

    return "\n\n".join(
        selected
    )


def get_relevant_unignored_repairs(
    update_readiness,
):
    repairs = update_readiness.get(
        "repairs",
        {},
    )

    if not isinstance(
        repairs,
        dict,
    ):
        return 0

    try:
        return max(
            0,
            int(
                repairs.get(
                    "relevant_unignored_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def get_compatibility_summary(
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
        return {}

    return summary


def get_availability_counts(
    availability,
):
    summary = availability.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        summary = {}

    device_counts = summary.get(
        "device_classification_counts",
        {},
    )

    entity_counts = summary.get(
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

    try:
        whole_device_count = max(
            0,
            int(
                device_counts.get(
                    "whole_device_unavailable_unlabelled",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        whole_device_count = 0

    try:
        ungrouped_count = max(
            0,
            int(
                entity_counts.get(
                    "ungrouped_unavailable",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        ungrouped_count = 0

    return (
        whole_device_count,
        ungrouped_count,
    )


def build_decision(
    *,
    summary_text,
    update_readiness,
    compatibility,
    availability,
):
    overview = extract_overview(
        summary_text
    )

    compatibility_summary = (
        get_compatibility_summary(
            compatibility
        )
    )

    coverage = compatibility.get(
        "coverage",
        {},
    )

    if not isinstance(
        coverage,
        dict,
    ):
        coverage = {}

    (
        whole_device_count,
        ungrouped_count,
    ) = get_availability_counts(
        availability
    )

    try:
        rule_count = max(
            0,
            int(
                compatibility_summary.get(
                    "rule_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        rule_count = 0

    try:
        review_count = max(
            0,
            int(
                compatibility_summary.get(
                    "review_required_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        review_count = 0

    try:
        manual_count = max(
            0,
            int(
                compatibility_summary.get(
                    "manual_review_count",
                    0,
                )
                or 0
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        manual_count = 0

    return build_core_update_decision(
        core_guidance_status=(
            overview.get(
                "Core update",
                "ASSESSMENT INCOMPLETE",
            )
        ),
        config_result=(
            overview.get(
                "Config check",
                "UNKNOWN",
            )
        ),
        core_assessment_complete=(
            overview.get(
                "Core evidence collection"
            )
            == "COMPLETE"
        ),
        relevant_unignored_repairs=(
            get_relevant_unignored_repairs(
                update_readiness
            )
        ),
        compatibility_rule_count=(
            rule_count
        ),
        compatibility_local_no_affected_count=(
            count_local_no_affected(
                compatibility
            )
        ),
        compatibility_review_required_count=(
            review_count
        ),
        compatibility_manual_review_count=(
            manual_count
        ),
        llm_local_match=(
            has_local_llm_match(
                compatibility
            )
        ),
        ui_prompts_inspected=bool(
            coverage.get(
                "ui_managed_prompt_content_inspected",
                False,
            )
        ),
        whole_device_unavailable_count=(
            whole_device_count
        ),
        ungrouped_unavailable_count=(
            ungrouped_count
        ),
    )


def relevant_compatibility_results(
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
        return []

    return [
        item
        for item in results
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "local_match",
                False,
            )
        )
    ]


def format_status(
    status,
):
    if status in STATUS_LABELS:
        return STATUS_LABELS[
            status
        ]

    return str(
        status or "unknown"
    ).replace(
        "_",
        " ",
    ).strip().capitalize()


def render_decision_support(
    lines,
    decision,
):
    lines.append(
        "## Core update decision support"
    )
    lines.append("")
    lines.append(
        "HA Audit's interpretation of the "
        "evidence it collected:"
    )
    lines.append("")
    lines.append(
        f"**Recommendation: "
        f"{decision['recommendation']}**"
    )

    lines.append("")
    lines.append(
        "**Before updating:**"
    )

    for item in decision[
        "before_update"
    ]:
        lines.append(
            f"- {item}"
        )

    if decision[
        "conditional_checks"
    ]:
        lines.append("")
        lines.append(
            "**Conditional checks / uncertainty:**"
        )

        for item in decision[
            "conditional_checks"
        ]:
            lines.append(
                f"- {item}"
            )

    if decision[
        "general_health"
    ]:
        lines.append("")
        lines.append(
            "**General Home Assistant health "
            "context:**"
        )

        for item in decision[
            "general_health"
        ]:
            lines.append(
                f"- {item}"
            )

        lines.append(
            f"- {decision['general_health_note']}"
        )

    if decision[
        "after_update"
    ]:
        lines.append("")
        lines.append(
            "**After updating:**"
        )

        for item in decision[
            "after_update"
        ]:
            lines.append(
                f"- {item}"
            )

    lines.append("")
    lines.append(
        f"*{decision['caution']}*"
    )


def render_local_compatibility(
    lines,
    compatibility,
):
    lines.append(
        "## Locally relevant Core compatibility findings"
    )
    lines.append("")

    results = relevant_compatibility_results(
        compatibility
    )

    if not results:
        lines.append(
            "No locally relevant deterministic "
            "compatibility rule was identified."
        )
        return

    lines.append(
        "Only rules with local evidence are shown "
        "here. Rules with no local match are omitted "
        "from this concise handoff."
    )

    for item in results:
        area = str(
            item.get(
                "area",
                "Unknown area",
            )
        )

        change = str(
            item.get(
                "change",
                "No change description available.",
            )
        )

        status = format_status(
            item.get(
                "status"
            )
        )

        note = str(
            item.get(
                "note",
                "No local evidence explanation available.",
            )
        )

        lines.append("")
        lines.append(
            f"### {area}"
        )
        lines.append("")
        lines.append(
            f"- **Change:** {change}"
        )
        lines.append(
            f"- **Result:** {status}."
        )
        lines.append(
            f"- **HA Audit evidence:** {note}"
        )

        evidence = item.get(
            "evidence",
            {},
        )

        if (
            isinstance(
                evidence,
                dict,
            )
            and (
                "llm" in str(
                    item.get(
                        "id",
                        "",
                    )
                ).lower()
                or "llm" in area.lower()
            )
            and not evidence.get(
                "ui_managed_prompt_content_inspected",
                False,
            )
        ):
            lines.append(
                "- **Remaining uncertainty:** "
                "UI-managed prompt/config-entry "
                "content was not inspected."
            )


def get_priority_counts(
    report,
):
    summary = report.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        summary = {}

    counts = summary.get(
        "final_priority_counts",
        {},
    )

    if isinstance(
        counts,
        dict,
    ):
        return {
            "HIGH": int(
                counts.get(
                    "HIGH",
                    0,
                )
                or 0
            ),
            "MEDIUM": int(
                counts.get(
                    "MEDIUM",
                    0,
                )
                or 0
            ),
            "LOW": int(
                counts.get(
                    "LOW",
                    0,
                )
                or 0
            ),
            "VERY LOW": int(
                counts.get(
                    "VERY LOW",
                    0,
                )
                or 0
            ),
        }

    return {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "VERY LOW": 0,
    }


def render_system_issues(
    lines,
    report,
):
    lines.append(
        "## System issues"
    )
    lines.append("")

    if not log_priority_available(
        report
    ):
        lines.append(
            "Final System Log prioritisation was "
            "not available for this run."
        )
        lines.append("")
        lines.append(
            "Do not infer issue priority or recurrence "
            "from raw occurrence counts alone."
        )
        return

    summary = report.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        summary = {}

    counts = get_priority_counts(
        report
    )

    durable_count = int(
        summary.get(
            "durable_recurrence_evidence_count",
            0,
        )
        or 0
    )

    short_count = int(
        summary.get(
            "short_window_no_promotion_count",
            0,
        )
        or 0
    )

    lines.append(
        "HA Audit's final System Log prioritisation "
        "for the current run:"
    )
    lines.append("")
    lines.append(
        "- **Priority counts:** "
        f"HIGH {counts['HIGH']}; "
        f"MEDIUM {counts['MEDIUM']}; "
        f"LOW {counts['LOW']}; "
        f"VERY LOW {counts['VERY LOW']}."
    )
    lines.append(
        "- **Durable recurrence (24h+):** "
        f"{durable_count}."
    )
    lines.append(
        "- **Short-window repeats:** "
        f"{short_count}. These do not count as "
        "durable recurrence."
    )

    families = [
        item
        for item in report.get(
            "families",
            [],
        )
        if (
            isinstance(
                item,
                dict,
            )
            and str(
                item.get(
                    "final_priority",
                    "",
                )
            ).upper()
            in (
                "HIGH",
                "MEDIUM",
            )
        )
    ]

    families.sort(
        key=attention_sort_key
    )

    shown = families[
        :ATTENTION_LIMIT
    ]

    lines.append("")
    lines.append(
        "### Attention first"
    )
    lines.append("")

    if not shown:
        lines.append(
            "No HIGH or MEDIUM System Log finding "
            "was available to surface."
        )
    else:
        for item in shown:
            priority = str(
                item.get(
                    "final_priority",
                    "UNKNOWN",
                )
            ).upper()

            title = str(
                item.get(
                    "title"
                )
                or "Unnamed System Log finding"
            )

            recurrence = item.get(
                "recurrence",
                {},
            )

            if not isinstance(
                recurrence,
                dict,
            ):
                recurrence = {}

            recurrence_class = str(
                recurrence.get(
                    "class"
                )
                or "NOT ESTABLISHED"
            )

            lines.append(
                f"- **{priority} — {title}**"
            )
            lines.append(
                "  - **Attention label:** "
                f"{issue_action_label(item)}."
            )
            lines.append(
                "  - **Recurrence:** "
                f"{recurrence_class}."
            )
            lines.append(
                "  - **Evidence note:** "
                f"{issue_note(item)}"
            )

    shown_medium = sum(
        1
        for item in shown
        if str(
            item.get(
                "final_priority",
                "",
            )
        ).upper()
        == "MEDIUM"
    )

    hidden_medium = max(
        0,
        counts[
            "MEDIUM"
        ]
        - shown_medium,
    )

    low_context = (
        counts[
            "LOW"
        ]
        + counts[
            "VERY LOW"
        ]
    )

    lines.append("")
    lines.append(
        "Only the top HIGH/MEDIUM findings are shown "
        "in this concise handoff."
    )

    if hidden_medium:
        lines.append(
            f"- Other MEDIUM findings omitted: "
            f"{hidden_medium}."
        )

    lines.append(
        "- LOW / VERY LOW contextual findings omitted: "
        f"{low_context}."
    )

    lines.append(
        "- Request `log_priority_final.json` if the "
        "complete prioritised family list is needed."
    )

    lines.append("")
    lines.append(
        "Treat these as HA Audit's evidence-based "
        "priorities, not as severity judgements or proof "
        "of a fault. Do not re-rank an issue solely from "
        "its raw occurrence count."
    )


def build_ai_handoff(
    *,
    summary_text,
    update_readiness,
    compatibility,
    availability,
    version,
    log_priority_final=None,
    generated_at=None,
):
    if generated_at is None:
        generated_at = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

    decision = build_decision(
        summary_text=summary_text,
        update_readiness=update_readiness,
        compatibility=compatibility,
        availability=availability,
    )

    evidence = extract_selected_sections(
        summary_text
    )

    lines = []

    lines.append(
        "# HA Audit AI / LLM Handoff"
    )
    lines.append("")
    lines.append(
        "This file was generated automatically "
        f"by HA Audit v{version}."
    )
    lines.append("")
    lines.append(
        f"Generated: {generated_at}"
    )

    lines.append("")
    lines.append(
        "## Purpose"
    )
    lines.append("")
    lines.append(
        "This is a vendor-neutral handoff for "
        "analysis by an AI or large language model."
    )
    lines.append("")
    lines.append(
        "It is intended for assistants such as "
        "ChatGPT, Claude, Gemini, local LLMs, or "
        "other systems capable of analysing "
        "Home Assistant evidence."
    )
    lines.append("")
    lines.append(
        "The evidence below is a concise selection "
        "from HA Audit's current run plus structured "
        "decision-support context."
    )

    lines.append("")
    lines.append(
        "## Instructions for the receiving AI"
    )
    lines.append("")
    lines.append(
        "- Treat HA Audit findings as evidence, "
        "not as proof of a fault or guarantee of safety."
    )
    lines.append(
        "- Clearly distinguish facts reported by "
        "HA Audit from your own inference or advice."
    )
    lines.append(
        "- Do not claim that a Home Assistant "
        "update is guaranteed safe."
    )
    lines.append(
        "- Treat the Core update recommendation as "
        "HA Audit's interpretation of its evidence, "
        "not as independent proof."
    )
    lines.append(
        "- If the recommendation conflicts with the "
        "supporting evidence or limitations, call out "
        "that conflict rather than repeating it."
    )
    lines.append(
        "- Do not recommend deleting entities, "
        "devices, YAML, automations, scripts, or "
        "configuration solely because they are "
        "unavailable, unknown, or not currently provided."
    )
    lines.append(
        "- Treat availability and Recorder-history "
        "findings as context unless stronger evidence "
        "shows an actual fault."
    )
    lines.append(
        "- Respect HA Audit's distinction between "
        "general Home Assistant health and Core "
        "update guidance."
    )
    lines.append(
        "- If evidence collection is incomplete, "
        "say what is missing rather than filling the "
        "gap with an assumption."
    )
    lines.append(
        "- For each locally relevant compatibility "
        "finding, explain why it was cleared or why "
        "review is still required."
    )
    lines.append(
        "- Prioritise concrete findings that deserve "
        "attention before informational observations."
    )
    lines.append(
        "- Use the System issues section as HA Audit's "
        "current prioritisation; do not re-rank issues "
        "solely from raw occurrence counts."
    )
    lines.append(
        "- Treat SHORT-WINDOW REPEAT as distinct from "
        "durable 24-hour recurrence."
    )
    lines.append(
        "- Explain findings in normal Home Assistant "
        "language suitable for a smart-home enthusiast."
    )
    lines.append(
        "- When suggesting a change, explain which "
        "HA Audit evidence supports that suggestion."
    )

    lines.append("")
    lines.append(
        "## Important limitations"
    )
    lines.append("")
    lines.append(
        "- HA Audit is read-only and does not prove "
        "that an installation is fault-free."
    )
    lines.append(
        "- Core update guidance is conservative "
        "evidence-based guidance, not a safe-to-update "
        "guarantee."
    )
    lines.append(
        "- Availability classifications may represent "
        "intentional, temporary, or feature-level states."
    )
    lines.append(
        "- Recorder history only covers the history "
        "that was actually available to HA Audit."
    )
    lines.append(
        "- Some Home Assistant configuration may be "
        "UI-managed or otherwise outside the local "
        "scan scope."
    )
    lines.append(
        "- Lower-level technical evidence and detailed "
        "JSON reports contain more information than "
        "this handoff."
    )
    lines.append(
        "- The System issues section intentionally shows "
        "only the highest-priority current findings; "
        "lower-priority families remain in the detailed "
        "final-priority report."
    )
    lines.append(
        "- If this handoff is insufficient, request "
        "the relevant detailed report rather than "
        "inventing missing information."
    )

    lines.append("")
    render_decision_support(
        lines,
        decision,
    )

    lines.append("")
    render_system_issues(
        lines,
        log_priority_final,
    )

    lines.append("")
    render_local_compatibility(
        lines,
        compatibility,
    )

    lines.append("")
    lines.append(
        "## Requested analysis"
    )
    lines.append("")
    lines.append(
        "Using the evidence below, answer in this order:"
    )
    lines.append("")
    lines.append(
        "1. **Core update recommendation** — explain "
        "whether the evidence supports proceeding, "
        "reviewing first, delaying, or treating the "
        "assessment as incomplete."
    )
    lines.append(
        "2. **Required before updating** — list only "
        "concrete actions that should be completed "
        "before the Core update."
    )
    lines.append(
        "3. **Conditional checks / uncertainty** — "
        "state anything HA Audit could not inspect or "
        "prove."
    )
    lines.append(
        "4. **System issues** — use HA Audit's final "
        "priorities and recurrence evidence to identify "
        "what deserves attention first. Do not treat "
        "SHORT-WINDOW REPEAT as durable recurrence."
    )
    lines.append(
        "5. **General Home Assistant health** — "
        "separate broader health context from both "
        "System Log findings and Core-update relevance."
    )
    lines.append(
        "6. **After updating** — explain what should "
        "be checked when HA Audit is rerun."
    )
    lines.append("")
    lines.append(
        "Do not turn informational counts into required "
        "work unless the evidence supports that conclusion."
    )

    lines.append("")
    lines.append(
        "## HA Audit evidence"
    )
    lines.append("")
    lines.append(
        "```text"
    )
    lines.append(
        evidence
    )
    lines.append(
        "```"
    )

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

    output = build_ai_handoff(
        summary_text=summary_text,
        update_readiness=update_readiness,
        compatibility=compatibility,
        availability=availability,
        version=VERSION,
        log_priority_final=log_priority_final,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            output
        )


if __name__ == "__main__":
    main()
