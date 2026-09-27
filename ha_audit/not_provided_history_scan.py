import json
import os
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ["SUPERVISOR_TOKEN"]

SUPERVISOR = "http://supervisor"

AUDIT_FILE = (
    "/config/audit_snapshot.json"
)

RECORDER_FILE = (
    "/config/recorder_health_audit.json"
)

OUTPUT_FILE = (
    "/config/not_provided_history_audit.json"
)


# ------------------------------------------------------------
# Conservative history policy
# ------------------------------------------------------------

REQUESTED_LOOKBACK_DAYS = 90

# When the end of the final usable interval is known, activity
# ending within this period is treated as a strong protective
# signal. If Recorder does not contain a following non-usable
# transition, the interval end is unknown and is also treated
# conservatively as protective rather than being called old.
RECENT_DAYS = 45

BATCH_SIZE = 20

IGNORED_STATES = {
    "unavailable",
    "unknown",
    "none",
}


HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def load_json_optional(path):
    try:
        return load_json(
            path
        )
    except Exception:
        return {}


def parse_timestamp(value):
    if not value:
        return None

    try:
        stamp = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00",
            )
        )
    except Exception:
        return None

    if stamp.tzinfo is None:
        stamp = stamp.replace(
            tzinfo=timezone.utc
        )

    return stamp


def state_timestamp(state_entry):
    if not isinstance(
        state_entry,
        dict,
    ):
        return None

    return parse_timestamp(
        state_entry.get(
            "last_changed"
        )
        or state_entry.get(
            "last_updated"
        )
    )


def normalised_state(state_entry):
    if not isinstance(
        state_entry,
        dict,
    ):
        return None

    state = state_entry.get(
        "state"
    )

    if state is None:
        return None

    return str(
        state
    ).strip()


def is_usable_state(state_text):
    if state_text is None:
        return False

    return (
        state_text.lower()
        not in IGNORED_STATES
    )


def chunks(items, size):
    for index in range(
        0,
        len(items),
        size,
    ):
        yield items[
            index:index + size
        ]


