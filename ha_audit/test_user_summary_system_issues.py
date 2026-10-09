import io
import sys
import types


stub = types.ModuleType(
    "upgrade_decision"
)


def build_core_update_decision(**kwargs):
    return {
        "recommendation": "PROCEED",
        "before_update": [
            "HA Audit found no reason to delay "
            "this Core update."
        ],
        "conditional_checks": [],
        "general_health": [],
        "general_health_note": (
            "These findings are separate from "
            "the Core update."
        ),
        "after_update": [
            "Rerun HA Audit."
        ],
    }


stub.build_core_update_decision = (
    build_core_update_decision
)

sys.modules[
    "upgrade_decision"
] = stub

from user_summary import (
    render_system_issues,
)


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def issue(
    family_id,
    title,
    priority,
    *,
    occurrences,
    action,
    recurrence,
    changed=False,
    availability_effect="NO CHANGE",
    recovery="NOT OBSERVED",
    fallback="NOT OBSERVED",
):
    return {
        "family_id": family_id,
        "title": title,
        "occurrence_count": occurrences,
        "local_action_path": action,
        "recovery_evidence": recovery,
        "fallback_evidence": fallback,
        "final_priority": priority,
        "priority_changed": changed,
        "recurrence": {
            "class": recurrence,
            "effect": (
                "PROMOTION EVIDENCE"
                if recurrence
                == "RECURRING 24H+"
                else (
                    "NO CHANGE - SHORT WINDOW"
                    if recurrence
                    == "SHORT-WINDOW REPEAT"
                    else "NO CHANGE"
                )
            ),
        },
        "availability_correlation": {
            "effect": availability_effect,
        },
    }


def render(report):
    lines = []

    render_system_issues(
        lines.append,
        report,
    )

    return "\n".join(
        lines
    )


def main():
    report = {
        "status": "ok",
        "scope": {
            "priority_produced": True,
        },
        "summary": {
            "durable_recurrence_evidence_count": 0,
            "short_window_no_promotion_count": 12,
        },
        "families": [
            issue(
                "shelly",
                "Shelly integration data retrieval",
                "HIGH",
                occurrences=783,
                action="LOCAL INVESTIGATION",
                recurrence="SHORT-WINDOW REPEAT",
            ),
            issue(
                "zigbee",
                "Zigbee / ZHA delivery failures",
                "HIGH",
                occurrences=615,
                action="LOCAL INVESTIGATION",
                recurrence="SHORT-WINDOW REPEAT",
            ),
            issue(
                "esphome",
                "ESPHome device connectivity",
                "HIGH",
                occurrences=61,
                action="LOCAL INVESTIGATION",
                recurrence="SHORT-WINDOW REPEAT",
            ),
            issue(
                "hue",
                "Hue Sync Box connectivity",
                "HIGH",
                occurrences=6,
                action="LOCAL INVESTIGATION",
                recurrence="SHORT-WINDOW REPEAT",
            ),
            issue(
                "apple",
                "Apple TV connectivity",
                "MEDIUM",
                occurrences=303,
                action="LOCAL INVESTIGATION",
                recurrence="SHORT-WINDOW REPEAT",
                recovery="OBSERVED",
            ),
            issue(
                "mypyllant",
                "myVAILLANT API / data retrieval",
                "MEDIUM",
                occurrences=15,
                action="LIMITED LOCAL CONTROL",
                recurrence="SHORT-WINDOW REPEAT",
            ),
            issue(
                "robovac",
                "RoboVac connectivity",
                "MEDIUM",
                occurrences=12,
                action="LOCAL INVESTIGATION",
                recurrence="NOT ESTABLISHED",
            ),
            issue(
                "missing",
                "Referenced entities or devices not currently available",
                "MEDIUM",
                occurrences=1,
                action="UNKNOWN",
                recurrence="SHORT-WINDOW REPEAT",
                changed=True,
                availability_effect="PROMOTION EVIDENCE",
            ),
        ]
        + [
            issue(
                f"low_{index}",
                f"Low context {index}",
                "LOW",
                occurrences=1,
                action="UNKNOWN",
                recurrence="NOT ESTABLISHED",
            )
            for index in range(10)
        ]
        + [
            issue(
                f"very_low_{index}",
                f"Very low context {index}",
                "VERY LOW",
                occurrences=1,
                action="UNKNOWN",
                recurrence="NOT ESTABLISHED",
            )
            for index in range(9)
        ],
    }

    output = render(
        report
    )

    required = (
        "SYSTEM ISSUES",
        "Priority: HIGH 4 | MEDIUM 4 | LOW 10 | VERY LOW 9",
        "Durable recurrence (24h+):   0",
        "Short-window repeats:        12",
        "[INVESTIGATE] HIGH - Shelly integration data retrieval",
        "[INVESTIGATE] HIGH - Zigbee / ZHA delivery failures",
        "[INVESTIGATE] HIGH - ESPHome device connectivity",
        "[INVESTIGATE] HIGH - Hue Sync Box connectivity",
        "[REVIEW] MEDIUM - Referenced entities or devices not currently available",
        "Priority raised by direct whole-device unavailability and Recorder evidence.",
        "Other MEDIUM findings:       3",
        "LOW / VERY LOW context:      19",
        "No issue has yet been proven recurring across 24 hours.",
        "Short-window repeats do not count as durable recurrence.",
    )

    for text in required:
        require(
            text in output,
            (
                "Missing expected user-facing "
                f"text: {text}"
            ),
        )

    require(
        "Apple TV connectivity"
        not in output,
        (
            "Sixth-ranked issue leaked into "
            "the top-five list."
        ),
    )

    durable_report = {
        "status": "ok",
        "scope": {
            "priority_produced": True,
        },
        "summary": {
            "durable_recurrence_evidence_count": 1,
            "short_window_no_promotion_count": 0,
        },
        "families": [
            issue(
                "durable",
                "Durable local issue",
                "HIGH",
                occurrences=4,
                action="LOCAL INVESTIGATION",
                recurrence="RECURRING 24H+",
            )
        ],
    }

    durable_output = render(
        durable_report
    )

    require(
        (
            "Independent new activity has been "
            "observed across at least 24 hours."
        )
        in durable_output,
        (
            "Durable recurrence explanation "
            "was not surfaced."
        ),
    )

    unavailable_output = render(
        {}
    )

    require(
        "System Log prioritisation:    UNAVAILABLE"
        in unavailable_output,
        (
            "Unavailable final-priority evidence "
            "was not handled conservatively."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT USER SYSTEM ISSUES TEST"
    )
    print("=" * 62)
    print(
        "Priority counts rendered:      PASS"
    )
    print(
        "Top-five limit enforced:       PASS"
    )
    print(
        "Correlated promotion surfaced: PASS"
    )
    print(
        "Short-window wording safe:     PASS"
    )
    print(
        "Durable recurrence surfaced:   PASS"
    )
    print(
        "Low-priority context grouped:  PASS"
    )
    print(
        "Unavailable evidence safe:     PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
