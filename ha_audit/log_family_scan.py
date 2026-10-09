import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

INPUT_FILE = (
    "/config/log_audit.json"
)

OUTPUT_FILE = (
    "/config/log_issue_families.json"
)

MAX_MESSAGE_SAMPLES = 8
MAX_MEMBERS_PER_FAMILY = 25
MAX_SAMPLE_LENGTH = 500


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


def truncate(
    value,
    limit=MAX_SAMPLE_LENGTH,
):
    text = clean_text(
        value
    )

    if len(
        text
    ) <= limit:
        return text

    return (
        text[
            :limit - 3
        ]
        + "..."
    )


def entry_messages(
    entry,
):
    messages = entry.get(
        "messages",
        [],
    )

    if isinstance(
        messages,
        list,
    ):
        return [
            clean_text(
                item
            )
            for item in messages
            if clean_text(
                item
            )
        ]

    if messages:
        return [
            clean_text(
                messages
            )
        ]

    return []


def entry_text(
    entry,
):
    source = entry.get(
        "source",
        {},
    )

    if not isinstance(
        source,
        dict,
    ):
        source = {}

    parts = [
        entry.get(
            "name",
            "",
        ),
        source.get(
            "file",
            "",
        ),
        entry.get(
            "exception",
            "",
        ),
    ]

    parts.extend(
        entry_messages(
            entry
        )
    )

    return " ".join(
        clean_text(
            item
        )
        for item in parts
        if clean_text(
            item
        )
    ).lower()


def logger_name(
    entry,
):
    return clean_text(
        entry.get(
            "name",
            "unknown",
        )
    )


def source_file(
    entry,
):
    source = entry.get(
        "source",
        {},
    )

    if not isinstance(
        source,
        dict,
    ):
        return ""

    return clean_text(
        source.get(
            "file",
            "",
        )
    ).lower()


def has_any(
    text,
    markers,
):
    return any(
        marker.lower()
        in text
        for marker in markers
    )


def match_zigbee_delivery(
    entry,
    text,
):
    delivery_markers = (
        "txstatus.",
        "failed to deliver packet",
        "nwk_route_discovery_failed",
        "mac_no_ack",
        "mac_channel_access_failure",
        "aps_no_ack",
        "failed to send request: device did not respond",
        "unexpected transmit confirm",
    )

    if has_any(
        text,
        delivery_markers,
    ):
        return True

    file_name = source_file(
        entry
    )

    if (
        file_name.startswith(
            "components/zha/"
        )
        or "/components/zha/"
        in file_name
    ):
        return True

    provenance_markers = (
        "components/zha/helpers.py",
        "homeassistant/components/zha/",
        "zha/application/platforms/",
        "zigpy.exceptions.deliveryerror",
        "zigpy_deconz.zigbee.application",
    )

    if has_any(
        text,
        provenance_markers,
    ):
        return True

    return False


def match_shelly(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "homeassistant.components.shelly"
    )


def match_apple_tv(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "homeassistant.components.apple_tv"
    )


def match_hue_sync(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "custom_components.huesyncbox"
    )


def match_octopus(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "custom_components.octopus_energy"
    )


def match_esphome(
    entry,
    text,
):
    name = logger_name(
        entry
    )

    return (
        name.startswith(
            "aioesphomeapi"
        )
        or name.startswith(
            "homeassistant.components.esphome"
        )
    )


def match_robovac(
    entry,
    text,
):
    name = logger_name(
        entry
    ).lower()

    return (
        "robovac"
        in name
        or "vacuum.robovac_"
        in text
    )


def match_music_queue_info(
    entry,
    text,
):
    return (
        "queue_info"
        in text
        and "undefined"
        in text
    )


def match_lg_tv_off(
    entry,
    text,
):
    return (
        "lg webos smart tv"
        in text
        and (
            "device is off"
            in text
            and "cannot be controlled"
            in text
        )
    )


def match_missing_targets(
    entry,
    text,
):
    return (
        logger_name(
            entry
        )
        == "homeassistant.helpers.service"
        and (
            "missing or not currently available"
            in text
        )
    )


