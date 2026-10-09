import json
import os
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

INPUT_FILE = (
    "/config/log_issue_history.json"
)

PERSISTENCE_FILE = (
    "/config/log_persistence.json"
)

OUTPUT_FILE = (
    "/config/log_recurrence.json"
)


SUPPORTED_HISTORY_SCHEMA_VERSION = 1
SUPPORTED_FINGERPRINT_SCHEMA_VERSION = 1

RECURRENCE_HOURS = 24.0


NOT_ESTABLISHED = (
    "NOT ESTABLISHED"
)

SHORT_WINDOW_REPEAT = (
    "SHORT-WINDOW REPEAT"
)

RECURRING_24H = (
    "RECURRING 24H+"
)

REPEAT_SPAN_UNKNOWN = (
    "REPEAT SPAN UNKNOWN"
)


CLASS_ORDER = (
    RECURRING_24H,
    SHORT_WINDOW_REPEAT,
    REPEAT_SPAN_UNKNOWN,
    NOT_ESTABLISHED,
)


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


def hours_between(
    first,
    second,
):
    first_dt = parse_timestamp(
        first
    )

    second_dt = parse_timestamp(
        second
    )

    if (
        first_dt is None
        or second_dt is None
    ):
        return None

    seconds = (
        second_dt
        - first_dt
    ).total_seconds()

    if seconds < 0:
        return None

    return round(
        seconds / 3600.0,
        2,
    )


def recurrence_class(
    record,
):
    repeat_count = safe_int(
        record.get(
            "repeat_activity_audits",
            0,
        )
    )

    if repeat_count <= 0:
        return (
            NOT_ESTABLISHED,
            None,
        )

    span_hours = hours_between(
        record.get(
            "first_audit_seen"
        ),
        record.get(
            "last_repeat_activity_at"
        ),
    )

    if span_hours is None:
        return (
            REPEAT_SPAN_UNKNOWN,
            None,
        )

    if span_hours >= RECURRENCE_HOURS:
        return (
            RECURRING_24H,
            span_hours,
        )

    return (
        SHORT_WINDOW_REPEAT,
        span_hours,
    )


def recurrence_basis(
    recurrence,
    repeat_count,
    span_hours,
):
    if recurrence == NOT_ESTABLISHED:
        return (
            "No independently observed new "
            "activity has occurred after the "
            "baseline audit. Repeated visibility "
            "of retained System Log evidence does "
            "not establish recurrence."
        )

    if recurrence == SHORT_WINDOW_REPEAT:
        return (
            "New activity has been observed after "
            "the baseline audit, but the observation "
            f"window is only {span_hours:.2f} hours. "
            "This is not treated as durable "
            "recurrence."
        )

    if recurrence == RECURRING_24H:
        return (
            "New activity has been observed after "
            "the baseline audit across an observation "
            f"window of {span_hours:.2f} hours. "
            "This provides cross-run recurrence "
            "evidence."
        )

    return (
        f"{repeat_count} repeat-activity audit(s) "
        "are recorded, but the observation span "
        "cannot be established reliably."
    )


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


def class_index(
    value,
):
    try:
        return CLASS_ORDER.index(
            value
        )
    except ValueError:
        return len(
            CLASS_ORDER
        )


