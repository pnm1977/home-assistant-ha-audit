import json
import os
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

INPUT_FILE = (
    "/config/log_priority_evidence.json"
)

OUTPUT_FILE = (
    "/config/log_priority.json"
)


PRIORITY_VERY_HIGH = "VERY HIGH"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"
PRIORITY_VERY_LOW = "VERY LOW"


OBSERVED = "OBSERVED"

SPAN_MULTI_DAY = "MULTI-DAY"

BREADTH_MULTIPLE = (
    "MULTIPLE TARGETS / PATHS"
)

ACTION_CLEAR_LOCAL = (
    "CLEAR LOCAL ACTION PATH"
)

ACTION_INVESTIGATE_LOCAL = (
    "LOCAL INVESTIGATION"
)

ACTION_LIMITED_LOCAL = (
    "LIMITED LOCAL CONTROL"
)

ACTION_PLATFORM = (
    "PLATFORM / UPSTREAM"
)


SPARSE_OCCURRENCE_MAX = 5
STRONG_RECURRENCE_MIN = 100


PRIORITY_ORDER = (
    PRIORITY_VERY_HIGH,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    PRIORITY_LOW,
    PRIORITY_VERY_LOW,
)


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(
    path,
):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(
            handle
        )


def clean_text(
    value,
):
    return " ".join(
        str(
            value or ""
        ).split()
    )


def safe_int(
    value,
):
    try:
        return int(
            value
        )
    except (
        TypeError,
        ValueError,
    ):
        return 0


def priority_index(
    priority,
):
    try:
        return PRIORITY_ORDER.index(
            priority
        )
    except ValueError:
        return len(
            PRIORITY_ORDER
        ) - 1


def promote(
    priority,
):
    index = priority_index(
        priority
    )

    if index <= 0:
        return PRIORITY_VERY_HIGH

    return PRIORITY_ORDER[
        index - 1
    ]


def demote(
    priority,
):
    index = priority_index(
        priority
    )

    if index >= (
        len(
            PRIORITY_ORDER
        )
        - 1
    ):
        return PRIORITY_VERY_LOW

    return PRIORITY_ORDER[
        index + 1
    ]


def cap_priority(
    priority,
    maximum,
):
    if (
        priority_index(
            priority
        )
        < priority_index(
            maximum
        )
    ):
        return maximum

    return priority


def base_priority(
    item,
):
    direct_failure = clean_text(
        item.get(
            "direct_failure_evidence"
        )
    )

    span = clean_text(
        item.get(
            "observed_span_class"
        )
    )

    breadth = clean_text(
        item.get(
            "breadth_evidence"
        )
    )

    action_path = clean_text(
        item.get(
            "local_action_path"
        )
    )

    occurrences = safe_int(
        item.get(
            "occurrence_count",
            0,
        )
    )

    if direct_failure != OBSERVED:
        if (
            span == SPAN_MULTI_DAY
            and breadth
            == BREADTH_MULTIPLE
        ):
            return (
                PRIORITY_LOW,
                (
                    "No direct functional failure "
                    "is observed, but the evidence "
                    "spans multiple days and affects "
                    "multiple targets or paths."
                ),
            )

        if (
            action_path
            == ACTION_CLEAR_LOCAL
            and occurrences > 1
        ):
            return (
                PRIORITY_LOW,
                (
                    "No direct functional failure "
                    "is observed, but there is a "
                    "clear local action path and the "
                    "condition occurred more than once."
                ),
            )

        return (
            PRIORITY_VERY_LOW,
            (
                "No direct functional failure is "
                "observed and the available evidence "
                "does not justify significant "
                "troubleshooting priority."
            ),
        )

    if action_path == ACTION_CLEAR_LOCAL:
        if span == SPAN_MULTI_DAY:
            return (
                PRIORITY_HIGH,
                (
                    "A direct failure is observed "
                    "across a multi-day span and "
                    "there is a clear local action "
                    "path."
                ),
            )

        if breadth == BREADTH_MULTIPLE:
            return (
                PRIORITY_MEDIUM,
                (
                    "A direct failure is observed "
                    "across multiple local execution "
                    "paths with a clear local action "
                    "path."
                ),
            )

        return (
            PRIORITY_LOW,
            (
                "A direct failure is observed with "
                "a clear local action path, but the "
                "current evidence is limited in "
                "time or breadth."
            ),
        )

    if (
        action_path
        == ACTION_INVESTIGATE_LOCAL
    ):
        if (
            span == SPAN_MULTI_DAY
            and breadth
            == BREADTH_MULTIPLE
        ):
            return (
                PRIORITY_HIGH,
                (
                    "A direct failure is observed "
                    "across a multi-day span and "
                    "multiple local targets or paths."
                ),
            )

        if (
            span == SPAN_MULTI_DAY
            or breadth
            == BREADTH_MULTIPLE
        ):
            return (
                PRIORITY_MEDIUM,
                (
                    "A direct failure is observed "
                    "with either multi-day or broad "
                    "local evidence."
                ),
            )

        return (
            PRIORITY_LOW,
            (
                "A direct failure is observed, but "
                "the current evidence is limited to "
                "a narrower local investigation."
            ),
        )

    if (
        action_path
        == ACTION_LIMITED_LOCAL
    ):
        if span == SPAN_MULTI_DAY:
            return (
                PRIORITY_MEDIUM,
                (
                    "A direct failure is observed "
                    "across a multi-day span, but "
                    "local control is limited because "
                    "the likely cause is external."
                ),
            )

        return (
            PRIORITY_LOW,
            (
                "A direct failure is observed, but "
                "the likely cause has limited local "
                "control and the evidence is not "
                "multi-day."
            ),
        )

    if action_path == ACTION_PLATFORM:
        if span == SPAN_MULTI_DAY:
            return (
                PRIORITY_MEDIUM,
                (
                    "A direct Home Assistant "
                    "platform or upstream failure is "
                    "observed across a multi-day span."
                ),
            )

        return (
            PRIORITY_LOW,
            (
                "A direct Home Assistant platform "
                "or upstream failure is observed, "
                "but the evidence is currently "
                "limited in duration."
            ),
        )

    if (
        span == SPAN_MULTI_DAY
        and breadth
        == BREADTH_MULTIPLE
    ):
        return (
            PRIORITY_MEDIUM,
            (
                "A direct failure is observed with "
                "multi-day and broad evidence, but "
                "the action domain remains unclear."
            ),
        )

    return (
        PRIORITY_LOW,
        (
            "A direct failure is observed, but the "
            "available evidence does not justify a "
            "higher priority."
        ),
    )