def match_slow_entity_update(
    entry,
    text,
):
    return (
        logger_name(
            entry
        )
        == "homeassistant.helpers.entity"
        and "taking over 10 seconds"
        in text
    )


def match_invalid_auth(
    entry,
    text,
):
    return (
        logger_name(
            entry
        )
        == "homeassistant.components.http.ban"
        and (
            "invalid authentication"
            in text
            or "login attempt"
            in text
        )
    )


def match_supervisor_store_reload(
    entry,
    text,
):
    return (
        logger_name(
            entry
        ).startswith(
            "homeassistant.components.hassio"
        )
        and "/store/reload"
        in text
    )


def match_mypyllant(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "custom_components.mypyllant"
    )


def match_nabu_casa(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "hass_nabucasa."
    )


def match_sonos(
    entry,
    text,
):
    return logger_name(
        entry
    ).startswith(
        "homeassistant.components.sonos"
    )


RULES = (
    {
        "id": "zigbee_delivery",
        "title": (
            "Zigbee / ZHA delivery failures"
        ),
        "match": match_zigbee_delivery,
    },
    {
        "id": "music_queue_info",
        "title": (
            "Music automation queue_info "
            "template failures"
        ),
        "match": match_music_queue_info,
    },
    {
        "id": "lg_tv_off",
        "title": (
            "LG TV automation calls while "
            "the device is off"
        ),
        "match": match_lg_tv_off,
    },
    {
        "id": "missing_targets",
        "title": (
            "Referenced entities or devices "
            "not currently available"
        ),
        "match": match_missing_targets,
    },
    {
        "id": "slow_entity_update",
        "title": (
            "Entity updates taking over "
            "10 seconds"
        ),
        "match": match_slow_entity_update,
    },
    {
        "id": "invalid_auth",
        "title": (
            "Invalid authentication requests"
        ),
        "match": match_invalid_auth,
    },
    {
        "id": "supervisor_store_reload",
        "title": (
            "Supervisor App Store reload "
            "timeouts"
        ),
        "match": match_supervisor_store_reload,
    },
    {
        "id": "shelly",
        "title": (
            "Shelly integration data retrieval"
        ),
        "match": match_shelly,
    },
    {
        "id": "apple_tv",
        "title": (
            "Apple TV connectivity"
        ),
        "match": match_apple_tv,
    },
    {
        "id": "hue_sync",
        "title": (
            "Hue Sync Box connectivity"
        ),
        "match": match_hue_sync,
    },
    {
        "id": "octopus_energy",
        "title": (
            "Octopus Energy API / data retrieval"
        ),
        "match": match_octopus,
    },
    {
        "id": "esphome",
        "title": (
            "ESPHome device connectivity"
        ),
        "match": match_esphome,
    },
    {
        "id": "robovac",
        "title": (
            "RoboVac connectivity"
        ),
        "match": match_robovac,
    },
    {
        "id": "mypyllant",
        "title": (
            "myVAILLANT API / data retrieval"
        ),
        "match": match_mypyllant,
    },
    {
        "id": "nabu_casa",
        "title": (
            "Home Assistant Cloud connectivity"
        ),
        "match": match_nabu_casa,
    },
    {
        "id": "sonos",
        "title": (
            "Sonos connectivity"
        ),
        "match": match_sonos,
    },
)


def fallback_message_signature(
    entry,
):
    messages = sorted(
        {
            clean_text(
                message
            )
            for message in entry_messages(
                entry
            )
            if clean_text(
                message
            )
        }
    )

    return "\n".join(
        messages
    )


def fallback_source_line(
    entry,
):
    source = entry.get(
        "source",
        {},
    )

    if not isinstance(
        source,
        dict,
    ):
        return ""

    line = source.get(
        "line"
    )

    if line is None:
        return ""

    return str(
        line
    )


