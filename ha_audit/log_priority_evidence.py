import json
import os
import re
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

FAMILY_FILE = (
    "/config/log_issue_families.json"
)

OWNERSHIP_FILE = (
    "/config/log_issue_ownership.json"
)

OUTPUT_FILE = (
    "/config/log_priority_evidence.json"
)


OBSERVED = "OBSERVED"
NOT_OBSERVED = "NOT OBSERVED"
UNKNOWN = "UNKNOWN"

PERSISTENCE_MULTI_DAY = "MULTI-DAY"
PERSISTENCE_SAME_DAY = "SAME-DAY"
PERSISTENCE_UNKNOWN = "UNKNOWN"

BREADTH_MULTIPLE = "MULTIPLE TARGETS"
BREADTH_SINGLE = "SINGLE TARGET"
BREADTH_UNKNOWN = "UNKNOWN"

ACTION_CLEAR_LOCAL = "CLEAR LOCAL ACTION PATH"
ACTION_INVESTIGATE_LOCAL = "LOCAL INVESTIGATION"
ACTION_LIMITED_LOCAL = "LIMITED LOCAL CONTROL"
ACTION_PLATFORM = "PLATFORM / UPSTREAM"
ACTION_UNKNOWN = "UNKNOWN"


ENTITY_RE = re.compile(
    r"\b("
    r"light"
    r"|media_player"
    r"|sensor"
    r"|binary_sensor"
    r"|switch"
    r"|vacuum"
    r"|climate"
    r"|automation"
    r"|script"
    r"|number"
    r"|select"
    r"|button"
    r")\."
    r"[a-z0-9_]+\b",
    re.IGNORECASE,
)

IP_RE = re.compile(
    r"\b"
    r"(?:"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"\."
    r"){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"\b"
)


KNOWN_MULTIPLE_TARGET_FAMILIES = {
    "zigbee_delivery",
    "apple_tv",
    "hue_sync",
    "missing_targets",
    "slow_entity_update",
    "esphome",
}


DIRECT_FAILURE_MARKERS = (
    "error executing",
    "failed to",
    "fails",
    "failure",
    "cannot be controlled",
    "cannot connect",
    "can't connect",
    "connection lost",
    "timed out",
    "timeout",
    "missing or not currently available",
    "invalid authentication",
    "received invalid sensor state",
    "error fetching",
    "error requesting",
    "failed to retrieve",
)


RECOVERY_MARKERS = (
    "re-established",
    "reestablished",
    "reconnected",
    "connection restored",
    "recovered",
)


