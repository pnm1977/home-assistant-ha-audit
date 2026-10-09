import json
import os
import re
from collections import Counter
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

PRIORITY_EVIDENCE_FILE = (
    "/config/log_priority_evidence.json"
)

AVAILABILITY_FILE = (
    "/config/availability_audit.json"
)

UNAVAILABLE_HISTORY_FILE = (
    "/config/unavailable_history_audit.json"
)

UPDATE_READINESS_FILE = (
    "/config/update_readiness_audit.json"
)

OUTPUT_FILE = (
    "/config/log_correlation.json"
)


NO_DIRECT_MATCH = (
    "NO DIRECT MATCH"
)

DIRECT_WHOLE_DEVICE = (
    "DIRECT WHOLE-DEVICE UNAVAILABLE"
)

DIRECT_PARTIAL = (
    "DIRECT PARTIAL AVAILABILITY"
)

DIRECT_UNAVAILABLE = (
    "DIRECT UNAVAILABLE ENTITY"
)


HISTORY_NOT_APPLICABLE = (
    "NOT APPLICABLE"
)

HISTORY_NO_USABLE = (
    "NO USABLE HISTORY OBSERVED"
)

HISTORY_USABLE = (
    "USABLE HISTORY OBSERVED"
)

HISTORY_NONE_RETURNED = (
    "NO HISTORY RETURNED"
)

HISTORY_QUERY_FAILED = (
    "HISTORY QUERY FAILED"
)

HISTORY_SOURCE_UNAVAILABLE = (
    "HISTORY SOURCE UNAVAILABLE"
)

HISTORY_MIXED = (
    "MIXED / UNKNOWN"
)


NO_REPAIR_MATCH = (
    "NO DOMAIN MATCH"
)

IGNORED_REPAIR_MATCH = (
    "IGNORED DOMAIN MATCH"
)

UNIGNORED_REPAIR_MATCH = (
    "UNIGNORED DOMAIN MATCH"
)


CORRELATION_NONE = (
    "NO DIRECT CORRELATION"
)

CORRELATION_AVAILABILITY = (
    "DIRECT AVAILABILITY CORRELATION"
)

CORRELATION_REPAIR = (
    "REPAIR DOMAIN CONTEXT"
)


