import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"
REFERENCE_FILE = "/config/not_provided_reference_audit.json"
RECORDER_FILE = "/config/recorder_health_audit.json"
HISTORY_FILE = "/config/not_provided_history_audit.json"
AVAILABILITY_FILE = "/config/availability_audit.json"

OUTPUT_FILE = "/config/ha_audit_latest.txt"


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


def count_mapping(value):
    if isinstance(
        value,
        dict,
    ):
        return len(
            value
        )

    return 0


def parse_iso(value):
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

    except Exception:
        return None


def format_local_time(
    value,
    timezone_name,
    include_seconds=False,
):
    stamp = parse_iso(
        value
    )

    if not stamp:
        if value:
            return str(
                value
            )

        return "unknown"

    try:
        local_stamp = stamp.astimezone(
            ZoneInfo(
                timezone_name
            )
        )

    except Exception:
        local_stamp = stamp