def validate_history(
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
        != SUPPORTED_HISTORY_SCHEMA_VERSION
    ):
        return (
            False,
            (
                "Unsupported history schema "
                "version."
            ),
        )

    if (
        safe_int(
            history.get(
                "fingerprint_schema_version",
                -1,
            )
        )
        != SUPPORTED_FINGERPRINT_SCHEMA_VERSION
    ):
        return (
            False,
            (
                "Unsupported fingerprint schema "
                "version."
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


def validate_current_persistence(
    history,
    persistence,
):
    if not isinstance(
        persistence,
        dict,
    ):
        return (
            False,
            "Persistence report is not an object.",
        )

    if persistence.get(
        "status"
    ) != "ok":
        return (
            False,
            (
                "Current persistence stage did not "
                "complete successfully."
            ),
        )

    scope = persistence.get(
        "scope",
        {},
    )

    if not isinstance(
        scope,
        dict,
    ):
        scope = {}

    if scope.get(
        "history_written"
    ) is not True:
        return (
            False,
            (
                "Current persistence stage did not "
                "write history."
            ),
        )

    summary = persistence.get(
        "summary",
        {},
    )

    if not isinstance(
        summary,
        dict,
    ):
        summary = {}

    persistence_sequence = safe_int(
        summary.get(
            "run_sequence",
            -1,
        )
    )

    history_sequence = safe_int(
        history.get(
            "run_sequence",
            -2,
        )
    )

    if (
        persistence_sequence < 1
        or persistence_sequence
        != history_sequence
    ):
        return (
            False,
            (
                "Persistence run sequence does not "
                "match the history being read."
            ),
        )

    persistence_time = persistence.get(
        "generated_at"
    )

    history_time = history.get(
        "updated_at"
    )

    if (
        not persistence_time
        or not history_time
        or persistence_time != history_time
    ):
        return (
            False,
            (
                "Persistence generation time does "
                "not match the latest history update."
            ),
        )

    expected_current = safe_int(
        summary.get(
            "current_family_count",
            -1,
        )
    )

    actual_current = sum(
        1
        for record in history.get(
            "records",
            {},
        ).values()
        if isinstance(
            record,
            dict,
        )
        and bool(
            record.get(
                "seen_in_latest_audit",
                False,
            )
        )
    )

    if (
        expected_current < 0
        or expected_current
        != actual_current
    ):
        return (
            False,
            (
                "Persistence current-family count "
                "does not match the history."
            ),
        )

    return (
        True,
        None,
    )


def build_record(
    record,
):
    (
        recurrence,
        span_hours,
    ) = recurrence_class(
        record
    )

    repeat_count = safe_int(
        record.get(
            "repeat_activity_audits",
            0,
        )
    )

    return {
        "stable_fingerprint": (
            record.get(
                "stable_fingerprint"
            )
        ),
        "family_id": (
            record.get(
                "latest_family_id"
            )
        ),
        "title": record.get(
            "title"
        ),
        "latest_priority": (
            record.get(
                "latest_priority"
            )
        ),
        "seen_in_latest_audit": bool(
            record.get(
                "seen_in_latest_audit",
                False,
            )
        ),
        "last_activity_status": (
            record.get(
                "last_activity_status"
            )
        ),
        "audit_appearances": safe_int(
            record.get(
                "audit_appearances",
                0,
            )
        ),
        "repeat_activity_audits": (
            repeat_count
        ),
        "consecutive_new_activity_audits": (
            safe_int(
                record.get(
                    "consecutive_new_activity_audits",
                    0,
                )
            )
        ),
        "first_audit_seen": (
            record.get(
                "first_audit_seen"
            )
        ),
        "first_repeat_activity_at": (
            record.get(
                "first_repeat_activity_at"
            )
        ),
        "last_repeat_activity_at": (
            record.get(
                "last_repeat_activity_at"
            )
        ),
        "recurrence_observation_span_hours": (
            span_hours
        ),
        "recurrence_class": recurrence,
        "recurrence_basis": (
            recurrence_basis(
                recurrence,
                repeat_count,
                span_hours,
            )
        ),
    }


def build_report(
    history,
    persistence,
):
    (
        valid,
        error,
    ) = validate_history(
        history
    )

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_recurrence_evidence"
            ),
            "input": (
                "log_issue_history.json"
            ),
            "persistence_input": (
                "log_persistence.json"
            ),
            "history_schema_version": (
                SUPPORTED_HISTORY_SCHEMA_VERSION
            ),
            "fingerprint_schema_version": (
                SUPPORTED_FINGERPRINT_SCHEMA_VERSION
            ),
            "recurrence_evidence_produced": (
                False
            ),
            "priority_changed": False,
            "action_recommendation_produced": (
                False
            ),
            "threshold_hours": (
                RECURRENCE_HOURS
            ),
            "definition_note": (
                "Recurrence is based on independently "
                "observed new activity after the "
                "baseline audit. Re-running HA Audit "
                "against unchanged retained System Log "
                "evidence does not create recurrence."
            ),
            "threshold_note": (
                "RECURRING 24H+ requires independently "
                "observed new activity at least 24 "
                "hours after the baseline audit. "
                "Shorter observation windows remain "
                "SHORT-WINDOW REPEAT regardless of "
                "how many rapid audit runs occur."
            ),
        },
        "status": "ok" if valid else "history_invalid",
        "error": error,
        "summary": {},
        "families": [],
    }

    if not valid:
        return report

    (
        persistence_current,
        persistence_error,
    ) = validate_current_persistence(
        history,
        persistence,
    )

    if not persistence_current:
        report[
            "status"
        ] = "persistence_not_current"

        report[
            "error"
        ] = persistence_error

        return report

    records = history.get(
        "records",
        {},
    )

    families = [
        build_record(
            record
        )
        for record in records.values()
        if isinstance(
            record,
            dict,
        )
    ]

    families.sort(
        key=lambda item: (
            0
            if item[
                "seen_in_latest_audit"
            ]
            else 1,
            class_index(
                item.get(
                    "recurrence_class"
                )
            ),
            priority_index(
                item.get(
                    "latest_priority"
                )
            ),
            -safe_int(
                item.get(
                    "repeat_activity_audits",
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

    counts = {
        value: sum(
            1
            for item in families
            if item[
                "recurrence_class"
            ]
            == value
        )
        for value in CLASS_ORDER
    }

    current = [
        item
        for item in families
        if item[
            "seen_in_latest_audit"
        ]
    ]

    current_counts = {
        value: sum(
            1
            for item in current
            if item[
                "recurrence_class"
            ]
            == value
        )
        for value in CLASS_ORDER
    }

    report[
        "scope"
    ][
        "recurrence_evidence_produced"
    ] = True

    report[
        "summary"
    ] = {
        "history_run_sequence": (
            safe_int(
                history.get(
                    "run_sequence",
                    0,
                )
            )
        ),
        "history_record_count": len(
            families
        ),
        "current_family_count": len(
            current
        ),
        "historical_not_current_count": (
            len(
                families
            )
            - len(
                current
            )
        ),
        "recurrence_counts": counts,
        "current_recurrence_counts": (
            current_counts
        ),
    }

    report[
        "families"
    ] = families

    return report


def main():
    try:
        history = load_json(
            INPUT_FILE
        )

        persistence = load_json(
            PERSISTENCE_FILE
        )

        report = build_report(
            history,
            persistence,
        )
    except Exception as exc:
        report = {
            "audit_version": VERSION,
            "generated_at": utc_now(),
            "scope": {
                "phase": (
                    "system_log_recurrence_evidence"
                ),
                "input": (
                    "log_issue_history.json"
                ),
                "persistence_input": (
                    "log_persistence.json"
                ),
                "recurrence_evidence_produced": (
                    False
                ),
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