ENTITY_ID_RE = re.compile(
    r"^[a-z0-9_]+\.[a-z0-9_]+$"
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


def clean_text(
    value,
):
    return " ".join(
        str(
            value or ""
        ).split()
    )


def is_entity_id(
    value,
):
    return bool(
        ENTITY_ID_RE.fullmatch(
            clean_text(
                value
            ).lower()
        )
    )


def priority_source_ok(
    report,
):
    source_status = report.get(
        "source_status",
        {},
    )

    if not isinstance(
        source_status,
        dict,
    ):
        return False

    return (
        source_status.get(
            "family_status"
        )
        == "ok"
        and source_status.get(
            "ownership_status"
        )
        == "ok"
    )


def availability_source_ok(
    report,
):
    return (
        isinstance(
            report,
            dict,
        )
        and isinstance(
            report.get(
                "entities"
            ),
            list,
        )
        and bool(
            report.get(
                "states_observed_at"
            )
        )
    )


def history_source_state(
    availability_report,
    history_report,
):
    if not isinstance(
        history_report,
        dict,
    ):
        return {
            "available": False,
            "aligned": False,
            "recorder_status": "unknown",
            "reason": (
                "Unavailable-history report "
                "is not valid."
            ),
        }

    policy = history_report.get(
        "history_policy",
        {},
    )

    if not isinstance(
        policy,
        dict,
    ):
        policy = {}

    recorder_status = policy.get(
        "recorder_status",
        "unknown",
    )

    availability_time = (
        availability_report.get(
            "states_observed_at"
        )
    )

    history_time = (
        history_report.get(
            "source_availability_observed_at"
        )
    )

    aligned = (
        bool(
            availability_time
        )
        and availability_time
        == history_time
    )

    entities_valid = isinstance(
        history_report.get(
            "entities"
        ),
        list,
    )

    available = (
        aligned
        and entities_valid
        and recorder_status == "ok"
    )

    if not aligned:
        reason = (
            "Unavailable-history evidence "
            "does not reference the current "
            "availability snapshot."
        )
    elif recorder_status != "ok":
        reason = (
            "Recorder history collection "
            "was not healthy."
        )
    elif not entities_valid:
        reason = (
            "Unavailable-history entity "
            "evidence is unavailable."
        )
    else:
        reason = None

    return {
        "available": available,
        "aligned": aligned,
        "recorder_status": (
            recorder_status
        ),
        "reason": reason,
    }


def repairs_source_ok(
    report,
):
    repairs = report.get(
        "repairs",
        {},
    )

    return (
        isinstance(
            repairs,
            dict,
        )
        and isinstance(
            repairs.get(
                "issues"
            ),
            list,
        )
    )


def items_by_entity_id(
    items,
):
    result = {}

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        entity_id = clean_text(
            item.get(
                "entity_id"
            )
        ).lower()

        if not entity_id:
            continue

        result[
            entity_id
        ] = item

    return result


def family_entity_identifiers(
    family,
):
    identifiers = family.get(
        "observed_identifiers",
        [],
    )

    if not isinstance(
        identifiers,
        list,
    ):
        return []

    return sorted(
        {
            clean_text(
                value
            ).lower()
            for value in identifiers
            if is_entity_id(
                value
            )
        }
    )


def history_classification(
    matches,
    history_available,
):
    if not matches:
        return (
            HISTORY_NOT_APPLICABLE
        )

    if not history_available:
        return (
            HISTORY_SOURCE_UNAVAILABLE
        )

    statuses = [
        match.get(
            "history_status"
        )
        for match in matches
        if match.get(
            "history_status"
        )
    ]

    if not statuses:
        return HISTORY_MIXED

    if (
        "history_query_failed"
        in statuses
    ):
        return (
            HISTORY_QUERY_FAILED
        )

    if (
        "usable_history_found"
        in statuses
    ):
        return (
            HISTORY_USABLE
        )

    if all(
        status
        == "history_found_no_usable_state"
        for status in statuses
    ):
        return (
            HISTORY_NO_USABLE
        )

    if (
        "no_history_returned"
        in statuses
    ):
        return (
            HISTORY_NONE_RETURNED
        )

    return HISTORY_MIXED


def availability_classification(
    matches,
):
    if not matches:
        return NO_DIRECT_MATCH

    classifications = {
        match.get(
            "classification"
        )
        for match in matches
    }

    if any(
        str(
            value or ""
        ).startswith(
            "whole_device_unavailable"
        )
        for value in classifications
    ):
        return (
            DIRECT_WHOLE_DEVICE
        )

    if (
        "partial_availability"
        in classifications
    ):
        return DIRECT_PARTIAL

    return DIRECT_UNAVAILABLE


def build_availability_matches(
    family,
    availability_by_entity,
    history_by_entity,
    history_available,
):
    matches = []

    for entity_id in (
        family_entity_identifiers(
            family
        )
    ):
        availability = (
            availability_by_entity.get(
                entity_id
            )
        )

        if not isinstance(
            availability,
            dict,
        ):
            continue

        history = (
            history_by_entity.get(
                entity_id
            )
            if history_available
            else None
        )

        if not isinstance(
            history,
            dict,
        ):
            history = {}

        matches.append(
            {
                "entity_id": (
                    entity_id
                ),
                "platform": (
                    availability.get(
                        "platform"
                    )
                ),
                "device": (
                    availability.get(
                        "device"
                    )
                ),
                "classification": (
                    availability.get(
                        "classification"
                    )
                ),
                "labels": (
                    availability.get(
                        "labels",
                        [],
                    )
                ),
                "history_status": (
                    history.get(
                        "history_status"
                    )
                    if history_available
                    else None
                ),
                "last_usable_state_started_at": (
                    history.get(
                        "last_usable_state_started_at"
                    )
                    if history_available
                    else None
                ),
                "last_usable_state_ended_at": (
                    history.get(
                        "last_usable_state_ended_at"
                    )
                    if history_available
                    else None
                ),
            }
        )

    return matches


def repair_matches(
    family,
    repairs,
):
    family_id = clean_text(
        family.get(
            "family_id"
        )
    ).lower()

    if not family_id:
        return []

    matches = []

    for repair in repairs:
        if not isinstance(
            repair,
            dict,
        ):
            continue

        domain = clean_text(
            repair.get(
                "domain"
            )
        ).lower()

        issue_domain = clean_text(
            repair.get(
                "issue_domain"
            )
        ).lower()

        if family_id not in {
            domain,
            issue_domain,
        }:
            continue

        matches.append(
            {
                "domain": repair.get(
                    "domain"
                ),
                "severity": (
                    repair.get(
                        "severity"
                    )
                ),
                "ignored": bool(
                    repair.get(
                        "ignored",
                        False,
                    )
                ),
                "is_fixable": (
                    repair.get(
                        "is_fixable"
                    )
                ),
                "translation_key": (
                    repair.get(
                        "translation_key"
                    )
                ),
                "upgrade_relevance": (
                    repair.get(
                        "upgrade_relevance"
                    )
                ),
            }
        )

    return matches


def repair_classification(
    matches,
):
    if not matches:
        return NO_REPAIR_MATCH

    if any(
        not match.get(
            "ignored",
            False,
        )
        for match in matches
    ):
        return (
            UNIGNORED_REPAIR_MATCH
        )

    return IGNORED_REPAIR_MATCH


def correlation_classification(
    availability_class,
    repair_class,
):
    if (
        availability_class
        != NO_DIRECT_MATCH
    ):
        return (
            CORRELATION_AVAILABILITY
        )

    if (
        repair_class
        != NO_REPAIR_MATCH
    ):
        return CORRELATION_REPAIR

    return CORRELATION_NONE


def build_family_record(
    family,
    availability_by_entity,
    history_by_entity,
    history_state,
    repairs,
):
    availability_matches = (
        build_availability_matches(
            family,
            availability_by_entity,
            history_by_entity,
            history_state[
                "available"
            ],
        )
    )

    availability_class = (
        availability_classification(
            availability_matches
        )
    )

    history_class = (
        history_classification(
            availability_matches,
            history_state[
                "available"
            ],
        )
    )

    matched_repairs = repair_matches(
        family,
        repairs,
    )

    repair_class = (
        repair_classification(
            matched_repairs
        )
    )

    history_status_counts = dict(
        Counter(
            match.get(
                "history_status"
            )
            for match
            in availability_matches
            if match.get(
                "history_status"
            )
        )
    )

    return {
        "family_id": family.get(
            "family_id"
        ),
        "title": family.get(
            "title"
        ),
        "occurrence_count": safe_int(
            family.get(
                "occurrence_count",
                0,
            )
        ),
        "ownership": family.get(
            "ownership"
        ),
        "local_action_path": (
            family.get(
                "local_action_path"
            )
        ),
        "correlation_class": (
            correlation_classification(
                availability_class,
                repair_class,
            )
        ),
        "availability": {
            "classification": (
                availability_class
            ),
            "exact_entity_match_count": (
                len(
                    availability_matches
                )
            ),
            "matches": (
                availability_matches
            ),
        },
        "unavailable_history": {
            "classification": (
                history_class
            ),
            "status_counts": (
                history_status_counts
            ),
        },
        "repairs": {
            "classification": (
                repair_class
            ),
            "exact_domain_match_count": (
                len(
                    matched_repairs
                )
            ),
            "unignored_match_count": (
                sum(
                    1
                    for match
                    in matched_repairs
                    if not match.get(
                        "ignored",
                        False,
                    )
                )
            ),
            "ignored_match_count": (
                sum(
                    1
                    for match
                    in matched_repairs
                    if match.get(
                        "ignored",
                        False,
                    )
                )
            ),
            "matches": matched_repairs,
            "match_basis": (
                "Exact Home Assistant Repair "
                "domain match only. A domain "
                "match does not prove the Repair "
                "and System Log family have the "
                "same root cause."
            ),
        },
    }


def build_report(
    priority_report,
    availability_report,
    history_report,
    update_report,
):
    generated_at = utc_now()

    priority_ok = (
        priority_source_ok(
            priority_report
        )
    )

    availability_ok = (
        availability_source_ok(
            availability_report
        )
    )

    repairs_ok = (
        repairs_source_ok(
            update_report
        )
    )

    if not (
        priority_ok
        and availability_ok
        and repairs_ok
    ):
        return {
            "audit_version": VERSION,
            "generated_at": generated_at,
            "scope": {
                "phase": (
                    "system_log_correlation_probe"
                ),
                "correlation_produced": False,
                "priority_changed": False,
                "action_recommendation_produced": (
                    False
                ),
            },
            "status": "source_incomplete",
            "error": (
                "One or more required source "
                "reports are incomplete."
            ),
            "source_status": {
                "priority_evidence": (
                    priority_ok
                ),
                "availability": (
                    availability_ok
                ),
                "repairs": repairs_ok,
            },
            "summary": {},
            "families": [],
        }

    history_state = (
        history_source_state(
            availability_report,
            history_report,
        )
    )

    availability_by_entity = (
        items_by_entity_id(
            availability_report.get(
                "entities",
                [],
            )
        )
    )

    history_by_entity = {}

    if history_state[
        "available"
    ]:
        history_by_entity = (
            items_by_entity_id(
                history_report.get(
                    "entities",
                    [],
                )
            )
        )

    repairs = (
        update_report.get(
            "repairs",
            {},
        ).get(
            "issues",
            [],
        )
    )

    families = priority_report.get(
        "families",
        [],
    )

    if not isinstance(
        families,
        list,
    ):
        families = []

    records = [
        build_family_record(
            family,
            availability_by_entity,
            history_by_entity,
            history_state,
            repairs,
        )
        for family in families
        if isinstance(
            family,
            dict,
        )
    ]

    records.sort(
        key=lambda item: (
            0
            if item[
                "correlation_class"
            ]
            == CORRELATION_AVAILABILITY
            else (
                1
                if item[
                    "correlation_class"
                ]
                == CORRELATION_REPAIR
                else 2
            ),
            -safe_int(
                item.get(
                    "occurrence_count",
                    0,
                )
            ),
            str(
                item.get(
                    "family_id",
                    "",
                )
            ),
        )
    )

    direct_availability = [
        record
        for record in records
        if record[
            "availability"
        ][
            "classification"
        ]
        != NO_DIRECT_MATCH
    ]

    repair_context = [
        record
        for record in records
        if record[
            "repairs"
        ][
            "classification"
        ]
        != NO_REPAIR_MATCH
    ]

    status = (
        "ok"
        if history_state[
            "available"
        ]
        else "partial"
    )

    return {
        "audit_version": VERSION,
        "generated_at": generated_at,
        "scope": {
            "phase": (
                "system_log_correlation_probe"
            ),
            "priority_input": (
                "log_priority_evidence.json"
            ),
            "availability_input": (
                "availability_audit.json"
            ),
            "unavailable_history_input": (
                "unavailable_history_audit.json"
            ),
            "repairs_input": (
                "update_readiness_audit.json"
            ),
            "correlation_produced": True,
            "priority_changed": False,
            "action_recommendation_produced": (
                False
            ),
            "availability_match_note": (
                "Availability correlation uses "
                "exact entity IDs already observed "
                "in the System Log family. Absence "
                "of a match does not prove the "
                "target is healthy."
            ),
            "repair_match_note": (
                "Repair correlation uses exact "
                "Home Assistant domain equality. "
                "It is contextual evidence only "
                "and does not prove the Repair is "
                "the same underlying fault."
            ),
            "privacy_note": (
                "Repair issue IDs, URLs, "
                "translation placeholders, IP "
                "addresses and raw System Log "
                "messages are not copied into "
                "this report."
            ),
        },
        "status": status,
        "error": (
            None
            if status == "ok"
            else history_state[
                "reason"
            ]
        ),
        "source_status": {
            "priority_evidence": True,
            "availability": True,
            "repairs": True,
            "unavailable_history": (
                history_state
            ),
        },
        "summary": {
            "family_count": len(
                records
            ),
            "direct_availability_family_count": (
                len(
                    direct_availability
                )
            ),
            "direct_unavailable_entity_match_count": (
                sum(
                    record[
                        "availability"
                    ][
                        "exact_entity_match_count"
                    ]
                    for record
                    in direct_availability
                )
            ),
            "whole_device_unavailable_match_count": (
                sum(
                    1
                    for record
                    in direct_availability
                    for match
                    in record[
                        "availability"
                    ][
                        "matches"
                    ]
                    if str(
                        match.get(
                            "classification",
                            "",
                        )
                    ).startswith(
                        "whole_device_unavailable"
                    )
                )
            ),
            "no_usable_history_match_count": (
                sum(
                    record[
                        "unavailable_history"
                    ][
                        "status_counts"
                    ].get(
                        "history_found_no_usable_state",
                        0,
                    )
                    for record
                    in direct_availability
                )
            ),
            "repair_domain_family_count": (
                len(
                    repair_context
                )
            ),
            "matched_repair_count": (
                sum(
                    record[
                        "repairs"
                    ][
                        "exact_domain_match_count"
                    ]
                    for record
                    in repair_context
                )
            ),
            "unignored_repair_match_count": (
                sum(
                    record[
                        "repairs"
                    ][
                        "unignored_match_count"
                    ]
                    for record
                    in repair_context
                )
            ),
            "ignored_repair_match_count": (
                sum(
                    record[
                        "repairs"
                    ][
                        "ignored_match_count"
                    ]
                    for record
                    in repair_context
                )
            ),
            "priority_changed": False,
        },
        "families": records,
    }


def main():
    try:
        priority_report = load_json(
            PRIORITY_EVIDENCE_FILE
        )

        availability_report = load_json(
            AVAILABILITY_FILE
        )

        history_report = load_json(
            UNAVAILABLE_HISTORY_FILE
        )

        update_report = load_json(
            UPDATE_READINESS_FILE
        )

        report = build_report(
            priority_report,
            availability_report,
            history_report,
            update_report,
        )

    except Exception as exc:
        report = {
            "audit_version": VERSION,
            "generated_at": utc_now(),
            "scope": {
                "phase": (
                    "system_log_correlation_probe"
                ),
                "correlation_produced": False,
                "priority_changed": False,
                "action_recommendation_produced": (
                    False
                ),
            },
            "status": "input_unavailable",
            "error": str(
                exc
            ),
            "summary": {},
            "families": [],
        }

    write_json(
        OUTPUT_FILE,
        report,
    )


if __name__ == "__main__":
    main()
