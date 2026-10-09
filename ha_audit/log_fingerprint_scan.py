import hashlib
import json
import os
import re
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

INPUT_FILE = (
    "/config/log_issue_families.json"
)

OUTPUT_FILE = (
    "/config/log_family_fingerprints.json"
)


FINGERPRINT_SCHEMA_VERSION = 1

FINGERPRINT_PREFIX = "lfp_"

FINGERPRINT_HEX_LENGTH = 20


SOURCE_LINE_RE = re.compile(
    r":\d+$"
)

LEADING_NUMERIC_ID_RE = re.compile(
    r"^\[\d+\]\s*"
)

IPV4_RE = re.compile(
    r"\b"
    r"(?:"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"\."
    r"){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"\b"
)

UUID_RE = re.compile(
    r"\b"
    r"[0-9a-f]{8}-"
    r"[0-9a-f]{4}-"
    r"[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-"
    r"[0-9a-f]{12}"
    r"\b",
    re.IGNORECASE,
)

MAC_RE = re.compile(
    r"\b"
    r"(?:[0-9a-f]{2}:){5}"
    r"[0-9a-f]{2}"
    r"\b",
    re.IGNORECASE,
)

LONG_HEX_RE = re.compile(
    r"\b[0-9a-f]{16,}\b",
    re.IGNORECASE,
)

LONG_NUMBER_RE = re.compile(
    r"\b\d{10,}\b"
)

HOME_ASSISTANT_VERSION_RE = re.compile(
    r"(home assistant/)"
    r"\d+(?:\.\d+){1,3}",
    re.IGNORECASE,
)

BUILD_VERSION_RE = re.compile(
    r"(build:)"
    r"\d+(?:\.\d+){1,3}",
    re.IGNORECASE,
)

OS_VERSION_RE = re.compile(
    r"\b"
    r"(ios|macos|android)"
    r"\s+"
    r"\d+(?:\.\d+){1,3}",
    re.IGNORECASE,
)

INVALID_NUMERIC_SENSOR_RE = re.compile(
    r"received invalid sensor state:"
    r"\s+\S+"
    r"\s+for entity"
    r"\s+([a-z0-9_]+\.[a-z0-9_]+)"
    r",\s*expected a number",
    re.IGNORECASE,
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


def list_values(
    family,
    key,
):
    value = family.get(
        key,
        [],
    )

    if not isinstance(
        value,
        list,
    ):
        return []

    return [
        clean_text(
            item
        )
        for item in value
        if clean_text(
            item
        )
    ]


def normalize_source(
    value,
):
    value = clean_text(
        value
    ).lower()

    return SOURCE_LINE_RE.sub(
        "",
        value,
    )


def normalize_message(
    value,
):
    value = clean_text(
        value
    )

    if not value:
        return ""

    lowered = value.lower()

    if (
        "no pong received after"
        in lowered
        and "disconnected"
        in lowered
    ):
        return (
            "websocket client disconnected: "
            "no pong received"
        )

    invalid_sensor = (
        INVALID_NUMERIC_SENSOR_RE.search(
            lowered
        )
    )

    if invalid_sensor:
        entity_id = invalid_sensor.group(
            1
        )

        return (
            "received invalid sensor state "
            f"for entity {entity_id}, "
            "expected a number"
        )

    if lowered.endswith(
        ": already running"
    ):
        return "automation or script already running"

    value = LEADING_NUMERIC_ID_RE.sub(
        "",
        value,
    )

    value = UUID_RE.sub(
        "<uuid>",
        value,
    )

    value = MAC_RE.sub(
        "<mac>",
        value,
    )

    value = IPV4_RE.sub(
        "<ip>",
        value,
    )

    value = HOME_ASSISTANT_VERSION_RE.sub(
        r"\1<version>",
        value,
    )

    value = BUILD_VERSION_RE.sub(
        r"\1<version>",
        value,
    )

    value = OS_VERSION_RE.sub(
        lambda match: (
            f"{match.group(1)} <version>"
        ),
        value,
    )

    value = LONG_HEX_RE.sub(
        "<hex>",
        value,
    )

    value = LONG_NUMBER_RE.sub(
        "<number>",
        value,
    )

    return clean_text(
        value
    ).lower()


def deterministic_identity(
    family,
):
    rule_id = clean_text(
        family.get(
            "rule_id",
            "",
        )
    )

    family_id = clean_text(
        family.get(
            "family_id",
            "",
        )
    )

    if rule_id:
        return rule_id.lower()

    return family_id.lower()


def fallback_identity_payload(
    family,
):
    loggers = sorted(
        {
            value.lower()
            for value
            in list_values(
                family,
                "logger_names",
            )
        }
    )

    sources = sorted(
        {
            normalize_source(
                value
            )
            for value
            in list_values(
                family,
                "sources",
            )
            if normalize_source(
                value
            )
        }
    )

    message_patterns = sorted(
        {
            normalize_message(
                value
            )
            for value
            in list_values(
                family,
                "message_samples",
            )
            if normalize_message(
                value
            )
        }
    )

    return {
        "loggers": loggers,
        "sources": sources,
        "message_patterns": (
            message_patterns
        ),
    }


def fingerprint_digest(
    payload,
):
    if not isinstance(
        payload,
        str,
    ):
        payload = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
            ensure_ascii=True,
        )

    digest = hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()

    return (
        FINGERPRINT_PREFIX
        + digest[
            :FINGERPRINT_HEX_LENGTH
        ]
    )


