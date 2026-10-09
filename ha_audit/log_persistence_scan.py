import json
import os
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

FAMILY_FILE = (
    "/config/log_issue_families.json"
)

FINGERPRINT_FILE = (
    "/config/log_family_fingerprints.json"
)

PRIORITY_FILE = (
    "/config/log_priority.json"
)

HISTORY_FILE = (
    "/config/log_issue_history.json"
)

OUTPUT_FILE = (
    "/config/log_persistence.json"
)


HISTORY_SCHEMA_VERSION = 1
FINGERPRINT_SCHEMA_VERSION = 1


ACTIVITY_BASELINE = "BASELINE"
ACTIVITY_NEW = "NEW ACTIVITY"
ACTIVITY_RETAINED = "RETAINED EVIDENCE"
ACTIVITY_NOT_PRESENT = "NOT PRESENT"


PRIORITY_ORDER = (
    "VERY HIGH",
    "HIGH",
    "MEDIUM",
    "LOW",
    "VERY LOW",
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


def write_json_atomic(
    path,
    payload,
):
    temp_path = (
        f"{path}.tmp"
    )

    with open(
        temp_path,
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

        handle.flush()

        os.fsync(
            handle.fileno()
        )

    os.replace(
        temp_path,
        path,
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


def parse_timestamp(
    value,
):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(
                value
            ).replace(
                "Z",
                "+00:00",
            )
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def earlier_timestamp(
    first,
    second,
):
    first_dt = parse_timestamp(
        first
    )

    second_dt = parse_timestamp(
        second
    )

    if first_dt is None:
        return second

    if second_dt is None:
        return first

    if first_dt <= second_dt:
        return first

    return second


def priority_index(
    value,
):
    try:
        return PRIORITY_ORDER.index(
            value
        )
    except ValueError:
        return len(
            PRIORITY_ORDER
        )


def empty_history(
    created_at,
):
    return {
        "history_schema_version": (
            HISTORY_SCHEMA_VERSION
        ),
        "fingerprint_schema_version": (
            FINGERPRINT_SCHEMA_VERSION
        ),
        "created_at": created_at,
        "updated_at": created_at,
        "run_sequence": 0,
        "last_audit_version": None,
        "records": {},
    }


def validate_existing_history(
    history,
):
    if not isinstance(
        history,
        dict,
    ):
        return (
            False,
            "History root is not an object.",
        )

    if (
        safe_int(
            history.get(
                "history_schema_version",
                -1,
            )
        )
        != HISTORY_SCHEMA_VERSION
    ):
        return (
            False,
            (
                "History schema version does "
                "not match the current writer."
            ),
        )

    if (
        safe_int(
            history.get(
                "fingerprint_schema_version",
                -1,
            )
        )
        != FINGERPRINT_SCHEMA_VERSION
    ):
        return (
            False,
            (
                "Fingerprint schema version in "
                "history does not match the "
                "current fingerprint schema."
            ),
        )

    if not isinstance(
        history.get(
            "records",
            {},
        ),
        dict,
    ):
        return (
            False,
            "History records are invalid.",
        )

    return (
        True,
        None,
    )


def source_status_ok(
    family_report,
    fingerprint_report,
    priority_report,
):
    family_source = (
        family_report.get(
            "source_collection",
            {},
        )
    )

    fingerprint_source = (
        fingerprint_report.get(
            "source_collection",
            {},
        )
    )

    priority_source = (
        priority_report.get(
            "source_status",
            {},
        )
    )

    if not isinstance(
        family_source,
        dict,
    ):
        family_source = {}

    if not isinstance(
        fingerprint_source,
        dict,
    ):
        fingerprint_source = {}

    if not isinstance(
        priority_source,
        dict,
    ):
        priority_source = {}

    return (
        family_source.get(
            "status"
        )
        == "ok"
        and fingerprint_source.get(
            "status"
        )
        == "ok"
        and priority_source.get(
            "family_status"
        )
        == "ok"
        and priority_source.get(
            "ownership_status"
        )
        == "ok"
    )


def report_items_by_id(
    report,
):
    families = report.get(
        "families",
        [],
    )

    if not isinstance(
        families,
        list,
    ):
        return {}

    return {
        item.get(
            "family_id"
        ): item
        for item in families
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "family_id"
        )
    }


def alignment_details(
    family_by_id,
    fingerprint_by_id,
    priority_by_id,
):
    family_ids = set(
        family_by_id
    )

    fingerprint_ids = set(
        fingerprint_by_id
    )

    priority_ids = set(
        priority_by_id
    )

    all_ids = (
        family_ids
        | fingerprint_ids
        | priority_ids
    )

    missing_fingerprint = sorted(
        family_ids
        - fingerprint_ids
    )

    missing_priority = sorted(
        family_ids
        - priority_ids
    )

    extra_fingerprint = sorted(
        fingerprint_ids
        - family_ids
    )

    extra_priority = sorted(
        priority_ids
        - family_ids
    )

    aligned = (
        family_ids
        == fingerprint_ids
        == priority_ids
    )

    return {
        "aligned": aligned,
        "family_count": len(
            family_ids
        ),
        "combined_id_count": len(
            all_ids
        ),
        "missing_fingerprint_family_ids": (
            missing_fingerprint
        ),
        "missing_priority_family_ids": (
            missing_priority
        ),
        "extra_fingerprint_family_ids": (
            extra_fingerprint
        ),
        "extra_priority_family_ids": (
            extra_priority
        ),
    }


def duplicate_fingerprint_count(
    fingerprint_report,
):
    summary = fingerprint_report.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        return -1

    return safe_int(
        summary.get(
            "duplicate_fingerprint_group_count",
            -1,
        )
    )


def fingerprint_schema_version(
    fingerprint_report,
):
    scope = fingerprint_report.get(
        "scope",
        {},
    )

    if not isinstance(
        scope,
        dict,
    ):
        return -1

    return safe_int(
        scope.get(
            "fingerprint_schema_version",
            -1,
        )
    )


def evidence_advanced(
    previous_record,
    family,
):
    previous_last_seen = (
        previous_record.get(
            "last_log_seen"
        )
    )

    current_last_seen = family.get(
        "last_seen"
    )

    previous_dt = parse_timestamp(
        previous_last_seen
    )

    current_dt = parse_timestamp(
        current_last_seen
    )

    if (
        previous_dt is not None
        and current_dt is not None
        and current_dt > previous_dt
    ):
        return True

    previous_count = safe_int(
        previous_record.get(
            "latest_occurrence_count",
            0,
        )
    )

    current_count = safe_int(
        family.get(
            "occurrence_count",
            0,
        )
    )

    if (
        previous_dt == current_dt
        and current_count
        > previous_count
    ):
        return True

    return False


def new_history_record(
    fingerprint,
    fingerprint_item,
    family,
    priority,
    run_at,
    run_sequence,
):
    return {
        "stable_fingerprint": (
            fingerprint
        ),
        "fingerprint_method": (
            fingerprint_item.get(
                "fingerprint_method"
            )
        ),
        "latest_family_id": (
            family.get(
                "family_id"
            )
        ),
        "title": family.get(
            "title"
        ),
        "first_audit_seen": run_at,
        "last_audit_seen": run_at,
        "last_seen_run_sequence": (
            run_sequence
        ),
        "audit_appearances": 1,
        "consecutive_audit_appearances": 1,
        "missed_audits_since_seen": 0,
        "repeat_activity_audits": 0,
        "consecutive_new_activity_audits": 0,
        "last_activity_status": (
            ACTIVITY_BASELINE
        ),
        "first_log_seen": family.get(
            "first_seen"
        ),
        "last_log_seen": family.get(
            "last_seen"
        ),
        "latest_occurrence_count": (
            safe_int(
                family.get(
                    "occurrence_count",
                    0,
                )
            )
        ),
        "latest_priority": priority.get(
            "priority"
        ),
        "seen_in_latest_audit": True,
    }


def update_history_record(
    previous_record,
    fingerprint_item,
    family,
    priority,
    run_at,
    run_sequence,
    previous_run_sequence,
):
    record = dict(
        previous_record
    )

    seen_previous_run = (
        safe_int(
            previous_record.get(
                "last_seen_run_sequence",
                -1,
            )
        )
        == previous_run_sequence
    )

    if seen_previous_run:
        consecutive_appearances = (
            safe_int(
                previous_record.get(
                    "consecutive_audit_appearances",
                    0,
                )
            )
            + 1
        )
    else:
        consecutive_appearances = 1

    new_activity = evidence_advanced(
        previous_record,
        family,
    )

    if new_activity:
        activity_status = (
            ACTIVITY_NEW
        )

        repeat_activity_audits = (
            safe_int(
                previous_record.get(
                    "repeat_activity_audits",
                    0,
                )
            )
            + 1
        )

        if (
            seen_previous_run
            and previous_record.get(
                "last_activity_status"
            )
            == ACTIVITY_NEW
        ):
            consecutive_new_activity = (
                safe_int(
                    previous_record.get(
                        "consecutive_new_activity_audits",
                        0,
                    )
                )
                + 1
            )
        else:
            consecutive_new_activity = 1
    else:
        activity_status = (
            ACTIVITY_RETAINED
        )

        repeat_activity_audits = (
            safe_int(
                previous_record.get(
                    "repeat_activity_audits",
                    0,
                )
            )
        )

        consecutive_new_activity = 0

    record.update(
        {
            "fingerprint_method": (
                fingerprint_item.get(
                    "fingerprint_method"
                )
            ),
            "latest_family_id": (
                family.get(
                    "family_id"
                )
            ),
            "title": family.get(
                "title"
            ),
            "last_audit_seen": run_at,
            "last_seen_run_sequence": (
                run_sequence
            ),
            "audit_appearances": (
                safe_int(
                    previous_record.get(
                        "audit_appearances",
                        0,
                    )
                )
                + 1
            ),
            "consecutive_audit_appearances": (
                consecutive_appearances
            ),
            "missed_audits_since_seen": 0,
            "repeat_activity_audits": (
                repeat_activity_audits
            ),
            "consecutive_new_activity_audits": (
                consecutive_new_activity
            ),
            "last_activity_status": (
                activity_status
            ),
            "first_log_seen": (
                earlier_timestamp(
                    previous_record.get(
                        "first_log_seen"
                    ),
                    family.get(
                        "first_seen"
                    ),
                )
            ),
            "last_log_seen": family.get(
                "last_seen"
            ),
            "latest_occurrence_count": (
                safe_int(
                    family.get(
                        "occurrence_count",
                        0,
                    )
                )
            ),
            "latest_priority": (
                priority.get(
                    "priority"
                )
            ),
            "seen_in_latest_audit": True,
        }
    )

    return record


def mark_not_present(
    previous_record,
):
    record = dict(
        previous_record
    )

    record[
        "seen_in_latest_audit"
    ] = False

    record[
        "missed_audits_since_seen"
    ] = (
        safe_int(
            previous_record.get(
                "missed_audits_since_seen",
                0,
            )
        )
        + 1
    )

    record[
        "consecutive_audit_appearances"
    ] = 0

    record[
        "consecutive_new_activity_audits"
    ] = 0

    record[
        "last_activity_status"
    ] = (
        ACTIVITY_NOT_PRESENT
    )

    return record


def current_report_record(
    history_record,
):
    return {
        "stable_fingerprint": (
            history_record.get(
                "stable_fingerprint"
            )
        ),
        "family_id": (
            history_record.get(
                "latest_family_id"
            )
        ),
        "title": history_record.get(
            "title"
        ),
        "priority": (
            history_record.get(
                "latest_priority"
            )
        ),
        "activity_since_previous_audit": (
            history_record.get(
                "last_activity_status"
            )
        ),
        "audit_appearances": (
            history_record.get(
                "audit_appearances"
            )
        ),
        "consecutive_audit_appearances": (
            history_record.get(
                "consecutive_audit_appearances"
            )
        ),
        "repeat_activity_audits": (
            history_record.get(
                "repeat_activity_audits"
            )
        ),
        "consecutive_new_activity_audits": (
            history_record.get(
                "consecutive_new_activity_audits"
            )
        ),
        "latest_occurrence_count": (
            history_record.get(
                "latest_occurrence_count"
            )
        ),
        "first_audit_seen": (
            history_record.get(
                "first_audit_seen"
            )
        ),
        "last_audit_seen": (
            history_record.get(
                "last_audit_seen"
            )
        ),
    }


def failure_report(
    run_at,
    status,
    error,
    alignment=None,
):
    return {
        "audit_version": VERSION,
        "generated_at": run_at,
        "scope": {
            "phase": (
                "system_log_persistence_probe"
            ),
            "history_schema_version": (
                HISTORY_SCHEMA_VERSION
            ),
            "fingerprint_schema_version": (
                FINGERPRINT_SCHEMA_VERSION
            ),
            "history_written": False,
            "persistence_judgement_produced": (
                False
            ),
            "priority_changed": False,
        },
        "status": status,
        "error": error,
        "alignment": alignment or {},
        "summary": {},
        "families": [],
    }


def build_update(
    family_report,
    fingerprint_report,
    priority_report,
    existing_history=None,
    run_at=None,
):
    if run_at is None:
        run_at = utc_now()

    if not source_status_ok(
        family_report,
        fingerprint_report,
        priority_report,
    ):
        return (
            None,
            failure_report(
                run_at,
                "source_incomplete",
                (
                    "One or more source reports "
                    "are incomplete."
                ),
            ),
            False,
        )

    if (
        fingerprint_schema_version(
            fingerprint_report
        )
        != FINGERPRINT_SCHEMA_VERSION
    ):
        return (
            None,
            failure_report(
                run_at,
                (
                    "fingerprint_schema_mismatch"
                ),
                (
                    "Fingerprint report schema "
                    "does not match the history "
                    "writer."
                ),
            ),
            False,
        )

    if (
        duplicate_fingerprint_count(
            fingerprint_report
        )
        != 0
    ):
        return (
            None,
            failure_report(
                run_at,
                (
                    "duplicate_fingerprints"
                ),
                (
                    "Current fingerprint report "
                    "contains duplicate stable "
                    "fingerprints."
                ),
            ),
            False,
        )

    family_by_id = report_items_by_id(
        family_report
    )

    fingerprint_by_id = (
        report_items_by_id(
            fingerprint_report
        )
    )

    priority_by_id = report_items_by_id(
        priority_report
    )

    alignment = alignment_details(
        family_by_id,
        fingerprint_by_id,
        priority_by_id,
    )

    if not alignment[
        "aligned"
    ]:
        return (
            None,
            failure_report(
                run_at,
                "alignment_error",
                (
                    "Family, fingerprint and "
                    "priority reports do not "
                    "contain the same family IDs."
                ),
                alignment,
            ),
            False,
        )

    if existing_history is None:
        history = empty_history(
            run_at
        )
    else:
        (
            valid_history,
            history_error,
        ) = validate_existing_history(
            existing_history
        )

        if not valid_history:
            return (
                None,
                failure_report(
                    run_at,
                    "history_invalid",
                    history_error,
                    alignment,
                ),
                False,
            )

        history = dict(
            existing_history
        )

        history[
            "records"
        ] = dict(
            existing_history.get(
                "records",
                {},
            )
        )

    previous_run_sequence = (
        safe_int(
            history.get(
                "run_sequence",
                0,
            )
        )
    )

    run_sequence = (
        previous_run_sequence
        + 1
    )

    previous_records = history.get(
        "records",
        {},
    )

    new_records = {
        fingerprint: (
            mark_not_present(
                record
            )
        )
        for (
            fingerprint,
            record,
        ) in previous_records.items()
        if isinstance(
            record,
            dict,
        )
    }

    current_records = []

    for family_id in sorted(
        family_by_id
    ):
        family = family_by_id[
            family_id
        ]

        fingerprint_item = (
            fingerprint_by_id[
                family_id
            ]
        )

        priority = priority_by_id[
            family_id
        ]

        fingerprint = (
            fingerprint_item.get(
                "stable_fingerprint"
            )
        )

        if not fingerprint:
            return (
                None,
                failure_report(
                    run_at,
                    (
                        "missing_fingerprint"
                    ),
                    (
                        "A current family does not "
                        "have a stable fingerprint."
                    ),
                    alignment,
                ),
                False,
            )

        previous_record = (
            previous_records.get(
                fingerprint
            )
        )

        if isinstance(
            previous_record,
            dict,
        ):
            record = (
                update_history_record(
                    previous_record,
                    fingerprint_item,
                    family,
                    priority,
                    run_at,
                    run_sequence,
                    previous_run_sequence,
                )
            )
        else:
            record = (
                new_history_record(
                    fingerprint,
                    fingerprint_item,
                    family,
                    priority,
                    run_at,
                    run_sequence,
                )
            )

        new_records[
            fingerprint
        ] = record

        current_records.append(
            current_report_record(
                record
            )
        )

    history.update(
        {
            "history_schema_version": (
                HISTORY_SCHEMA_VERSION
            ),
            "fingerprint_schema_version": (
                FINGERPRINT_SCHEMA_VERSION
            ),
            "updated_at": run_at,
            "run_sequence": (
                run_sequence
            ),
            "last_audit_version": VERSION,
            "records": new_records,
        }
    )

    current_records.sort(
        key=lambda item: (
            priority_index(
                item.get(
                    "priority"
                )
            ),
            -safe_int(
                item.get(
                    "repeat_activity_audits",
                    0,
                )
            ),
            -safe_int(
                item.get(
                    "latest_occurrence_count",
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

    report = {
        "audit_version": VERSION,
        "generated_at": run_at,
        "scope": {
            "phase": (
                "system_log_persistence_probe"
            ),
            "family_input": (
                "log_issue_families.json"
            ),
            "fingerprint_input": (
                "log_family_fingerprints.json"
            ),
            "priority_input": (
                "log_priority.json"
            ),
            "history_file": (
                "log_issue_history.json"
            ),
            "history_schema_version": (
                HISTORY_SCHEMA_VERSION
            ),
            "fingerprint_schema_version": (
                FINGERPRINT_SCHEMA_VERSION
            ),
            "history_written": False,
            "persistence_judgement_produced": (
                False
            ),
            "priority_changed": False,
            "activity_note": (
                "NEW ACTIVITY requires log "
                "evidence to advance since the "
                "previous audit. Merely retaining "
                "the same System Log evidence does "
                "not count as recurrence."
            ),
            "privacy_note": (
                "History stores stable hashes and "
                "small derived counters only. Raw "
                "messages, source traces, IP "
                "addresses and entity lists are "
                "not stored."
            ),
        },
        "status": "ok",
        "error": None,
        "alignment": alignment,
        "summary": {
            "run_sequence": (
                run_sequence
            ),
            "current_family_count": len(
                current_records
            ),
            "history_record_count": len(
                new_records
            ),
            "baseline_family_count": sum(
                1
                for item in current_records
                if item[
                    "activity_since_previous_audit"
                ]
                == ACTIVITY_BASELINE
            ),
            "new_activity_family_count": sum(
                1
                for item in current_records
                if item[
                    "activity_since_previous_audit"
                ]
                == ACTIVITY_NEW
            ),
            "retained_evidence_family_count": sum(
                1
                for item in current_records
                if item[
                    "activity_since_previous_audit"
                ]
                == ACTIVITY_RETAINED
            ),
            "not_present_history_count": sum(
                1
                for item in new_records.values()
                if not item.get(
                    "seen_in_latest_audit",
                    False,
                )
            ),
        },
        "families": current_records,
    }

    return (
        history,
        report,
        True,
    )


def main():
    run_at = utc_now()

    try:
        family_report = load_json(
            FAMILY_FILE
        )

        fingerprint_report = (
            load_json(
                FINGERPRINT_FILE
            )
        )

        priority_report = load_json(
            PRIORITY_FILE
        )
    except Exception as exc:
        report = failure_report(
            run_at,
            "input_unavailable",
            str(
                exc
            ),
        )

        write_json_atomic(
            OUTPUT_FILE,
            report,
        )

        return

    existing_history = None

    if os.path.exists(
        HISTORY_FILE
    ):
        try:
            existing_history = (
                load_json(
                    HISTORY_FILE
                )
            )
        except Exception as exc:
            report = failure_report(
                run_at,
                "history_unreadable",
                str(
                    exc
                ),
            )

            write_json_atomic(
                OUTPUT_FILE,
                report,
            )

            return

    (
        history,
        report,
        write_ready,
    ) = build_update(
        family_report,
        fingerprint_report,
        priority_report,
        existing_history,
        run_at,
    )

    if write_ready:
        try:
            write_json_atomic(
                HISTORY_FILE,
                history,
            )

            report[
                "scope"
            ][
                "history_written"
            ] = True
        except Exception as exc:
            report[
                "status"
            ] = "history_write_failed"

            report[
                "error"
            ] = str(
                exc
            )

    write_json_atomic(
        OUTPUT_FILE,
        report,
    )


if __name__ == "__main__":
    main()
