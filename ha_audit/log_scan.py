import json
import os
import re
from datetime import datetime, timezone

import websocket


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ.get(
    "SUPERVISOR_TOKEN",
)

WS_URL = (
    "ws://supervisor/core/websocket"
)

OUTPUT_FILE = (
    "/config/log_audit.json"
)

MAX_ENTRIES = 100
MAX_MESSAGES_PER_ENTRY = 5
MAX_MESSAGE_LENGTH = 750
MAX_EXCEPTION_LENGTH = 2000


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


def redact_text(
    value,
):
    text = str(
        value or ""
    )

    text = BEARER_RE.sub(
        "Bearer [REDACTED]",
        text,
    )

    text = SECRET_RE.sub(
        lambda match: (
            f"{match.group(1)}=[REDACTED]"
        ),
        text,
    )

    text = URL_QUERY_RE.sub(
        lambda match: (
            f"{match.group(1)}=[REDACTED]"
        ),
        text,
    )

    return text


def truncate_text(
    value,
    limit,
):
    text = redact_text(
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


def timestamp_to_iso(
    value,
):
    if value in (
        None,
        "",
    ):
        return None

    try:
        return datetime.fromtimestamp(
            float(
                value
            ),
            tz=timezone.utc,
        ).isoformat()
    except (
        TypeError,
        ValueError,
        OSError,
    ):
        return None


def normalise_source(
    value,
):
    if isinstance(
        value,
        (
            list,
            tuple,
        ),
    ):
        if len(
            value
        ) >= 2:
            return {
                "file": str(
                    value[
                        0
                    ]
                ),
                "line": value[
                    1
                ],
            }

        if len(
            value
        ) == 1:
            return {
                "file": str(
                    value[
                        0
                    ]
                ),
                "line": None,
            }

    if value:
        return {
            "file": str(
                value
            ),
            "line": None,
        }

    return {
        "file": None,
        "line": None,
    }


def normalise_messages(
    value,
):
    if isinstance(
        value,
        list,
    ):
        candidates = value
    elif value is None:
        candidates = []
    else:
        candidates = [
            value
        ]

    result = []

    for item in candidates:
        text = truncate_text(
            item,
            MAX_MESSAGE_LENGTH,
        )

        if not text:
            continue

        if text in result:
            continue

        result.append(
            text
        )

        if (
            len(
                result
            )
            >= MAX_MESSAGES_PER_ENTRY
        ):
            break

    return result


def normalise_entry(
    item,
):
    if not isinstance(
        item,
        dict,
    ):
        return None

    try:
        count = max(
            1,
            int(
                item.get(
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
        count = 1

    level = str(
        item.get(
            "level",
            "UNKNOWN",
        )
        or "UNKNOWN"
    ).upper()

    messages = normalise_messages(
        item.get(
            "message"
        )
    )

    exception = truncate_text(
        item.get(
            "exception",
            "",
        ),
        MAX_EXCEPTION_LENGTH,
    )

    return {
        "level": level,
        "name": str(
            item.get(
                "name",
                "unknown",
            )
            or "unknown"
        ),
        "source": normalise_source(
            item.get(
                "source"
            )
        ),
        "count": count,
        "first_seen": timestamp_to_iso(
            item.get(
                "first_occurred"
            )
        ),
        "last_seen": timestamp_to_iso(
            item.get(
                "timestamp"
            )
        ),
        "messages": messages,
        "exception": exception,
    }


def collect_system_log(
    *,
    ws_factory=websocket.create_connection,
    token=None,
):
    token = (
        token
        if token is not None
        else TOKEN
    )

    if not token:
        return {
            "status": (
                "token_unavailable"
            ),
            "entries": [],
            "error": (
                "SUPERVISOR_TOKEN is not "
                "available to HA Audit."
            ),
        }

    try:
        ws = ws_factory(
            WS_URL,
            timeout=30,
            suppress_origin=True,
        )
    except Exception as exc:
        return {
            "status": (
                "connection_failed"
            ),
            "entries": [],
            "error": str(
                exc
            ),
        }

    try:
        greeting = json.loads(
            ws.recv()
        )

        if greeting.get(
            "type"
        ) != "auth_required":
            return {
                "status": (
                    "unexpected_greeting"
                ),
                "entries": [],
                "error": (
                    "Unexpected Home Assistant "
                    "WebSocket greeting."
                ),
            }

        ws.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": token,
                }
            )
        )

        authentication = json.loads(
            ws.recv()
        )

        if authentication.get(
            "type"
        ) != "auth_ok":
            return {
                "status": (
                    "authentication_failed"
                ),
                "entries": [],
                "error": (
                    "Home Assistant WebSocket "
                    "authentication failed."
                ),
            }

        ws.send(
            json.dumps(
                {
                    "id": 1,
                    "type": (
                        "system_log/list"
                    ),
                }
            )
        )

        while True:
            response = json.loads(
                ws.recv()
            )

            if (
                response.get(
                    "type"
                )
                != "result"
                or response.get(
                    "id"
                )
                != 1
            ):
                continue

            if not response.get(
                "success",
                False,
            ):
                error = response.get(
                    "error",
                    {},
                )

                return {
                    "status": (
                        "command_failed"
                    ),
                    "entries": [],
                    "error": (
                        error.get(
                            "message"
                        )
                        if isinstance(
                            error,
                            dict,
                        )
                        else str(
                            error
                        )
                    ),
                }

            result = response.get(
                "result",
                [],
            )

            if not isinstance(
                result,
                list,
            ):
                return {
                    "status": (
                        "invalid_response"
                    ),
                    "entries": [],
                    "error": (
                        "system_log/list did not "
                        "return a list."
                    ),
                }

            return {
                "status": "ok",
                "entries": result,
                "error": None,
            }

    except Exception as exc:
        return {
            "status": (
                "request_failed"
            ),
            "entries": [],
            "error": str(
                exc
            ),
        }

    finally:
        try:
            ws.close()
        except Exception:
            pass


def build_report(
    collection,
):
    report = {
        "audit_version": VERSION,
        "generated_at": utc_now(),
        "scope": {
            "phase": (
                "core_log_collection_probe"
            ),
            "source": (
                "Home Assistant System Log"
            ),
            "collection_method": (
                "system_log/list"
            ),
            "current_core_session_only": (
                True
            ),
            "warning_and_error_entries_only": (
                True
            ),
            "home_assistant_deduplicated": (
                True
            ),
            "judgement_produced": False,
            "severity_produced": False,
            "note": (
                "Home Assistant System Log "
                "already groups recurring warning "
                "and error records. HA Audit is "
                "collecting that evidence only. "
                "It does not yet decide whether "
                "an entry is harmful, resource-"
                "intensive, user-fixable, upstream, "
                "or relevant to an update."
            ),
        },
        "collection": {
            "status": collection.get(
                "status"
            ),
            "error": collection.get(
                "error"
            ),
        },
        "summary": {},
        "entries": [],
    }

    if collection.get(
        "status"
    ) != "ok":
        return report

    raw_entries = collection.get(
        "entries",
        [],
    )

    entries = []

    for item in raw_entries:
        entry = normalise_entry(
            item
        )

        if entry is not None:
            entries.append(
                entry
            )

    entries.sort(
        key=lambda item: (
            -int(
                item.get(
                    "count",
                    0,
                )
            ),
            0
            if item.get(
                "level"
            )
            in (
                "CRITICAL",
                "ERROR",
            )
            else 1,
            str(
                item.get(
                    "name",
                    "",
                )
            ),
        )
    )

    entries = entries[
        :MAX_ENTRIES
    ]

    error_entries = [
        item
        for item in entries
        if item.get(
            "level"
        )
        in (
            "CRITICAL",
            "ERROR",
        )
    ]

    warning_entries = [
        item
        for item in entries
        if item.get(
            "level"
        )
        == "WARNING"
    ]

    total_occurrences = sum(
        int(
            item.get(
                "count",
                0,
            )
        )
        for item in entries
    )

    report[
        "summary"
    ] = {
        "entries_returned": len(
            entries
        ),
        "error_entry_count": len(
            error_entries
        ),
        "warning_entry_count": len(
            warning_entries
        ),
        "total_occurrence_count": (
            total_occurrences
        ),
        "highest_repeat_count": (
            entries[
                0
            ].get(
                "count",
                0,
            )
            if entries
            else 0
        ),
    }

    report[
        "entries"
    ] = entries

    return report


def main():
    collection = collect_system_log()

    report = build_report(
        collection
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
