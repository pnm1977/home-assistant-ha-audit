import json
import os
from collections import Counter
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

PRIORITY_FILE = (
    "/config/log_priority.json"
)

FINGERPRINT_FILE = (
    "/config/log_family_fingerprints.json"
)

RECURRENCE_FILE = (
    "/config/log_recurrence.json"
)

CORRELATION_FILE = (
    "/config/log_correlation.json"
)

OUTPUT_FILE = (
    "/config/log_priority_final.json"
)


PRIORITY_ORDER = (
    "VERY LOW",
    "LOW",
    "MEDIUM",
    "HIGH",
    "VERY HIGH",
)

MAX_EMITTED_PRIORITY = (
    "HIGH"
)

RECURRING_24H = (
    "RECURRING 24H+"
)

SHORT_WINDOW_REPEAT = (
    "SHORT-WINDOW REPEAT"
)

DIRECT_WHOLE_DEVICE = (
    "DIRECT WHOLE-DEVICE UNAVAILABLE"
)

NO_USABLE_HISTORY = (
    "NO USABLE HISTORY OBSERVED"
)

NO_DIRECT_MATCH = (
    "NO DIRECT MATCH"
)

NO_REPAIR_MATCH = (
    "NO DOMAIN MATCH"
)

LIMITED_LOCAL_CONTROL = (
    "LIMITED LOCAL CONTROL"
)

PLATFORM_UPSTREAM = (
    "PLATFORM / UPSTREAM"
)

UNKNOWN_ACTION = (
    "UNKNOWN"
)

