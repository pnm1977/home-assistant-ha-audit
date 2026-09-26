import json
import os
from datetime import datetime, timezone

import websocket


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ["SUPERVISOR_TOKEN"]

WS_URL = "ws://supervisor/core/websocket"

OUTPUT_FILE = "/config/recorder_health_audit.json"

REQUESTED_LOOKBACK_DAYS = 90


def parse_timestamp(value):
    if isinstance(value, dict):
        value = value.get("value")

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


def unwrap_value(value):
    if (
        isinstance(value, dict)
        and "value" in value
    ):
        return value.get("value")

    return value


def collect_system_health():
    ws = websocket.create_connection(
        WS_URL,
        timeout=30,
        suppress_origin=True,
    )

    try:
        greeting = json.loads(
            ws.recv()
        )

        if greeting.get("type") != "auth_required":
            raise RuntimeError(
                "Unexpected WebSocket greeting"
            )

        ws.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": TOKEN,
                }
            )
        )

        authentication = json.loads(
            ws.recv()
        )

        if authentication.get("type") != "auth_ok":
            raise RuntimeError(
                "WebSocket authentication failed"
            )

        message_id = 1

        ws.send(
            json.dumps(
                {
                    "id": message_id,
                    "type": "system_health/info",
                }
            )
        )

        recorder_info = {}
        subscription_confirmed = False

        while True:
            response = json.loads(
                ws.recv()
            )

            if response.get("id") != message_id:
                continue

            if response.get("type") == "result":
                if not response.get("success"):
                    raise RuntimeError(
                        "system_health/info failed: "
                        f"{response.get('error')}"
                    )

                subscription_confirmed = True
                continue

            if response.get("type") != "event":
                continue

            event = response.get(
                "event",
                {},
            )

            event_type = event.get(
                "type"
            )

            if event_type == "initial":
                data = event.get(
                    "data",
                    {},
                )

                recorder_domain = data.get(
                    "recorder",
                    {},
                )

                initial_info = recorder_domain.get(
                    "info",
                    {},
                )

                if isinstance(
                    initial_info,
                    dict,
                ):
                    recorder_info.update(
                        initial_info
                    )

                continue

            if event_type == "update":
                if event.get(
                    "domain"
                ) != "recorder":
                    continue

                key = event.get(
                    "key"
                )

                if not key:
                    continue

                if event.get(
                    "success",
                    False,
                ):
                    recorder_info[
                        key
                    ] = event.get(
                        "data"
                    )
                else:
                    recorder_info[
                        key
                    ] = {
                        "type": "failed",
                        "error": event.get(
                            "error",
                            {},
                        ),
                    }

                continue

            if event_type == "finish":
                break

        if not subscription_confirmed:
            raise RuntimeError(
                "system_health/info subscription "
                "was not confirmed"
            )

        if not recorder_info:
            raise RuntimeError(
                "Recorder system health data "
                "was not returned"
            )

        return recorder_info

    finally:
        ws.close()


generated_at = datetime.now(
    timezone.utc
)

status = "ok"
error = None
recorder_info = {}

try:
    recorder_info = collect_system_health()
except Exception as exc:
    status = "error"
    error = str(
        exc
    )


oldest_raw = recorder_info.get(
    "oldest_recorder_run"
)

current_raw = recorder_info.get(
    "current_recorder_run"
)

oldest = parse_timestamp(
    oldest_raw
)

current = parse_timestamp(
    current_raw
)


available_history_days = None
effective_lookback_days = None

if oldest:
    available_history_days = max(
        0.0,
        (
            generated_at
            - oldest.astimezone(
                timezone.utc
            )
        ).total_seconds()
        / 86400.0,
    )

    effective_lookback_days = min(
        float(
            REQUESTED_LOOKBACK_DAYS
        ),
        available_history_days,
    )


report = {
    "audit_version": VERSION,

    "generated_at":
        generated_at.isoformat(),

    "status": status,

    "error": error,

    "requested_history_lookback_days":
        REQUESTED_LOOKBACK_DAYS,

    "recorder": {
        "oldest_recorder_run":
            oldest.isoformat()
            if oldest
            else unwrap_value(
                oldest_raw
            ),

        "current_recorder_run":
            current.isoformat()
            if current
            else unwrap_value(
                current_raw
            ),

        "estimated_db_size":
            unwrap_value(
                recorder_info.get(
                    "estimated_db_size"
                )
            ),

        "database_engine":
            unwrap_value(
                recorder_info.get(
                    "database_engine"
                )
            ),

        "database_version":
            unwrap_value(
                recorder_info.get(
                    "database_version"
                )
            ),
    },

    "history_availability": {
        "available_history_days":
            round(
                available_history_days,
                2,
            )
            if available_history_days
            is not None
            else None,

        "effective_lookback_days":
            round(
                effective_lookback_days,
                2,
            )
            if effective_lookback_days
            is not None
            else None,

        "important":
            (
                "The oldest Recorder run is an "
                "upper bound on the time range "
                "available from Recorder. It does "
                "not guarantee that every entity "
                "has history for the whole period, "
                "because individual entities may "
                "be excluded or have shorter "
                "recorded histories."
            ),
    },

    "raw_recorder_info":
        recorder_info,
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


print("")
print(
    "Recorder history availability audit"
)
print(
    "------------------------------------------"
)

print(
    f"Status:                     "
    f"{status}"
)

if oldest:
    print(
        f"Oldest Recorder run:        "
        f"{oldest.isoformat()}"
    )

if available_history_days is not None:
    print(
        f"Recorder history available: "
        f"{available_history_days:.1f} days"
    )

if effective_lookback_days is not None:
    print(
        f"Effective history lookback: "
        f"{effective_lookback_days:.1f} days"
    )

if error:
    print(
        f"Error:                      "
        f"{error}"
    )

print("")
print(
    "Recorder availability is context only; "
    "it does not prove every entity has "
    "history for the whole period."
)

print("")
print(
    f"Recorder report saved: "
    f"{OUTPUT_FILE}"
)
