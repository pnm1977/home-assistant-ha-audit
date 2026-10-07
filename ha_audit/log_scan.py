import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

import requests


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

SUPERVISOR_URL = os.environ.get(
    "SUPERVISOR_URL",
    "http://supervisor",
)

SUPERVISOR_TOKEN = os.environ.get(
    "SUPERVISOR_TOKEN",
)

OUTPUT_FILE = (
    "/config/log_audit.json"
)

LINES_REQUESTED = 2000

MAX_GROUPS = 100
MAX_UNPARSED_SAMPLES = 10
MAX_SAMPLE_LENGTH = 500


ANSI_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
)

HA_LOG_RE = re.compile(
    r"(?P<timestamp>"
    r"\d{4}-\d{2}-\d{2}"
    r"[ T]"
    r"\d{2}:\d{2}:\d{2}"
    r"(?:[.,]\d+)?"
    r")"
    r"\s+"
    r"(?P<level>"
    r"DEBUG|INFO|WARNING|ERROR|CRITICAL"
    r")"
    r"\s+"
    r"\((?P<thread>[^)]*)\)"
    r"\s+"
    r"\[(?P<source>[^\]]+)\]"
    r"\s+"
    r"(?P<message>.*)"
)

FALLBACK_LOG_RE = re.compile(
    r"\b"
    r"(?P<level>"
    r"DEBUG|INFO|WARNING|ERROR|CRITICAL"
    r")"
    r"\b"
    r".*?"
    r"\[(?P<source>[^\]]+)\]"
    r"\s+"
    r"(?P<message>.*)"
)

SECRET_RE = re.compile(
    r"(?i)"
    r"\b("
    r"access[_-]?token"
    r"|token"
    r"|api[_-]?key"
    r"|password"
    r"|secret"
    r"|authorization"
    r")"
    r"\s*[:=]\s*"
    r"([^\s,&]+)"
)

BEARER_RE = re.compile(
    r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"
)

URL_QUERY_RE = re.compile(
    r"([?&][A-Za-z0-9_.~-]+)=([^&\s]+)"
)


def utc_now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def clean_text(value):
    value = ANSI_RE.sub(
        "",
        str(
            value or ""
        ),
    )

    return " ".join(
        value.split()
    )


def redact_message(value):
    value = clean_text(
        value
    )

    value = BEARER_RE.sub(
        "Bearer [REDACTED]",
        value,
    )

    value = SECRET_RE.sub(
        lambda match: (
            f"{match.group(1)}=[REDACTED]"
        ),
        value,
    )

    value = URL_QUERY_RE.sub(
        lambda match: (
            f"{match.group(1)}=[REDACTED]"
        ),
        value,
    )

    return value


def truncate_sample(value):
    value = redact_message(
        value
    )

    if len(
        value
    ) <= MAX_SAMPLE_LENGTH:
        return value

    return (
        value[
            :MAX_SAMPLE_LENGTH - 3
        ]
        + "..."
    )


def parse_log_line(line):
    clean_line = clean_text(
        line
    )

    if not clean_line:
        return None

    match = HA_LOG_RE.search(
        clean_line
    )

    if match:
        return {
            "timestamp": (
                match.group(
                    "timestamp"
                )
            ),
            "level": (
                match.group(
                    "level"
                )
            ),
            "source": (
                match.group(
                    "source"
                )
            ),
            "thread": (
                match.group(
                    "thread"
                )
            ),
            "message": redact_message(
                match.group(
                    "message"
                )
            ),
        }

    match = FALLBACK_LOG_RE.search(
        clean_line
    )

    if match:
        return {
            "timestamp": None,
            "level": (
                match.group(
                    "level"
                )
            ),
            "source": (
                match.group(
                    "source"
                )
            ),
            "thread": None,
            "message": redact_message(
                match.group(
                    "message"
                )
            ),
        }

    return None


def group_key(
    item,
):
    return (
        item.get(
            "level",
            "UNKNOWN",
        ),
        item.get(
            "source",
            "unknown",
        ),
        clean_text(
            item.get(
                "message",
                "",
            )
        ),
    )