def fallback_family(
    entry,
    index,
):
    # The source-entry index and exception text must not be part of
    # fallback identity.
    #
    # Home Assistant can expose the same underlying System Log issue as
    # multiple rows in one collection. Exception payloads can vary between
    # those rows even when the visible logger/source/message evidence is
    # identical. Including exception text here therefore creates separate
    # family IDs that later collapse to the same stable fingerprint.
    #
    # Consolidate only when logger, level, source location and the complete
    # cleaned message set are identical. This keeps the fallback grouping
    # conservative while removing observer-only row/exception differences.
    signature = "|".join(
        (
            logger_name(
                entry
            ).lower(),
            clean_text(
                entry.get(
                    "level",
                    "UNKNOWN",
                )
            ).upper(),
            source_file(
                entry
            ),
            fallback_source_line(
                entry
            ),
            fallback_message_signature(
                entry
            ),
        )
    )

    digest = hashlib.sha1(
        signature.encode(
            "utf-8"
        )
    ).hexdigest()[
        :10
    ]

    return {
        "id": (
            f"unclassified_{digest}"
        ),
        "title": (
            "Unclassified System Log entry"
        ),
        "grouping_method": (
            "single_entry_fallback"
        ),
        "rule_id": None,
    }


def classify_entry(
    entry,
    index,
):
    text = entry_text(
        entry
    )

    for rule in RULES:
        if rule[
            "match"
        ](
            entry,
            text,
        ):
            return {
                "id": rule[
                    "id"
                ],
                "title": rule[
                    "title"
                ],
                "grouping_method": (
                    "deterministic_rule"
                ),
                "rule_id": rule[
                    "id"
                ],
            }

    return fallback_family(
        entry,
        index,
    )


def source_label(
    entry,
):
    source = entry.get(
        "source",
        {},
    )

    if not isinstance(
        source,
        dict,
    ):
        return None

    filename = source.get(
        "file"
    )

    line = source.get(
        "line"
    )

    if not filename:
        return None

    if line is None:
        return str(
            filename
        )

    return (
        f"{filename}:{line}"
    )


def safe_count(
    entry,
):
    try:
        return max(
            1,
            int(
                entry.get(
                    "count",
                    1,
                )
                or 1
            ),
        )
    except (
        TypeError,
        ValueError,
    ):
        return 1


def min_timestamp(
    values,
):
    values = [
        value
        for value in values
        if value
    ]

    if not values:
        return None

    return min(
        values
    )


def max_timestamp(
    values,
):
    values = [
        value
        for value in values
        if value
    ]

    if not values:
        return None

    return max(
        values
    )


def build_family(
    definition,
    members,
):
    level_occurrences = defaultdict(
        int
    )

    level_entry_counts = defaultdict(
        int
    )

    logger_names = set()
    sources = set()
    messages = []

    for member in members:
        entry = member[
            "entry"
        ]

        count = safe_count(
            entry
        )

        level = clean_text(
            entry.get(
                "level",
                "UNKNOWN",
            )
        ).upper()

        level_occurrences[
            level
        ] += count

        level_entry_counts[
            level
        ] += 1

        logger_names.add(
            logger_name(
                entry
            )
        )

        source = source_label(
            entry
        )

        if source:
            sources.add(
                source
            )

        for message in entry_messages(
            entry
        ):
            sample = truncate(
                message
            )

            if (
                sample
                and sample
                not in messages
            ):
                messages.append(
                    sample
                )

            if (
                len(
                    messages
                )
                >= MAX_MESSAGE_SAMPLES
            ):
                break

    occurrence_count = sum(
        safe_count(
            member[
                "entry"
            ]
        )
        for member in members
    )

    first_seen = min_timestamp(
        [
            member[
                "entry"
            ].get(
                "first_seen"
            )
            for member in members
        ]
    )

    last_seen = max_timestamp(
        [
            member[
                "entry"
            ].get(
                "last_seen"
            )
            for member in members
        ]
    )

    member_rows = []

    for member in members[
        :MAX_MEMBERS_PER_FAMILY
    ]:
        entry = member[
            "entry"
        ]

        member_rows.append(
            {
                "source_entry_index": (
                    member[
                        "index"
                    ]
                ),
                "level": clean_text(
                    entry.get(
                        "level",
                        "UNKNOWN",
                    )
                ).upper(),
                "name": logger_name(
                    entry
                ),
                "count": safe_count(
                    entry
                ),
                "first_seen": (
                    entry.get(
                        "first_seen"
                    )
                ),
                "last_seen": (
                    entry.get(
                        "last_seen"
                    )
                ),
            }
        )

    return {
        "family_id": definition[
            "id"
        ],
        "title": definition[
            "title"
        ],
        "grouping_method": definition[
            "grouping_method"
        ],
        "rule_id": definition[
            "rule_id"
        ],
        "source_entry_count": len(
            members
        ),
        "occurrence_count": (
            occurrence_count
        ),
        "level_occurrences": dict(
            sorted(
                level_occurrences.items()
            )
        ),
        "level_entry_counts": dict(
            sorted(
                level_entry_counts.items()
            )
        ),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "logger_names": sorted(
            logger_names
        ),
        "sources": sorted(
            sources
        ),
        "message_samples": messages[
            :MAX_MESSAGE_SAMPLES
        ],
        "members": member_rows,
    }


