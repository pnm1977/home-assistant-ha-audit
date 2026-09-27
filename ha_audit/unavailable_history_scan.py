import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import requests


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ["SUPERVISOR_TOKEN"]

SUPERVISOR = "http://supervisor"

AVAILABILITY_FILE = (
    "/config/availability_audit.json"
)

RECORDER_FILE = (
    "/config/recorder_health_audit.json"
)

OUTPUT_FILE = (
    "/config/unavailable_history_audit.json"
)


# ------------------------------------------------------------
# Conservative history policy
# ------------------------------------------------------------

REQUESTED_LOOKBACK_DAYS = 90

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


def series_entity_id(
    series,
    requested_entity_ids,
):
    for state_entry in series:
        if not isinstance(
            state_entry,
            dict,
        ):
            continue

        candidate = state_entry.get(
            "entity_id"
        )

        if candidate:
            return candidate

    # A single-entity retry can still be mapped safely even if a
    # minimal History API response unexpectedly omits entity_id.
    if len(requested_entity_ids) == 1:
        return requested_entity_ids[0]

    return None


def merge_history_payload(
    payload,
    requested_entity_ids,
    history_by_entity,
):
    for series in payload:
        if not isinstance(
            series,
            list,
        ):
            continue

        if not series:
            continue

        entity_id = series_entity_id(
            series,
            requested_entity_ids,
        )

        if entity_id not in history_by_entity:
            continue

        history_by_entity[
            entity_id
        ].extend(
            series
        )


def history_entry_timestamp(state_entry):
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


def analyse_history_series(series):
    timeline = []

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

        changed = history_entry_timestamp(
            state_entry
        )

        if not changed:
            continue

        state_text = str(
            state
        )

        timeline.append(
            {
                "timestamp": changed,
                "state": state_text,
                "normalised_state": (
                    state_text.strip().lower()
                ),
            }
        )

    timeline.sort(
        key=lambda item: item[
            "timestamp"
        ]
    )

    last_recorded = (
        timeline[-1]
        if timeline
        else None
    )

    last_usable_index = None

    for index, item in enumerate(
        timeline
    ):
        if (
            item[
                "normalised_state"
            ]
            not in IGNORED_STATES
        ):
            last_usable_index = index

    if last_usable_index is None:
        last_usable = None
        last_usable_ended_at = None
    else:
        last_usable = timeline[
            last_usable_index
        ]

        last_usable_ended_at = None

        for item in timeline[
            last_usable_index + 1:
        ]:
            if (
                item[
                    "normalised_state"
                ]
                in IGNORED_STATES
            ):
                last_usable_ended_at = item[
                    "timestamp"
                ]
                break

    return {
        "last_recorded_state": (
            last_recorded[
                "state"
            ]
            if last_recorded
            else None
        ),
        "last_recorded_state_at": (
            last_recorded[
                "timestamp"
            ].isoformat()
            if last_recorded
            else None
        ),
        "last_usable_state": (
            last_usable[
                "state"
            ]
            if last_usable
            else None
        ),
        "last_usable_state_started_at": (
            last_usable[
                "timestamp"
            ].isoformat()
            if last_usable
            else None
        ),
        "last_usable_state_ended_at": (
            last_usable_ended_at.isoformat()
            if last_usable_ended_at
            else None
        ),
    }


# ------------------------------------------------------------
# Main audit
# ------------------------------------------------------------