def analyse_log_text(
    log_text,
):
    raw_lines = str(
        log_text or ""
    ).splitlines()

    nonempty_lines = [
        line
        for line in raw_lines
        if line.strip()
    ]

    parsed = []
    unparsed_samples = []

    for line in nonempty_lines:
        item = parse_log_line(
            line
        )

        if item is None:
            if (
                len(
                    unparsed_samples
                )
                < MAX_UNPARSED_SAMPLES
            ):
                unparsed_samples.append(
                    truncate_sample(
                        line
                    )
                )

            continue

        parsed.append(
            item
        )

    groups = {}

    for item in parsed:
        key = group_key(
            item
        )

        if key not in groups:
            groups[
                key
            ] = {
                "level": key[0],
                "source": key[1],
                "message": key[2],
                "count": 0,
                "first_seen": None,
                "last_seen": None,
                "sample": truncate_sample(
                    key[2]
                ),
            }

        group = groups[
            key
        ]

        group[
            "count"
        ] += 1

        timestamp = item.get(
            "timestamp"
        )

        if timestamp:
            if (
                group[
                    "first_seen"
                ]
                is None
                or timestamp
                < group[
                    "first_seen"
                ]
            ):
                group[
                    "first_seen"
                ] = timestamp

            if (
                group[
                    "last_seen"
                ]
                is None
                or timestamp
                > group[
                    "last_seen"
                ]
            ):
                group[
                    "last_seen"
                ] = timestamp

    level_counts = Counter(
        item.get(
            "level",
            "UNKNOWN",
        )
        for item in parsed
    )

    grouped_rows = list(
        groups.values()
    )

    grouped_rows.sort(
        key=lambda item: (
            -int(
                item.get(
                    "count",
                    0,
                )
            ),
            str(
                item.get(
                    "level",
                    "",
                )
            ),
            str(
                item.get(
                    "source",
                    "",
                )
            ),
            str(
                item.get(
                    "message",
                    "",
                )
            ),
        )
    )

    repeated_groups = [
        item
        for item in grouped_rows
        if item.get(
            "count",
            0,
        )
        > 1
    ]

    parsed_count = len(
        parsed
    )

    total_count = len(
        nonempty_lines
    )

    if total_count:
        parse_rate = round(
            (
                parsed_count
                / total_count
            )
            * 100,
            1,
        )
    else:
        parse_rate = 0.0

    return {
        "line_count": len(
            raw_lines
        ),
        "nonempty_line_count": (
            total_count
        ),
        "parsed_line_count": (
            parsed_count
        ),
        "unparsed_line_count": (
            total_count
            - parsed_count
        ),
        "parse_rate_percent": (
            parse_rate
        ),
        "level_counts": dict(
            sorted(
                level_counts.items()
            )
        ),
        "unique_group_count": len(
            grouped_rows
        ),
        "repeated_group_count": len(
            repeated_groups
        ),
        "highest_repeat_count": (
            repeated_groups[
                0
            ].get(
                "count",
                0,
            )
            if repeated_groups
            else 0
        ),
        "groups": grouped_rows[
            :MAX_GROUPS
        ],
        "unparsed_samples": (
            unparsed_samples
        ),
    }


def fetch_core_logs(
    *,
    session=requests,
    token=None,
    lines=LINES_REQUESTED,
):
    token = (
        token
        if token is not None
        else SUPERVISOR_TOKEN
    )

    if not token:
        return {
            "status": (
                "token_unavailable"
            ),
            "http_status": None,
            "text": "",
            "error": (
                "SUPERVISOR_TOKEN is not "
                "available to HA Audit."
            ),
        }

    url = (
        f"{SUPERVISOR_URL}"
        f"/core/logs"
    )

    headers = {
        "Authorization": (
            f"Bearer {token}"
        ),
        "Accept": (
            "text/x-log"
        ),
    }

    params = {
        "verbose": "",
        "lines": int(
            lines
        ),
        "no_colors": "",
    }

    try:
        response = session.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )
    except Exception as exc:
        return {
            "status": (
                "request_failed"
            ),
            "http_status": None,
            "text": "",
            "error": str(
                exc
            ),
        }

    if response.status_code != 200:
        if response.status_code in (
            401,
            403,
        ):
            status = (
                "permission_denied"
            )
        else:
            status = (
                "http_error"
            )

        return {
            "status": status,
            "http_status": (
                response.status_code
            ),
            "text": "",
            "error": (
                f"Supervisor Core log "
                f"request returned HTTP "
                f"{response.status_code}."
            ),
        }

    return {
        "status": "ok",
        "http_status": (
            response.status_code
        ),
        "text": (
            response.text
            or ""
        ),
        "error": None,
    }


def build_report(
    collection,
    *,
    lines_requested=LINES_REQUESTED,
):
    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "core_log_collection_probe"
            ),
            "source": (
                "Home Assistant Core"
            ),
            "endpoint": (
                "/core/logs"
            ),
            "lines_requested": (
                int(
                    lines_requested
                )
            ),
            "verbose": True,
            "no_colors": True,
            "judgement_produced": False,
            "severity_produced": False,
            "note": (
                "This probe groups recent Core "
                "log evidence. It does not decide "
                "whether a message is harmful, "
                "resource-intensive, user-fixable, "
                "or relevant to an update."
            ),
        },
        "collection": {
            "status": collection.get(
                "status"
            ),
            "http_status": (
                collection.get(
                    "http_status"
                )
            ),
            "error": (
                collection.get(
                    "error"
                )
            ),
        },
        "summary": {},
        "groups": [],
        "unparsed_samples": [],
    }

    if collection.get(
        "status"
    ) != "ok":
        return report

    analysis = analyse_log_text(
        collection.get(
            "text",
            "",
        )
    )

    report[
        "summary"
    ] = {
        key: value
        for key, value
        in analysis.items()
        if key not in (
            "groups",
            "unparsed_samples",
        )
    }

    report[
        "groups"
    ] = analysis.get(
        "groups",
        [],
    )

    report[
        "unparsed_samples"
    ] = analysis.get(
        "unparsed_samples",
        [],
    )

    return report


def main():
    collection = fetch_core_logs(
        lines=LINES_REQUESTED
    )

    report = build_report(
        collection,
        lines_requested=(
            LINES_REQUESTED
        ),
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