def build_family_report(
    log_audit,
):
    collection = log_audit.get(
        "collection",
        {},
    )

    if not isinstance(
        collection,
        dict,
    ):
        collection = {}

    source_status = collection.get(
        "status",
        "unknown",
    )

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_issue_family_probe"
            ),
            "input": (
                "log_audit.json"
            ),
            "grouping_only": True,
            "priority_produced": False,
            "severity_produced": False,
            "action_recommendation_produced": (
                False
            ),
            "sort_order": (
                "occurrence_count_descending"
            ),
            "sort_order_note": (
                "Occurrence count is used only "
                "to make the probe easier to "
                "inspect. It is not a priority "
                "or severity score."
            ),
            "note": (
                "Known related System Log records "
                "are grouped using conservative "
                "deterministic rules. Unclassified "
                "rows remain separate unless their "
                "logger, level, source location and "
                "cleaned message evidence are exactly "
                "the same within the snapshot."
            ),
        },
        "source_collection": {
            "status": source_status,
            "error": collection.get(
                "error"
            ),
        },
        "summary": {},
        "families": [],
    }

    if source_status != "ok":
        return report

    entries = log_audit.get(
        "entries",
        [],
    )

    if not isinstance(
        entries,
        list,
    ):
        entries = []

    grouped = {}

    for index, entry in enumerate(
        entries
    ):
        if not isinstance(
            entry,
            dict,
        ):
            continue

        definition = classify_entry(
            entry,
            index,
        )

        family_id = definition[
            "id"
        ]

        if family_id not in grouped:
            grouped[
                family_id
            ] = {
                "definition": (
                    definition
                ),
                "members": [],
            }

        grouped[
            family_id
        ][
            "members"
        ].append(
            {
                "index": index,
                "entry": entry,
            }
        )

    families = []

    for group in grouped.values():
        families.append(
            build_family(
                group[
                    "definition"
                ],
                group[
                    "members"
                ],
            )
        )

    families.sort(
        key=lambda item: (
            -int(
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

    deterministic = [
        family
        for family in families
        if family.get(
            "grouping_method"
        )
        == "deterministic_rule"
    ]

    fallback = [
        family
        for family in families
        if family.get(
            "grouping_method"
        )
        == "single_entry_fallback"
    ]

    multi_entry = [
        family
        for family in families
        if family.get(
            "source_entry_count",
            0,
        )
        > 1
    ]

    report[
        "summary"
    ] = {
        "source_entry_count": len(
            entries
        ),
        "family_count": len(
            families
        ),
        "deterministic_family_count": len(
            deterministic
        ),
        "unclassified_family_count": len(
            fallback
        ),
        "multi_entry_family_count": len(
            multi_entry
        ),
        "source_occurrence_count": sum(
            safe_count(
                entry
            )
            for entry in entries
            if isinstance(
                entry,
                dict,
            )
        ),
        "family_occurrence_count": sum(
            int(
                family.get(
                    "occurrence_count",
                    0,
                )
            )
            for family in families
        ),
    }

    report[
        "families"
    ] = families

    return report


def main():
    try:
        log_audit = load_json(
            INPUT_FILE
        )
    except Exception as exc:
        log_audit = {
            "collection": {
                "status": (
                    "input_unavailable"
                ),
                "error": str(
                    exc
                ),
            },
            "entries": [],
        }

    report = build_family_report(
        log_audit
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