def fingerprint_family(
    family,
):
    grouping_method = clean_text(
        family.get(
            "grouping_method",
            "",
        )
    )

    family_id = clean_text(
        family.get(
            "family_id",
            "",
        )
    )

    rule_id = clean_text(
        family.get(
            "rule_id",
            "",
        )
    )

    if (
        grouping_method
        == "deterministic_rule"
        or rule_id
    ):
        identity = (
            deterministic_identity(
                family
            )
        )

        fingerprint = (
            fingerprint_digest(
                (
                    "deterministic_rule|"
                    f"{identity}"
                )
            )
        )

        return {
            "stable_fingerprint": (
                fingerprint
            ),
            "fingerprint_method": (
                "deterministic_rule_v1"
            ),
        }

    payload = (
        fallback_identity_payload(
            family
        )
    )

    fingerprint = (
        fingerprint_digest(
            {
                "method": (
                    "fallback_evidence_v1"
                ),
                "evidence": payload,
            }
        )
    )

    return {
        "stable_fingerprint": (
            fingerprint
        ),
        "fingerprint_method": (
            "fallback_evidence_v1"
        ),
    }


def build_record(
    family,
):
    result = fingerprint_family(
        family
    )

    return {
        "family_id": family.get(
            "family_id"
        ),
        "title": family.get(
            "title"
        ),
        "grouping_method": family.get(
            "grouping_method"
        ),
        "rule_id": family.get(
            "rule_id"
        ),
        "stable_fingerprint": result[
            "stable_fingerprint"
        ],
        "fingerprint_method": result[
            "fingerprint_method"
        ],
        "fingerprint_schema_version": (
            FINGERPRINT_SCHEMA_VERSION
        ),
    }


def duplicate_groups(
    records,
):
    grouped = {}

    for record in records:
        fingerprint = record.get(
            "stable_fingerprint"
        )

        if not fingerprint:
            continue

        grouped.setdefault(
            fingerprint,
            [],
        ).append(
            record.get(
                "family_id"
            )
        )

    duplicates = []

    for (
        fingerprint,
        family_ids,
    ) in grouped.items():
        if len(
            family_ids
        ) <= 1:
            continue

        duplicates.append(
            {
                "stable_fingerprint": (
                    fingerprint
                ),
                "family_ids": sorted(
                    family_ids
                ),
            }
        )

    duplicates.sort(
        key=lambda item: (
            item[
                "stable_fingerprint"
            ]
        )
    )

    return duplicates


def build_report(
    family_report,
):
    source_collection = (
        family_report.get(
            "source_collection",
            {},
        )
    )

    if not isinstance(
        source_collection,
        dict,
    ):
        source_collection = {}

    source_status = (
        source_collection.get(
            "status",
            "unknown",
        )
    )

    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "system_log_stable_fingerprint_probe"
            ),
            "input": (
                "log_issue_families.json"
            ),
            "fingerprint_schema_version": (
                FINGERPRINT_SCHEMA_VERSION
            ),
            "stable_fingerprints_produced": (
                True
            ),
            "history_written": False,
            "persistence_judgement_produced": (
                False
            ),
            "priority_changed": False,
            "note": (
                "Stable fingerprints are intended "
                "to identify the same issue family "
                "across separate HA Audit runs. "
                "No historical state is written by "
                "this probe."
            ),
            "privacy_note": (
                "Fingerprint source evidence is "
                "hashed and is not written to the "
                "output. Raw message text, IP "
                "addresses and other source details "
                "are not persisted here."
            ),
        },
        "source_collection": {
            "status": source_status,
            "error": source_collection.get(
                "error"
            ),
        },
        "summary": {},
        "families": [],
        "duplicate_fingerprint_groups": [],
    }

    if source_status != "ok":
        return report

    families = family_report.get(
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
            family
        )
        for family in families
        if isinstance(
            family,
            dict,
        )
    ]

    duplicates = duplicate_groups(
        records
    )

    report[
        "summary"
    ] = {
        "family_count": len(
            records
        ),
        "stable_fingerprint_count": len(
            {
                record[
                    "stable_fingerprint"
                ]
                for record in records
            }
        ),
        "deterministic_fingerprint_count": (
            sum(
                1
                for record in records
                if record[
                    "fingerprint_method"
                ]
                == "deterministic_rule_v1"
            )
        ),
        "fallback_fingerprint_count": (
            sum(
                1
                for record in records
                if record[
                    "fingerprint_method"
                ]
                == "fallback_evidence_v1"
            )
        ),
        "duplicate_fingerprint_group_count": (
            len(
                duplicates
            )
        ),
        "history_written": False,
    }

    report[
        "families"
    ] = records

    report[
        "duplicate_fingerprint_groups"
    ] = duplicates

    return report


def main():
    try:
        family_report = load_json(
            INPUT_FILE
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

    report = build_report(
        family_report
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