FALLBACK_MARKERS = (
    "using cached",
    "using cache",
    "fallback",
    "fall back",
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


def family_text(
    family,
):
    parts = []

    for key in (
        "title",
        "logger_names",
        "sources",
        "message_samples",
    ):
        value = family.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            parts.extend(
                value
            )
        elif value:
            parts.append(
                value
            )

    return " ".join(
        clean_text(
            item
        )
        for item in parts
        if clean_text(
            item
        )
    )


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


def observed_span_hours(
    family,
):
    first_seen = parse_timestamp(
        family.get(
            "first_seen"
        )
    )

    last_seen = parse_timestamp(
        family.get(
            "last_seen"
        )
    )

    if (
        first_seen is None
        or last_seen is None
    ):
        return None

    seconds = (
        last_seen
        - first_seen
    ).total_seconds()

    if seconds < 0:
        return None

    return round(
        seconds / 3600,
        2,
    )


def persistence_evidence(
    family,
):
    hours = observed_span_hours(
        family
    )

    if hours is None:
        return (
            PERSISTENCE_UNKNOWN,
            None,
        )

    if hours >= 24:
        return (
            PERSISTENCE_MULTI_DAY,
            hours,
        )

    return (
        PERSISTENCE_SAME_DAY,
        hours,
    )


def marker_evidence(
    text,
    markers,
):
    lowered = text.lower()

    if any(
        marker
        in lowered
        for marker in markers
    ):
        return OBSERVED

    return NOT_OBSERVED


def direct_failure_evidence(
    family,
):
    return marker_evidence(
        family_text(
            family
        ),
        DIRECT_FAILURE_MARKERS,
    )


def recovery_evidence(
    family,
):
    return marker_evidence(
        family_text(
            family
        ),
        RECOVERY_MARKERS,
    )


def fallback_evidence(
    family,
):
    return marker_evidence(
        family_text(
            family
        ),
        FALLBACK_MARKERS,
    )


def extracted_targets(
    family,
):
    text = family_text(
        family
    )

    targets = set()

    for match in ENTITY_RE.finditer(
        text
    ):
        targets.add(
            match.group(
                0
            ).lower()
        )

    for match in IP_RE.finditer(
        text
    ):
        targets.add(
            match.group(
                0
            )
        )

    return sorted(
        targets
    )


def breadth_evidence(
    family,
):
    family_id = clean_text(
        family.get(
            "family_id",
            "",
        )
    )

    targets = extracted_targets(
        family
    )

    if (
        family_id
        in KNOWN_MULTIPLE_TARGET_FAMILIES
    ):
        return (
            BREADTH_MULTIPLE,
            targets,
        )

    if len(
        targets
    ) >= 2:
        return (
            BREADTH_MULTIPLE,
            targets,
        )

    if len(
        targets
    ) == 1:
        return (
            BREADTH_SINGLE,
            targets,
        )

    return (
        BREADTH_UNKNOWN,
        targets,
    )


def local_action_path(
    ownership,
):
    domain = clean_text(
        ownership.get(
            "ownership",
            "",
        )
    )

    confidence = clean_text(
        ownership.get(
            "ownership_confidence",
            "",
        )
    )

    if (
        domain
        == "USER / LOCAL CONFIGURATION"
    ):
        if confidence == "HIGH":
            return ACTION_CLEAR_LOCAL

        return ACTION_INVESTIGATE_LOCAL

    if (
        domain
        == "DEVICE / LOCAL NETWORK"
    ):
        return ACTION_INVESTIGATE_LOCAL

    if domain == "EXTERNAL SERVICE":
        return ACTION_LIMITED_LOCAL

    if (
        domain
        == "HOME ASSISTANT PLATFORM"
    ):
        return ACTION_PLATFORM

    return ACTION_UNKNOWN


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


def build_record(
    family,
    ownership,
):
    persistence, span_hours = (
        persistence_evidence(
            family
        )
    )

    breadth, targets = (
        breadth_evidence(
            family
        )
    )

    levels = family.get(
        "level_occurrences",
        {},
    )

    if not isinstance(
        levels,
        dict,
    ):
        levels = {}

    return {
        "family_id": family.get(
            "family_id"
        ),
        "title": family.get(
            "title"
        ),
        "source_entry_count": safe_int(
            family.get(
                "source_entry_count",
                0,
            )
        ),
        "occurrence_count": safe_int(
            family.get(
                "occurrence_count",
                0,
            )
        ),
        "error_occurrences": safe_int(
            levels.get(
                "ERROR",
                0,
            )
        ),
        "warning_occurrences": safe_int(
            levels.get(
                "WARNING",
                0,
            )
        ),
        "first_seen": family.get(
            "first_seen"
        ),
        "last_seen": family.get(
            "last_seen"
        ),
        "observed_span_hours": (
            span_hours
        ),
        "persistence_evidence": (
            persistence
        ),
        "direct_failure_evidence": (
            direct_failure_evidence(
                family
            )
        ),
        "recovery_evidence": (
            recovery_evidence(
                family
            )
        ),
        "fallback_evidence": (
            fallback_evidence(
                family
            )
        ),
        "breadth_evidence": breadth,
        "observed_targets": targets,
        "ownership": ownership.get(
            "ownership"
        ),
        "ownership_confidence": (
            ownership.get(
                "ownership_confidence"
            )
        ),
        "local_action_path": (
            local_action_path(
                ownership
            )
        ),
    }


def build_report(
    family_report,
    ownership_report,
):
    family_source = (
        family_report.get(
            "source_collection",
            {},
        )
    )

    ownership_source = (
        ownership_report.get(
            "source_collection",
            {},
        )
    )

    if not isinstance(
        family_source,
        dict,
    ):
        family_source = {}

    if not isinstance(
        ownership_source,
        dict,
    ):
        ownership_source = {}

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_priority_evidence_probe"
            ),
            "family_input": (
                "log_issue_families.json"
            ),
            "ownership_input": (
                "log_issue_ownership.json"
            ),
            "evidence_features_produced": True,
            "priority_produced": False,
            "severity_produced": False,
            "action_recommendation_produced": (
                False
            ),
            "note": (
                "These fields are evidence inputs "
                "for a future priority model. No "
                "field is itself a priority score."
            ),
            "absence_note": (
                "NOT OBSERVED means the evidence "
                "was not present in the bounded "
                "System Log sample. It does not "
                "prove that recovery, fallback or "
                "failure never occurred."
            ),
        },
        "source_status": {
            "family_status": (
                family_source.get(
                    "status",
                    "unknown",
                )
            ),
            "ownership_status": (
                ownership_source.get(
                    "status",
                    "unknown",
                )
            ),
        },
        "summary": {},
        "families": [],
    }

    if (
        family_source.get(
            "status"
        )
        != "ok"
        or ownership_source.get(
            "status"
        )
        != "ok"
    ):
        return report

    families = family_report.get(
        "families",
        [],
    )

    ownership_families = (
        ownership_report.get(
            "families",
            [],
        )
    )

    if not isinstance(
        families,
        list,
    ):
        families = []

    if not isinstance(
        ownership_families,
        list,
    ):
        ownership_families = []

    ownership_by_id = {
        item.get(
            "family_id"
        ): item
        for item in ownership_families
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "family_id"
        )
    }

    records = []
    missing_ownership = []

    for family in families:
        if not isinstance(
            family,
            dict,
        ):
            continue

        family_id = family.get(
            "family_id"
        )

        ownership = ownership_by_id.get(
            family_id
        )

        if ownership is None:
            missing_ownership.append(
                family_id
            )
            continue

        records.append(
            build_record(
                family,
                ownership,
            )
        )

    family_ids = {
        family.get(
            "family_id"
        )
        for family in families
        if isinstance(
            family,
            dict,
        )
        and family.get(
            "family_id"
        )
    }

    extra_ownership = sorted(
        family_id
        for family_id
        in ownership_by_id
        if family_id
        not in family_ids
    )

    records.sort(
        key=lambda item: (
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

    report[
        "summary"
    ] = {
        "family_count": len(
            records
        ),
        "missing_ownership_count": len(
            missing_ownership
        ),
        "missing_ownership_family_ids": (
            missing_ownership
        ),
        "extra_ownership_count": len(
            extra_ownership
        ),
        "extra_ownership_family_ids": (
            extra_ownership
        ),
        "multi_day_family_count": sum(
            1
            for item in records
            if item[
                "persistence_evidence"
            ]
            == PERSISTENCE_MULTI_DAY
        ),
        "direct_failure_family_count": sum(
            1
            for item in records
            if item[
                "direct_failure_evidence"
            ]
            == OBSERVED
        ),
        "recovery_observed_family_count": sum(
            1
            for item in records
            if item[
                "recovery_evidence"
            ]
            == OBSERVED
        ),
        "fallback_observed_family_count": sum(
            1
            for item in records
            if item[
                "fallback_evidence"
            ]
            == OBSERVED
        ),
        "multiple_target_family_count": sum(
            1
            for item in records
            if item[
                "breadth_evidence"
            ]
            == BREADTH_MULTIPLE
        ),
        "priority_produced": False,
    }

    report[
        "families"
    ] = records

    return report


def main():
    try:
        family_report = load_json(
            FAMILY_FILE
        )
    except Exception as exc:
        family_report = {
            "source_collection": {
                "status": (
                    "input_unavailable"
                ),
                "error": str(
                    exc
                ),
            },
            "families": [],
        }

    try:
        ownership_report = load_json(
            OWNERSHIP_FILE
        )
    except Exception as exc:
        ownership_report = {
            "source_collection": {
                "status": (
                    "input_unavailable"
                ),
                "error": str(
                    exc
                ),
            },
            "families": [],
        }

    report = build_report(
        family_report,
        ownership_report,
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