def fetch_history(
    entity_ids,
    start_time,
    end_time,
):
    encoded_start = quote(
        start_time.isoformat(
            timespec="seconds"
        ),
        safe="",
    )

    url = (
        f"{SUPERVISOR}"
        f"/core/api/history/period/"
        f"{encoded_start}"
    )

    params = {
        "filter_entity_id":
            ",".join(
                entity_ids
            ),

        "end_time":
            end_time.isoformat(
                timespec="seconds"
            ),

        "minimal_response":
            "true",

        "no_attributes":
            "true",

        "significant_changes_only":
            "true",
    }

    response = requests.get(
        url,
        headers=HEADERS,
        params=params,
        timeout=120,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(
        payload,
        list,
    ):
        raise RuntimeError(
            "History API returned an "
            "unexpected response."
        )

    return payload


def merge_history_payload(
    payload,
    requested_entity_ids,
    history_by_entity,
):
    requested = set(
        requested_entity_ids
    )

    for series in payload:
        if not isinstance(
            series,
            list,
        ):
            continue

        if not series:
            continue

        series_entity_id = None

        for state_entry in series:
            if not isinstance(
                state_entry,
                dict,
            ):
                continue

            candidate = (
                state_entry.get(
                    "entity_id"
                )
            )

            if candidate:
                series_entity_id = candidate
                break

        if (
            series_entity_id
            and series_entity_id in requested
            and series_entity_id in history_by_entity
        ):
            history_by_entity[
                series_entity_id
            ].extend(
                series
            )


def analyse_history_series(series):
    entries = []

    for state_entry in series:
        state_text = normalised_state(
            state_entry
        )

        changed = state_timestamp(
            state_entry
        )

        if (
            state_text is None
            or changed is None
        ):
            continue

        entries.append(
            {
                "state":
                    state_text,

                "timestamp":
                    changed,

                "usable":
                    is_usable_state(
                        state_text
                    ),
            }
        )

    entries.sort(
        key=lambda item:
            item["timestamp"]
    )

    if not entries:
        return {
            "last_recorded_state":
                None,

            "last_recorded_state_at":
                None,

            "last_usable_state":
                None,

            "last_usable_state_started_at":
                None,

            "last_usable_state_ended_at":
                None,

            "last_usable_state_end_known":
                False,

            "last_usable_state_at":
                None,

            "last_usable_state_at_basis":
                None,
        }

    last_recorded = entries[
        -1
    ]

    last_usable_index = None

    for index, item in enumerate(
        entries
    ):
        if item[
            "usable"
        ]:
            last_usable_index = index

    if last_usable_index is None:
        return {
            "last_recorded_state":
                last_recorded[
                    "state"
                ],

            "last_recorded_state_at":
                last_recorded[
                    "timestamp"
                ].isoformat(),

            "last_usable_state":
                None,

            "last_usable_state_started_at":
                None,

            "last_usable_state_ended_at":
                None,

            "last_usable_state_end_known":
                False,

            "last_usable_state_at":
                None,

            "last_usable_state_at_basis":
                None,
        }

    last_usable = entries[
        last_usable_index
    ]

    ended_at = None

    for later in entries[
        last_usable_index + 1:
    ]:
        if not later[
            "usable"
        ]:
            ended_at = later[
                "timestamp"
            ]
            break

    reference_time = (
        ended_at
        or last_usable[
            "timestamp"
        ]
    )

    reference_basis = (
        "interval_end"
        if ended_at
        else "interval_start_end_unknown"
    )

    return {
        "last_recorded_state":
            last_recorded[
                "state"
            ],

        "last_recorded_state_at":
            last_recorded[
                "timestamp"
            ].isoformat(),

        "last_usable_state":
            last_usable[
                "state"
            ],

        "last_usable_state_started_at":
            last_usable[
                "timestamp"
            ].isoformat(),

        "last_usable_state_ended_at":
            (
                ended_at.isoformat()
                if ended_at
                else None
            ),

        "last_usable_state_end_known":
            bool(
                ended_at
            ),

        # Compatibility field for the current summary/report
        # consumer. When the interval end is known this is the
        # true end; otherwise it is only the recorded start of
        # the final usable state and the basis field says so.
        "last_usable_state_at":
            reference_time.isoformat(),

        "last_usable_state_at_basis":
            reference_basis,
    }


# ------------------------------------------------------------
# Load audit data
# ------------------------------------------------------------

audit = load_json(
    AUDIT_FILE
)

recorder = load_json_optional(
    RECORDER_FILE
)


not_provided_entities = (
    audit.get(
        "entities",
        {},
    )
    .get(
        "not_currently_provided",
        {},
    )
    .get(
        "entities",
        [],
    )
)


entities_by_id = {
    item.get(
        "entity_id"
    ): item

    for item in not_provided_entities

    if isinstance(
        item,
        dict,
    )
    and item.get(
        "entity_id"
    )
}


entity_ids = sorted(
    entities_by_id
)


# ------------------------------------------------------------
# Determine history end and real Recorder window
# ------------------------------------------------------------

audit_generated_at = parse_timestamp(
    audit.get(
        "generated_at"
    )
)

if audit_generated_at:
    end_time = audit_generated_at

    history_end_source = (
        "audit_snapshot_generated_at"
    )

else:
    end_time = datetime.now(
        timezone.utc
    )

    history_end_source = (
        "scanner_generated_at_fallback"
    )


requested_start = (
    end_time
    - timedelta(
        days=REQUESTED_LOOKBACK_DAYS
    )
)


recorder_oldest = parse_timestamp(
    recorder.get(
        "recorder",
        {},
    ).get(
        "oldest_recorder_run"
    )
)


recorder_status = recorder.get(
    "status"
)


if (
    recorder_status == "ok"
    and recorder_oldest
):
    start_time = max(
        requested_start,
        recorder_oldest,
    )

    history_window_source = (
        "recorder_oldest_run"
    )

else:
    start_time = requested_start

    history_window_source = (
        "requested_lookback_fallback"
    )


history_window_clamped = False

if start_time > end_time:
    start_time = end_time

    history_window_clamped = True


effective_lookback_days = max(
    0.0,
    (
        end_time
        - start_time
    ).total_seconds()
    / 86400.0,
)


recent_cutoff = (
    end_time
    - timedelta(
        days=RECENT_DAYS
    )
)


# ------------------------------------------------------------
# Query Home Assistant history
# ------------------------------------------------------------

history_by_entity = {
    entity_id: []
    for entity_id in entity_ids
}

query_failures = {}

batch_query_failures = 0
individual_retry_attempts = 0
individual_retry_failures = 0


for batch in chunks(
    entity_ids,
    BATCH_SIZE,
):
    try:
        payload = fetch_history(
            batch,
            start_time,
            end_time,
        )

        merge_history_payload(
            payload,
            batch,
            history_by_entity,
        )

    except Exception as batch_error:
        batch_query_failures += 1

        batch_message = str(
            batch_error
        )

        # Retry individually so one failed batch does not turn
        # every entity in it into a failed history result.
        for entity_id in batch:
            individual_retry_attempts += 1

            try:
                payload = fetch_history(
                    [entity_id],
                    start_time,
                    end_time,
                )

                merge_history_payload(
                    payload,
                    [entity_id],
                    history_by_entity,
                )

            except Exception as retry_error:
                individual_retry_failures += 1

                query_failures[
                    entity_id
                ] = (
                    "Batch query failed: "
                    f"{batch_message}; "
                    "individual retry failed: "
                    f"{retry_error}"
                )

            time.sleep(
                0.05
            )

    time.sleep(
        0.2
    )


# ------------------------------------------------------------
# Analyse usable history
# ------------------------------------------------------------

results = []

status_counts = Counter()

platform_status_counts = {}


for entity_id in entity_ids:
    source = dict(
        entities_by_id[
            entity_id
        ]
    )

    platform = source.get(
        "platform",
        "unknown",
    )

    series = history_by_entity.get(
        entity_id,
        [],
    )

    analysis = analyse_history_series(
        series
    )

    result = source

    result[
        "requested_history_lookback_days"
    ] = REQUESTED_LOOKBACK_DAYS

    result[
        "effective_history_lookback_days"
    ] = round(
        effective_lookback_days,
        2,
    )

    result[
        "history_records_returned"
    ] = len(
        series
    )

    result.update(
        analysis
    )


    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if entity_id in query_failures:
        status = (
            "history_query_failed"
        )

        result[
            "history_status"
        ] = status

        result[
            "history_status_reason"
        ] = (
            "Recorder history could not "
            "be checked for this entity."
        )

        result[
            "history_error"
        ] = query_failures[
            entity_id
        ]


    elif result.get(
        "last_usable_state"
    ) is not None:

        ended_at = parse_timestamp(
            result.get(
                "last_usable_state_ended_at"
            )
        )

        started_at = parse_timestamp(
            result.get(
                "last_usable_state_started_at"
            )
        )

        if ended_at is None:
            # The final usable state has no following non-usable
            # transition in Recorder. We cannot prove that it
            # ended before the recent cutoff, so preserve it as
            # protective context rather than calling it old.
            status = (
                "recent_activity"
            )

            result[
                "history_status_reason"
            ] = (
                "The final usable state has no "
                "recorded end transition. Its end "
                "is unknown, so it remains "
                "protective context."
            )

        elif ended_at >= recent_cutoff:
            status = (
                "recent_activity"
            )

            result[
                "history_status_reason"
            ] = (
                "The final usable interval ended "
                f"within {RECENT_DAYS} days of "
                "the audit snapshot."
            )

        else:
            status = (
                "older_activity"
            )

            result[
                "history_status_reason"
            ] = (
                "Recorder shows the final usable "
                "interval ended before the recent "
                f"{RECENT_DAYS}-day window."
            )

        result[
            "history_status"
        ] = status

        result[
            "history_error"
        ] = None

        # Defensive fallback: a usable state should always have
        # a parsed start time, but keep the output explicit if a
        # malformed history response ever reaches this point.
        if started_at is None:
            result[
                "history_status_reason"
            ] += (
                " The usable-state start timestamp "
                "could not be parsed."
            )


    else:
        status = (
            "no_usable_history_found"
        )

        result[
            "history_status"
        ] = status

        result[
            "history_status_reason"
        ] = (
            "No usable state was returned within "
            "the effective Recorder window. This "
            "does not establish that the entity "
            "is obsolete or safe to remove."
        )

        result[
            "history_error"
        ] = None


    status_counts[
        status
    ] += 1


    if platform not in platform_status_counts:
        platform_status_counts[
            platform
        ] = Counter()

    platform_status_counts[
        platform
    ][
        status
    ] += 1


    results.append(
        result
    )


# ------------------------------------------------------------
# Group results
# ------------------------------------------------------------

results.sort(
    key=lambda item: (
        item.get(
            "history_status",
            "",
        ),
        item.get(
            "platform",
            "",
        ),
        item.get(
            "entity_id",
            "",
        ),
    )
)


recent_entities = [
    item
    for item in results
    if item.get(
        "history_status"
    ) == "recent_activity"
]


older_entities = [
    item
    for item in results
    if item.get(
        "history_status"
    ) == "older_activity"
]


no_history_entities = [
    item
    for item in results
    if item.get(
        "history_status"
    ) == "no_usable_history_found"
]


failed_entities = [
    item
    for item in results
    if item.get(
        "history_status"
    ) == "history_query_failed"
]


unknown_end_entities = [
    item
    for item in recent_entities
    if (
        item.get(
            "last_usable_state"
        ) is not None
        and not item.get(
            "last_usable_state_end_known",
            False,
        )
    )
]


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

report = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "source_audit_generated_at":
        (
            audit_generated_at.isoformat()
            if audit_generated_at
            else None
        ),

    "history_policy": {
        "requested_lookback_days":
            REQUESTED_LOOKBACK_DAYS,

        "effective_lookback_days":
            round(
                effective_lookback_days,
                2,
            ),

        "history_window_source":
            history_window_source,

        "history_window_clamped":
            history_window_clamped,

        "history_end_source":
            history_end_source,

        "history_start":
            start_time.isoformat(),

        "history_end":
            end_time.isoformat(),

        "recorder_status":
            recorder_status,

        "recorder_oldest_run":
            (
                recorder_oldest.isoformat()
                if recorder_oldest
                else None
            ),

        "recent_activity_days":
            RECENT_DAYS,

        "batch_size":
            BATCH_SIZE,

        "ignored_states":
            sorted(
                IGNORED_STATES
            ),

        "recent_activity_rule":
            (
                "Recent activity includes a final usable "
                "interval that ended within the recent "
                "window, or a final usable interval whose "
                "end is not recorded. Unknown interval "
                "ends are treated conservatively as "
                "protective context."
            ),

        "important":
            (
                "History is protective context only. "
                "Lack of usable history does not mean "
                "an entity is obsolete or safe to remove. "
                "Recorder retention, exclusions, or "
                "entity-specific history gaps may limit "
                "available evidence."
            ),
    },

    "query_diagnostics": {
        "batch_query_failures":
            batch_query_failures,

        "individual_retry_attempts":
            individual_retry_attempts,

        "individual_retry_failures":
            individual_retry_failures,
    },

    "summary": {
        "not_currently_provided":
            len(
                entity_ids
            ),

        "recent_activity":
            len(
                recent_entities
            ),

        "recent_activity_end_unknown":
            len(
                unknown_end_entities
            ),

        "older_activity":
            len(
                older_entities
            ),

        "no_usable_history_found":
            len(
                no_history_entities
            ),

        "history_query_failed":
            len(
                failed_entities
            ),
    },

    "status_by_platform": {
        platform:
            dict(
                counts
            )

        for platform, counts
        in sorted(
            platform_status_counts.items()
        )
    },

    "recent_activity_entities":
        recent_entities,

    "older_activity_entities":
        older_entities,

    "no_usable_history_entities":
        no_history_entities,

    "history_query_failed_entities":
        failed_entities,

    "entities":
        results,
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:
    json.dump(
        report,
        handle,
        indent=2,
    )


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")

print(
    "Not-provided entity history audit"
)

print(
    "------------------------------------------"
)

print(
    f"Entities checked:            "
    f"{len(entity_ids)}"
)

print(
    f"Requested lookback:          "
    f"{REQUESTED_LOOKBACK_DAYS} days"
)

print(
    f"Effective lookback:          "
    f"{effective_lookback_days:.1f} days"
)

if recorder_oldest:
    print(
        f"Recorder history starts:     "
        f"{recorder_oldest.isoformat()}"
    )

print(
    f"Recent/protective activity:  "
    f"{len(recent_entities)}"
)

print(
    f"  End time unknown:          "
    f"{len(unknown_end_entities)}"
)

print(
    f"Older activity found:        "
    f"{len(older_entities)}"
)

print(
    f"No usable history found:     "
    f"{len(no_history_entities)}"
)

print(
    f"History query failures:      "
    f"{len(failed_entities)}"
)

print("")

print(
    "Important: history is protective "
    "context only."
)

print(
    "An unknown usable-state end is kept "
    "protective rather than assumed old."
)

print("")

print(
    f"History report saved: "
    f"{OUTPUT_FILE}"
)