def apply_modifiers(
    item,
    priority,
):
    modifiers = []

    family_id = clean_text(
        item.get(
            "family_id"
        )
    )

    direct_failure = clean_text(
        item.get(
            "direct_failure_evidence"
        )
    )

    span = clean_text(
        item.get(
            "observed_span_class"
        )
    )

    recovery = clean_text(
        item.get(
            "recovery_evidence"
        )
    )

    fallback = clean_text(
        item.get(
            "fallback_evidence"
        )
    )

    ownership_confidence = clean_text(
        item.get(
            "ownership_confidence"
        )
    )

    action_path = clean_text(
        item.get(
            "local_action_path"
        )
    )

    occurrences = safe_int(
        item.get(
            "occurrence_count",
            0,
        )
    )

    if (
        priority == PRIORITY_MEDIUM
        and direct_failure == OBSERVED
        and span == SPAN_MULTI_DAY
        and action_path
        == ACTION_INVESTIGATE_LOCAL
        and occurrences
        >= STRONG_RECURRENCE_MIN
    ):
        priority = promote(
            priority
        )

        modifiers.append(
            (
                "Very strong repeated local failure "
                "evidence raises the priority by "
                "one level."
            )
        )

    if (
        recovery == OBSERVED
        or fallback == OBSERVED
    ):
        previous = priority

        priority = demote(
            priority
        )

        if priority != previous:
            if (
                recovery == OBSERVED
                and fallback == OBSERVED
            ):
                modifiers.append(
                    (
                        "Observed recovery and "
                        "fallback reduce the priority "
                        "by one level."
                    )
                )

            elif recovery == OBSERVED:
                modifiers.append(
                    (
                        "Observed recovery reduces "
                        "the priority by one level."
                    )
                )

            else:
                modifiers.append(
                    (
                        "Observed fallback reduces "
                        "the priority by one level."
                    )
                )

    if occurrences <= SPARSE_OCCURRENCE_MAX:
        capped = cap_priority(
            priority,
            PRIORITY_MEDIUM,
        )

        if capped != priority:
            priority = capped

            modifiers.append(
                (
                    "Sparse observed recurrence "
                    "caps log-only priority at "
                    "MEDIUM."
                )
            )

    if ownership_confidence == "LOW":
        capped = cap_priority(
            priority,
            PRIORITY_MEDIUM,
        )

        if capped != priority:
            priority = capped

            modifiers.append(
                (
                    "LOW ownership confidence caps "
                    "priority at MEDIUM."
                )
            )

    if family_id == "invalid_auth":
        capped = cap_priority(
            priority,
            PRIORITY_MEDIUM,
        )

        if capped != priority:
            priority = capped

            modifiers.append(
                (
                    "Authentication failures are "
                    "capped at MEDIUM until security "
                    "or client-impact evidence can "
                    "corroborate higher urgency."
                )
            )

    if (
        occurrences <= SPARSE_OCCURRENCE_MAX
        and action_path
        in (
            ACTION_LIMITED_LOCAL,
            ACTION_PLATFORM,
        )
    ):
        capped = cap_priority(
            priority,
            PRIORITY_LOW,
        )

        if capped != priority:
            priority = capped

            modifiers.append(
                (
                    "Sparse platform/upstream or "
                    "external-service evidence caps "
                    "priority at LOW."
                )
            )

    return (
        priority,
        modifiers,
    )


