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

AUDIT_FILE = "/config/audit_snapshot.json"

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

# Activity within this period is a strong protective signal.
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
    item.get("entity_id"): item
    for item in not_provided_entities
    if item.get("entity_id")
}


entity_ids = sorted(
    entities_by_id
)


# ------------------------------------------------------------
# Determine real history window
# ------------------------------------------------------------

end_time = datetime.now(
    timezone.utc
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
                in history_by_entity
            ):
                history_by_entity[
                    series_entity_id
                ].extend(
                    series
                )

    except Exception as error:
        message = str(
            error
        )

        # Query failure must never be interpreted as
        # evidence that an entity is stale.
        for entity_id in batch:
            query_failures[
                entity_id
            ] = message

    time.sleep(
        0.2
    )


# ------------------------------------------------------------
# Analyse last usable state
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

    last_usable = None


    for state_entry in series:
        if not isinstance(
            state_entry,
            dict,
        ):
            continue

        state = state_entry.get(
            "state"
        )

        if state is None:
            continue

        state_text = str(
            state
        )

        if (
            state_text.strip().lower()
            in IGNORED_STATES
        ):
            continue

        changed = parse_timestamp(
            state_entry.get(
                "last_changed"
            )
            or state_entry.get(
                "last_updated"
            )
        )

        if not changed:
            continue

        if (
            last_usable is None
            or changed
            > last_usable[
                "timestamp"
            ]
        ):
            last_usable = {
                "timestamp":
                    changed,

                "state":
                    state_text,
            }


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
            "last_usable_state"
        ] = None

        result[
            "last_usable_state_at"
        ] = None

        result[
            "history_error"
        ] = query_failures[
            entity_id
        ]


    elif last_usable:
        last_time = last_usable[
            "timestamp"
        ]

        if last_time >= recent_cutoff:
            status = (
                "recent_activity"
            )

        else:
            status = (
                "older_activity"
            )

        result[
            "history_status"
        ] = status

        result[
            "last_usable_state"
        ] = last_usable[
            "state"
        ]

        result[
            "last_usable_state_at"
        ] = last_time.isoformat()

        result[
            "history_error"
        ] = None


    else:
        status = (
            "no_usable_history_found"
        )

        result[
            "history_status"
        ] = status

        result[
            "last_usable_state"
        ] = None

        result[
            "last_usable_state_at"
        ] = None

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


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

report = {
    "audit_version":
        VERSION,

    "generated_at":
        end_time.isoformat(),

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

        "history_start":
            start_time.isoformat(),

        "history_end":
            end_time.isoformat(),

        "recorder_oldest_run":
            (
                recorder_oldest.isoformat()
                if recorder_oldest
                else None
            ),

        "recent_activity_days":
            RECENT_DAYS,

        "ignored_states":
            sorted(
                IGNORED_STATES
            ),

        "important":
            (
                "History is protective context only. "
                "Lack of usable history does not mean "
                "an entity is safe to delete. Recorder "
                "retention, exclusions, or entity-specific "
                "history gaps may limit available evidence."
            ),
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
    f"Recent activity "
    f"(<= {RECENT_DAYS} days):    "
    f"{len(recent_entities)}"
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
    "Important: no usable history "
    "does NOT mean safe to delete."
)

print(
    "Recorder retention, exclusions, "
    "or entity-specific history gaps "
    "may limit available evidence."
)

print("")

print(
    f"History report saved: "
    f"{OUTPUT_FILE}"
)