def main():
    availability = load_json(
        AVAILABILITY_FILE
    )

    recorder = load_json_optional(
        RECORDER_FILE
    )

    unavailable_entities = availability.get(
        "entities",
        [],
    )

    if not isinstance(
        unavailable_entities,
        list,
    ):
        unavailable_entities = []

    entities_by_id = {
        item.get("entity_id"): item
        for item in unavailable_entities
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

    # --------------------------------------------------------
    # Determine history end from the availability snapshot
    # --------------------------------------------------------

    source_availability_observed_at = (
        availability.get(
            "states_observed_at"
        )
    )

    availability_observed_at = parse_timestamp(
        source_availability_observed_at
    )

    if availability_observed_at:
        end_time = availability_observed_at
        history_end_source = (
            "availability_states_observed_at"
        )
    else:
        end_time = datetime.now(
            timezone.utc
        )
        history_end_source = (
            "scanner_start_fallback"
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

    # --------------------------------------------------------
    # Query Home Assistant history
    # --------------------------------------------------------

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

            # A batch failure should not automatically turn every
            # entity in that batch into a failed history result.
            # Retry each entity independently and only retain genuine
            # per-entity failures.
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

    # --------------------------------------------------------
    # Analyse history
    # --------------------------------------------------------

    results = []

    status_counts = Counter()

    platform_status_counts = defaultdict(
        Counter
    )

    availability_classification_counts = defaultdict(
        Counter
    )

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

        availability_classification = source.get(
            "classification",
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
            "history_records_returned"
        ] = len(
            series
        )

        result.update(
            analysis
        )

        if entity_id in query_failures:
            status = (
                "history_query_failed"
            )

            result[
                "history_error"
            ] = query_failures[
                entity_id
            ]

        elif not series:
            status = (
                "no_history_returned"
            )

            result[
                "history_error"
            ] = None

        elif analysis.get(
            "last_usable_state"
        ) is None:
            status = (
                "history_found_no_usable_state"
            )

            result[
                "history_error"
            ] = None

        else:
            status = (
                "usable_history_found"
            )

            result[
                "history_error"
            ] = None

        result[
            "history_status"
        ] = status

        status_counts[
            status
        ] += 1

        platform_status_counts[
            platform
        ][
            status
        ] += 1

        availability_classification_counts[
            availability_classification
        ][
            status
        ] += 1

        results.append(
            result
        )

    results.sort(
        key=lambda item: (
            item.get(
                "history_status",
                "",
            ),
            item.get(
                "classification",
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

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    generated_at = datetime.now(
        timezone.utc
    )

    report = {
        "audit_version":
            VERSION,

        "generated_at":
            generated_at.isoformat(),

        "source_availability_observed_at":
            source_availability_observed_at,

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

            "batch_size":
                BATCH_SIZE,

            "ignored_states":
                sorted(
                    IGNORED_STATES
                ),

            "important":
                (
                    "Recorder history is observational context only. "
                    "Old, recent, or absent usable history does not by "
                    "itself indicate a fault, stale entity, configuration "
                    "problem, or required action. Recorder retention, "
                    "exclusions, and temporary availability conditions may "
                    "limit the evidence returned."
                ),

            "last_usable_interval":
                (
                    "last_usable_state_started_at is when the final usable "
                    "state began. last_usable_state_ended_at is populated "
                    "only when Recorder history contains a following "
                    "unavailable, unknown, or none state that marks the end "
                    "of that usable interval."
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
            "currently_unavailable_checked":
                len(
                    entity_ids
                ),

            "usable_history_found":
                status_counts.get(
                    "usable_history_found",
                    0,
                ),

            "history_found_no_usable_state":
                status_counts.get(
                    "history_found_no_usable_state",
                    0,
                ),

            "no_history_returned":
                status_counts.get(
                    "no_history_returned",
                    0,
                ),

            "history_query_failed":
                status_counts.get(
                    "history_query_failed",
                    0,
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

        "status_by_availability_classification": {
            classification:
                dict(
                    counts
                )
            for classification, counts
            in sorted(
                availability_classification_counts.items()
            )
        },

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

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print("")

    print(
        "Unavailable entity history audit"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"Entities checked:                 "
        f"{len(entity_ids)}"
    )

    print(
        f"Requested lookback:               "
        f"{REQUESTED_LOOKBACK_DAYS} days"
    )

    print(
        f"Effective lookback:               "
        f"{effective_lookback_days:.1f} days"
    )

    print(
        f"Usable history found:             "
        f"{status_counts.get('usable_history_found', 0)}"
    )

    print(
        f"History found, no usable state:   "
        f"{status_counts.get('history_found_no_usable_state', 0)}"
    )

    print(
        f"No history returned:              "
        f"{status_counts.get('no_history_returned', 0)}"
    )

    print(
        f"History query failures:           "
        f"{status_counts.get('history_query_failed', 0)}"
    )

    if batch_query_failures:
        print(
            f"Batch failures retried:           "
            f"{batch_query_failures}"
        )

        print(
            f"Individual retry failures:        "
            f"{individual_retry_failures}"
        )

    print("")

    print(
        "Recorder history is observational context only."
    )

    print(
        "Old, recent, or absent history does not by itself "
        "indicate a fault or required action."
    )

    print("")

    print(
        f"History report saved: "
        f"{OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