def classify_priority(
    item,
):
    (
        priority,
        basis,
    ) = base_priority(
        item
    )

    (
        priority,
        modifiers,
    ) = apply_modifiers(
        item,
        priority,
    )

    return {
        "priority": priority,
        "priority_basis": basis,
        "priority_modifiers": (
            modifiers
        ),
        "priority_method": (
            "deterministic_rule_hierarchy"
        ),
    }


def build_record(
    item,
):
    classification = (
        classify_priority(
            item
        )
    )

    return {
        "family_id": item.get(
            "family_id"
        ),
        "title": item.get(
            "title"
        ),
        "occurrence_count": safe_int(
            item.get(
                "occurrence_count",
                0,
            )
        ),
        "error_occurrences": safe_int(
            item.get(
                "error_occurrences",
                0,
            )
        ),
        "warning_occurrences": safe_int(
            item.get(
                "warning_occurrences",
                0,
            )
        ),
        "observed_span_class": (
            item.get(
                "observed_span_class"
            )
        ),
        "direct_failure_evidence": (
            item.get(
                "direct_failure_evidence"
            )
        ),
        "recovery_evidence": (
            item.get(
                "recovery_evidence"
            )
        ),
        "fallback_evidence": (
            item.get(
                "fallback_evidence"
            )
        ),
        "breadth_evidence": (
            item.get(
                "breadth_evidence"
            )
        ),
        "ownership": item.get(
            "ownership"
        ),
        "ownership_confidence": (
            item.get(
                "ownership_confidence"
            )
        ),
        "local_action_path": (
            item.get(
                "local_action_path"
            )
        ),
        "priority": classification[
            "priority"
        ],
        "priority_method": (
            classification[
                "priority_method"
            ]
        ),
        "priority_basis": (
            classification[
                "priority_basis"
            ]
        ),
        "priority_modifiers": (
            classification[
                "priority_modifiers"
            ]
        ),
    }


def build_report(
    evidence_report,
):
    source_status = (
        evidence_report.get(
            "source_status",
            {},
        )
    )

    if not isinstance(
        source_status,
        dict,
    ):
        source_status = {}

    family_status = (
        source_status.get(
            "family_status",
            "unknown",
        )
    )

    ownership_status = (
        source_status.get(
            "ownership_status",
            "unknown",
        )
    )

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_priority_probe"
            ),
            "input": (
                "log_priority_evidence.json"
            ),
            "priority_produced": True,
            "severity_produced": False,
            "action_recommendation_produced": (
                False
            ),
            "model": (
                "log_evidence_baseline_v2"
            ),
            "model_note": (
                "Priority is assigned by a "
                "deterministic rule hierarchy. "
                "Occurrence count is contextual "
                "evidence and is not a priority "
                "score."
            ),
            "recurrence_note": (
                "Occurrence count can strengthen "
                "or constrain an evidence-based "
                "priority, but does not determine "
                "priority by itself."
            ),
            "very_high_note": (
                "VERY HIGH is reserved for future "
                "corroborated critical-impact "
                "evidence and is not emitted by "
                "the current log-only model."
            ),
        },
        "source_status": {
            "family_status": family_status,
            "ownership_status": (
                ownership_status
            ),
        },
        "summary": {},
        "families": [],
    }

    if (
        family_status != "ok"
        or ownership_status != "ok"
    ):
        return report

    families = evidence_report.get(
        "families",
        [],
    )

    if not isinstance(
        families,
        list,
    ):
        families = []

    records = [
        build_record(
            item
        )
        for item in families
        if isinstance(
            item,
            dict,
        )
    ]

    records.sort(
        key=lambda item: (
            priority_index(
                item[
                    "priority"
                ]
            ),
            -item[
                "occurrence_count"
            ],
            str(
                item.get(
                    "title",
                    "",
                )
            ),
        )
    )

    priority_counts = {
        priority: 0
        for priority in PRIORITY_ORDER
    }

    for item in records:
        priority_counts[
            item[
                "priority"
            ]
        ] += 1

    report[
        "summary"
    ] = {
        "family_count": len(
            records
        ),
        "priority_counts": (
            priority_counts
        ),
        "very_high_emitted": (
            priority_counts[
                PRIORITY_VERY_HIGH
            ]
            > 0
        ),
        "priority_produced": True,
    }

    report[
        "families"
    ] = records

    return report


def main():
    try:
        evidence_report = load_json(
            INPUT_FILE
        )
    except Exception as exc:
        evidence_report = {
            "source_status": {
                "family_status": (
                    "input_unavailable"
                ),
                "ownership_status": (
                    "input_unavailable"
                ),
            },
            "input_error": str(
                exc
            ),
            "families": [],
        }

    report = build_report(
        evidence_report
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            report,
            handle,
            indent=2,
            sort_keys=False,
        )

        handle.write(
            "\n"
        )


if __name__ == "__main__":
    main()