MIXED_UNKNOWN = (
    "MIXED / UNKNOWN"
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


def write_json(
    path,
    payload,
):
    with open(
        path,
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            payload,
            handle,
            indent=2,
            sort_keys=False,
        )

        handle.write(
            "\n"
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
    value,
):
    try:
        return PRIORITY_ORDER.index(
            value
        )
    except ValueError:
        return -1


def priority_counts(
    records,
    field,
):
    counts = Counter(
        record.get(
            field
        )
        for record in records
    )

    return {
        priority: safe_int(
            counts.get(
                priority,
                0,
            )
        )
        for priority in reversed(
            PRIORITY_ORDER
        )
    }


def duplicate_values(
    values,
):
    counts = Counter(
        value
        for value in values
        if value
    )

    return sorted(
        value
        for value, count
        in counts.items()
        if count > 1
    )


def one_level_up(
    priority,
):
    index = priority_index(
        priority
    )

    if index < 0:
        return priority

    max_index = priority_index(
        MAX_EMITTED_PRIORITY
    )

    return PRIORITY_ORDER[
        min(
            index + 1,
            max_index,
        )
    ]


def cap_priority(
    priority,
    maximum,
):
    priority_pos = priority_index(
        priority
    )

    maximum_pos = priority_index(
        maximum
    )

    if (
        priority_pos < 0
        or maximum_pos < 0
    ):
        return priority

    return PRIORITY_ORDER[
        min(
            priority_pos,
            maximum_pos,
        )
    ]


def report_version(
    report,
):
    return str(
        report.get(
            "audit_version",
            ""
        )
        or ""
    )


def priority_source_ok(
    report,
):
    scope = report.get(
        "scope",
        {},
    )

    source_status = report.get(
        "source_status",
        {},
    )

    return (
        isinstance(
            scope,
            dict,
        )
        and scope.get(
            "priority_produced"
        )
        is True
        and isinstance(
            source_status,
            dict,
        )
        and source_status.get(
            "family_status"
        )
        == "ok"
        and source_status.get(
            "ownership_status"
        )
        == "ok"
        and isinstance(
            report.get(
                "families"
            ),
            list,
        )
    )


def fingerprint_source_ok(
    report,
):
    scope = report.get(
        "scope",
        {},
    )

    source_collection = report.get(
        "source_collection",
        {},
    )

    duplicate_groups = report.get(
        "duplicate_fingerprint_groups",
        [],
    )

    return (
        isinstance(
            scope,
            dict,
        )
        and scope.get(
            "stable_fingerprints_produced"
        )
        is True
        and isinstance(
            source_collection,
            dict,
        )
        and source_collection.get(
            "status"
        )
        == "ok"
        and isinstance(
            report.get(
                "families"
            ),
            list,
        )
        and isinstance(
            duplicate_groups,
            list,
        )
        and len(
            duplicate_groups
        )
        == 0
    )


def recurrence_source_ok(
    report,
):
    scope = report.get(
        "scope",
        {},
    )

    return (
        report.get(
            "status"
        )
        == "ok"
        and isinstance(
            scope,
            dict,
        )
        and scope.get(
            "recurrence_evidence_produced"
        )
        is True
        and isinstance(
            report.get(
                "families"
            ),
            list,
        )
    )


def correlation_source_ok(
    report,
):
    scope = report.get(
        "scope",
        {},
    )

    return (
        report.get(
            "status"
        )
        == "ok"
        and isinstance(
            scope,
            dict,
        )
        and scope.get(
            "correlation_produced"
        )
        is True
        and isinstance(
            report.get(
                "families"
            ),
            list,
        )
    )


def family_map(
    items,
):
    result = {}

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        family_id = item.get(
            "family_id"
        )

        if not family_id:
            continue

        result[
            family_id
        ] = item

    return result


def fingerprint_map(
    items,
):
    result = {}

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        family_id = item.get(
            "family_id"
        )

        fingerprint = item.get(
            "stable_fingerprint"
        )

        if (
            not family_id
            or not fingerprint
        ):
            continue

        result[
            family_id
        ] = fingerprint

    return result


def current_recurrence_map(
    items,
):
    result = {}

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        if not bool(
            item.get(
                "seen_in_latest_audit",
                False,
            )
        ):
            continue

        fingerprint = item.get(
            "stable_fingerprint"
        )

        if not fingerprint:
            continue

        result[
            fingerprint
        ] = item

    return result


def validate_alignment(
    priority_report,
    fingerprint_report,
    recurrence_report,
    correlation_report,
):
    source_checks = {
        "priority": (
            priority_source_ok(
                priority_report
            )
        ),
        "fingerprints": (
            fingerprint_source_ok(
                fingerprint_report
            )
        ),
        "recurrence": (
            recurrence_source_ok(
                recurrence_report
            )
        ),
        "correlation": (
            correlation_source_ok(
                correlation_report
            )
        ),
    }

    if not all(
        source_checks.values()
    ):
        return (
            False,
            (
                "One or more required source "
                "reports are incomplete."
            ),
            source_checks,
            {},
        )

    versions = {
        report_version(
            priority_report
        ),
        report_version(
            fingerprint_report
        ),
        report_version(
            recurrence_report
        ),
        report_version(
            correlation_report
        ),
    }

    versions.discard(
        ""
    )

    if len(
        versions
    ) != 1:
        return (
            False,
            (
                "Source reports do not share "
                "one audit version."
            ),
            source_checks,
            {
                "versions": sorted(
                    versions
                ),
            },
        )

    priority_items = (
        priority_report.get(
            "families",
            [],
        )
    )

    fingerprint_items = (
        fingerprint_report.get(
            "families",
            [],
        )
    )

    correlation_items = (
        correlation_report.get(
            "families",
            [],
        )
    )

    recurrence_items = (
        recurrence_report.get(
            "families",
            [],
        )
    )

    priority_ids = [
        item.get(
            "family_id"
        )
        for item in priority_items
        if isinstance(
            item,
            dict,
        )
    ]

    fingerprint_ids = [
        item.get(
            "family_id"
        )
        for item in fingerprint_items
        if isinstance(
            item,
            dict,
        )
    ]

    correlation_ids = [
        item.get(
            "family_id"
        )
        for item in correlation_items
        if isinstance(
            item,
            dict,
        )
    ]

    duplicate_family_ids = sorted(
        set(
            duplicate_values(
                priority_ids
            )
            + duplicate_values(
                fingerprint_ids
            )
            + duplicate_values(
                correlation_ids
            )
        )
    )

    if duplicate_family_ids:
        return (
            False,
            (
                "One or more source reports "
                "contain duplicate family IDs."
            ),
            source_checks,
            {
                "duplicate_family_ids": (
                    duplicate_family_ids
                ),
            },
        )

    priority_set = set(
        priority_ids
    )

    fingerprint_set = set(
        fingerprint_ids
    )

    correlation_set = set(
        correlation_ids
    )

    if not (
        priority_set
        == fingerprint_set
        == correlation_set
    ):
        return (
            False,
            (
                "Priority, fingerprint and "
                "correlation family sets do "
                "not align."
            ),
            source_checks,
            {
                "priority_family_count": (
                    len(
                        priority_set
                    )
                ),
                "fingerprint_family_count": (
                    len(
                        fingerprint_set
                    )
                ),
                "correlation_family_count": (
                    len(
                        correlation_set
                    )
                ),
            },
        )

    fingerprints = (
        fingerprint_map(
            fingerprint_items
        )
    )

    duplicate_fingerprints = (
        duplicate_values(
            fingerprints.values()
        )
    )

    if duplicate_fingerprints:
        return (
            False,
            (
                "Current fingerprint mapping "
                "contains duplicates."
            ),
            source_checks,
            {
                "duplicate_fingerprints": (
                    duplicate_fingerprints
                ),
            },
        )

    recurrence_by_fingerprint = (
        current_recurrence_map(
            recurrence_items
        )
    )

    fingerprint_set_current = set(
        fingerprints.values()
    )

    recurrence_set_current = set(
        recurrence_by_fingerprint.keys()
    )

    if (
        fingerprint_set_current
        != recurrence_set_current
    ):
        return (
            False,
            (
                "Current recurrence fingerprints "
                "do not align with the current "
                "fingerprint report."
            ),
            source_checks,
            {
                "fingerprint_count": len(
                    fingerprint_set_current
                ),
                "current_recurrence_count": len(
                    recurrence_set_current
                ),
            },
        )

    mismatched_family_ids = []

    for family_id, fingerprint in (
        fingerprints.items()
    ):
        recurrence = (
            recurrence_by_fingerprint.get(
                fingerprint,
                {},
            )
        )

        if recurrence.get(
            "family_id"
        ) != family_id:
            mismatched_family_ids.append(
                family_id
            )

    if mismatched_family_ids:
        return (
            False,
            (
                "Current recurrence family IDs "
                "do not align with stable "
                "fingerprints."
            ),
            source_checks,
            {
                "mismatched_family_ids": (
                    sorted(
                        mismatched_family_ids
                    )
                ),
            },
        )

    return (
        True,
        None,
        source_checks,
        {
            "family_count": len(
                priority_set
            ),
            "stable_fingerprint_count": (
                len(
                    fingerprint_set_current
                )
            ),
            "current_recurrence_count": (
                len(
                    recurrence_set_current
                )
            ),
        },
    )


def recurrence_can_promote(
    priority_item,
    recurrence_item,
):
    return (
        recurrence_item.get(
            "recurrence_class"
        )
        == RECURRING_24H
        and priority_item.get(
            "direct_failure_evidence"
        )
        == "OBSERVED"
        and priority_item.get(
            "recovery_evidence"
        )
        != "OBSERVED"
        and priority_item.get(
            "fallback_evidence"
        )
        != "OBSERVED"
    )


def correlation_can_promote(
    priority_item,
    correlation_item,
):
    availability = (
        correlation_item.get(
            "availability",
            {},
        )
    )

    unavailable_history = (
        correlation_item.get(
            "unavailable_history",
            {},
        )
    )

    if not isinstance(
        availability,
        dict,
    ):
        availability = {}

    if not isinstance(
        unavailable_history,
        dict,
    ):
        unavailable_history = {}

    return (
        priority_item.get(
            "direct_failure_evidence"
        )
        == "OBSERVED"
        and availability.get(
            "classification"
        )
        == DIRECT_WHOLE_DEVICE
        and unavailable_history.get(
            "classification"
        )
        == NO_USABLE_HISTORY
    )


def promotion_cap(
    priority_item,
):
    action_path = priority_item.get(
        "local_action_path"
    )

    ownership = priority_item.get(
        "ownership"
    )

    if action_path in {
        LIMITED_LOCAL_CONTROL,
        PLATFORM_UPSTREAM,
        UNKNOWN_ACTION,
    }:
        return "MEDIUM"

    if ownership == MIXED_UNKNOWN:
        return "MEDIUM"

    return MAX_EMITTED_PRIORITY


def build_family_record(
    priority_item,
    fingerprint,
    recurrence_item,
    correlation_item,
):
    base_priority = priority_item.get(
        "priority"
    )

    recurrence_class = (
        recurrence_item.get(
            "recurrence_class"
        )
    )

    availability = (
        correlation_item.get(
            "availability",
            {},
        )
    )

    unavailable_history = (
        correlation_item.get(
            "unavailable_history",
            {},
        )
    )

    repairs = (
        correlation_item.get(
            "repairs",
            {},
        )
    )

    if not isinstance(
        availability,
        dict,
    ):
        availability = {}

    if not isinstance(
        unavailable_history,
        dict,
    ):
        unavailable_history = {}

    if not isinstance(
        repairs,
        dict,
    ):
        repairs = {}

    recurrence_qualifies = (
        recurrence_can_promote(
            priority_item,
            recurrence_item,
        )
    )

    correlation_qualifies = (
        correlation_can_promote(
            priority_item,
            correlation_item,
        )
    )

    promotion_evidence = []

    if recurrence_qualifies:
        promotion_evidence.append(
            (
                "Durable recurrence has been "
                "observed across at least 24 "
                "hours without observed recovery "
                "or fallback."
            )
        )

    if correlation_qualifies:
        promotion_evidence.append(
            (
                "The logged target is directly "
                "correlated with a whole device "
                "that is unavailable and has no "
                "usable Recorder history."
            )
        )

    final_priority = (
        base_priority
    )

    if promotion_evidence:
        final_priority = one_level_up(
            base_priority
        )

        final_priority = cap_priority(
            final_priority,
            promotion_cap(
                priority_item
            ),
        )

    promoted = (
        priority_index(
            final_priority
        )
        > priority_index(
            base_priority
        )
    )

    if promoted:
        priority_change_basis = (
            "Independent cross-run or functional "
            "corroboration raises the snapshot "
            "priority by one level."
        )
    elif promotion_evidence:
        priority_change_basis = (
            "Promotion evidence is present, but "
            "the conservative actionability cap "
            "prevents a higher priority."
        )
    else:
        priority_change_basis = (
            "No qualifying enrichment evidence "
            "changes the snapshot priority."
        )

    recurrence_effect = (
        "PROMOTION EVIDENCE"
        if recurrence_qualifies
        else (
            "NO CHANGE - SHORT WINDOW"
            if recurrence_class
            == SHORT_WINDOW_REPEAT
            else "NO CHANGE"
        )
    )

    correlation_effect = (
        "PROMOTION EVIDENCE"
        if correlation_qualifies
        else "NO CHANGE"
    )

    repair_classification = repairs.get(
        "classification",
        NO_REPAIR_MATCH,
    )

    repair_effect = (
        "CONTEXT ONLY"
        if repair_classification
        != NO_REPAIR_MATCH
        else "NO MATCH"
    )

    return {
        "stable_fingerprint": (
            fingerprint
        ),
        "family_id": priority_item.get(
            "family_id"
        ),
        "title": priority_item.get(
            "title"
        ),
        "occurrence_count": safe_int(
            priority_item.get(
                "occurrence_count",
                0,
            )
        ),
        "ownership": priority_item.get(
            "ownership"
        ),
        "ownership_confidence": (
            priority_item.get(
                "ownership_confidence"
            )
        ),
        "local_action_path": (
            priority_item.get(
                "local_action_path"
            )
        ),
        "direct_failure_evidence": (
            priority_item.get(
                "direct_failure_evidence"
            )
        ),
        "recovery_evidence": (
            priority_item.get(
                "recovery_evidence"
            )
        ),
        "fallback_evidence": (
            priority_item.get(
                "fallback_evidence"
            )
        ),
        "snapshot_priority": (
            base_priority
        ),
        "final_priority": (
            final_priority
        ),
        "priority_changed": promoted,
        "priority_change_basis": (
            priority_change_basis
        ),
        "recurrence": {
            "class": recurrence_class,
            "observation_span_hours": (
                recurrence_item.get(
                    "recurrence_observation_span_hours"
                )
            ),
            "effect": (
                recurrence_effect
            ),
        },
        "availability_correlation": {
            "classification": (
                availability.get(
                    "classification",
                    NO_DIRECT_MATCH,
                )
            ),
            "history_classification": (
                unavailable_history.get(
                    "classification"
                )
            ),
            "effect": (
                correlation_effect
            ),
        },
        "repairs": {
            "classification": (
                repair_classification
            ),
            "unignored_match_count": (
                safe_int(
                    repairs.get(
                        "unignored_match_count",
                        0,
                    )
                )
            ),
            "ignored_match_count": (
                safe_int(
                    repairs.get(
                        "ignored_match_count",
                        0,
                    )
                )
            ),
            "effect": repair_effect,
        },
        "promotion_evidence": (
            promotion_evidence
        ),
    }


def build_report(
    priority_report,
    fingerprint_report,
    recurrence_report,
    correlation_report,
):
    generated_at = utc_now()

    (
        aligned,
        error,
        source_checks,
        alignment,
    ) = validate_alignment(
        priority_report,
        fingerprint_report,
        recurrence_report,
        correlation_report,
    )

    report = {
        "audit_version": VERSION,
        "generated_at": generated_at,
        "scope": {
            "phase": (
                "system_log_final_priority"
            ),
            "priority_input": (
                "log_priority.json"
            ),
            "fingerprint_input": (
                "log_family_fingerprints.json"
            ),
            "recurrence_input": (
                "log_recurrence.json"
            ),
            "correlation_input": (
                "log_correlation.json"
            ),
            "model": (
                "enriched_priority_v1"
            ),
            "priority_produced": False,
            "severity_produced": False,
            "action_recommendation_produced": (
                False
            ),
            "maximum_promotion_levels": 1,
            "maximum_emitted_priority": (
                MAX_EMITTED_PRIORITY
            ),
            "rules_note": (
                "The snapshot priority is never "
                "demoted by this layer. Durable "
                "24-hour recurrence or direct "
                "whole-device unavailability with "
                "no usable Recorder history can "
                "raise priority by at most one "
                "level. SHORT-WINDOW REPEAT does "
                "not raise priority. Repair-domain "
                "matches are context only. Absence "
                "of direct correlation never lowers "
                "priority."
            ),
            "very_high_note": (
                "VERY HIGH remains reserved for "
                "future corroborated critical-impact "
                "evidence and is not emitted by "
                "enriched_priority_v1."
            ),
        },
        "status": (
            "ok"
            if aligned
            else "source_misaligned"
        ),
        "error": error,
        "source_status": (
            source_checks
        ),
        "alignment": (
            alignment
        ),
        "summary": {},
        "families": [],
    }

    if not aligned:
        return report

    priority_by_family = family_map(
        priority_report.get(
            "families",
            [],
        )
    )

    correlation_by_family = family_map(
        correlation_report.get(
            "families",
            [],
        )
    )

    fingerprints = fingerprint_map(
        fingerprint_report.get(
            "families",
            [],
        )
    )

    recurrence_by_fingerprint = (
        current_recurrence_map(
            recurrence_report.get(
                "families",
                [],
            )
        )
    )

    records = []

    for family_id, priority_item in (
        priority_by_family.items()
    ):
        fingerprint = fingerprints[
            family_id
        ]

        recurrence_item = (
            recurrence_by_fingerprint[
                fingerprint
            ]
        )

        correlation_item = (
            correlation_by_family[
                family_id
            ]
        )

        records.append(
            build_family_record(
                priority_item,
                fingerprint,
                recurrence_item,
                correlation_item,
            )
        )

    records.sort(
        key=lambda item: (
            -priority_index(
                item.get(
                    "final_priority"
                )
            ),
            -priority_index(
                item.get(
                    "snapshot_priority"
                )
            ),
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
            ),
        )
    )

    report[
        "scope"
    ][
        "priority_produced"
    ] = True

    report[
        "summary"
    ] = {
        "family_count": len(
            records
        ),
        "snapshot_priority_counts": (
            priority_counts(
                records,
                "snapshot_priority",
            )
        ),
        "final_priority_counts": (
            priority_counts(
                records,
                "final_priority",
            )
        ),
        "promoted_family_count": sum(
            1
            for record in records
            if record[
                "priority_changed"
            ]
        ),
        "durable_recurrence_evidence_count": (
            sum(
                1
                for record in records
                if record[
                    "recurrence"
                ][
                    "effect"
                ]
                == "PROMOTION EVIDENCE"
            )
        ),
        "availability_promotion_evidence_count": (
            sum(
                1
                for record in records
                if record[
                    "availability_correlation"
                ][
                    "effect"
                ]
                == "PROMOTION EVIDENCE"
            )
        ),
        "short_window_no_promotion_count": (
            sum(
                1
                for record in records
                if record[
                    "recurrence"
                ][
                    "effect"
                ]
                == "NO CHANGE - SHORT WINDOW"
            )
        ),
        "repair_context_only_family_count": (
            sum(
                1
                for record in records
                if record[
                    "repairs"
                ][
                    "effect"
                ]
                == "CONTEXT ONLY"
            )
        ),
        "very_high_emitted": any(
            record[
                "final_priority"
            ]
            == "VERY HIGH"
            for record in records
        ),
    }

    report[
        "families"
    ] = records

    return report


def main():
    try:
        priority_report = load_json(
            PRIORITY_FILE
        )

        fingerprint_report = load_json(
            FINGERPRINT_FILE
        )

        recurrence_report = load_json(
            RECURRENCE_FILE
        )

        correlation_report = load_json(
            CORRELATION_FILE
        )

        report = build_report(
            priority_report,
            fingerprint_report,
            recurrence_report,
            correlation_report,
        )

    except Exception as exc:
        report = {
            "audit_version": VERSION,
            "generated_at": utc_now(),
            "scope": {
                "phase": (
                    "system_log_final_priority"
                ),
                "model": (
                    "enriched_priority_v1"
                ),
                "priority_produced": False,
                "severity_produced": False,
                "action_recommendation_produced": (
                    False
                ),
            },
            "status": "input_unavailable",
            "error": str(
                exc
            ),
            "source_status": {},
            "alignment": {},
            "summary": {},
            "families": [],
        }

    write_json(
        OUTPUT_FILE,
        report,
    )


if __name__ == "__main__":
    main()
