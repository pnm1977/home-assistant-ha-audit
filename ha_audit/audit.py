import json
import os
from collections import Counter
from datetime import datetime, timezone

import requests
import websocket

TOKEN = os.environ["SUPERVISOR_TOKEN"]

SUPERVISOR = "http://supervisor"
WS_URL = "ws://supervisor/core/websocket"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# REST helpers
# ------------------------------------------------------------

def get_json(path, timeout=30):
    response = requests.get(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]

    return payload


def post_json(path, timeout=60):
    response = requests.post(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()

    payload = response.json()

    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]

    return payload


def safe_collect(function):
    try:
        return {
            "status": "ok",
            "data": function(),
        }
    except Exception as error:
        return {
            "status": "error",
            "error": str(error),
        }


# ------------------------------------------------------------
# WebSocket helper
# ------------------------------------------------------------

def collect_registries():
    ws = websocket.create_connection(
        WS_URL,
        timeout=30,
        suppress_origin=True,
    )

    try:
        message = json.loads(ws.recv())

        if message.get("type") != "auth_required":
            raise RuntimeError(
                f"Unexpected WebSocket greeting: {message}"
            )

        ws.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": TOKEN,
                }
            )
        )

        auth_result = json.loads(ws.recv())

        if auth_result.get("type") != "auth_ok":
            raise RuntimeError(
                f"WebSocket authentication failed: {auth_result}"
            )

        commands = [
            "config/entity_registry/list_for_display",
            "config/device_registry/list",
            "config/area_registry/list",
        ]

        results = {}

        for command_id, command in enumerate(commands, start=1):
            ws.send(
                json.dumps(
                    {
                        "id": command_id,
                        "type": command,
                    }
                )
            )

            while True:
                response = json.loads(ws.recv())

                if (
                    response.get("type") == "result"
                    and response.get("id") == command_id
                ):
                    if not response.get("success"):
                        raise RuntimeError(
                            f"{command} failed: "
                            f"{response.get('error')}"
                        )

                    results[command] = response.get("result")
                    break

        return results

    finally:
        ws.close()


# ------------------------------------------------------------
# Basic HA information
# ------------------------------------------------------------

supervisor_result = safe_collect(
    lambda: get_json("/supervisor/info")
)

core_result = safe_collect(
    lambda: get_json("/core/info")
)

os_result = safe_collect(
    lambda: get_json("/os/info")
)

ha_config_result = safe_collect(
    lambda: get_json("/core/api/config")
)

states_result = safe_collect(
    lambda: get_json("/core/api/states")
)

config_check_result = safe_collect(
    lambda: post_json(
        "/core/api/config/core/check_config",
        timeout=120,
    )
)

registry_result = safe_collect(
    collect_registries
)


# ------------------------------------------------------------
# Extract safe results
# ------------------------------------------------------------

supervisor = (
    supervisor_result["data"]
    if supervisor_result["status"] == "ok"
    else {}
)

core = (
    core_result["data"]
    if core_result["status"] == "ok"
    else {}
)

os_info = (
    os_result["data"]
    if os_result["status"] == "ok"
    else {}
)

ha_config = (
    ha_config_result["data"]
    if ha_config_result["status"] == "ok"
    else {}
)

states = (
    states_result["data"]
    if states_result["status"] == "ok"
    else []
)

registry_data = (
    registry_result["data"]
    if registry_result["status"] == "ok"
    else {}
)


# ------------------------------------------------------------
# Entity registry
# ------------------------------------------------------------

entity_display = registry_data.get(
    "config/entity_registry/list_for_display",
    {},
)

entity_registry = entity_display.get(
    "entities",
    [],
)

entity_registry_by_id = {
    entry["ei"]: entry
    for entry in entity_registry
    if entry.get("ei")
}


# ------------------------------------------------------------
# Device registry
# ------------------------------------------------------------

devices = registry_data.get(
    "config/device_registry/list",
    [],
)

device_by_id = {
    device["id"]: device
    for device in devices
    if device.get("id")
}


# ------------------------------------------------------------
# Area registry
# ------------------------------------------------------------

areas = registry_data.get(
    "config/area_registry/list",
    [],
)

area_by_id = {
    area["area_id"]: area.get("name")
    for area in areas
    if area.get("area_id")
}


# ------------------------------------------------------------
# Current states
# ------------------------------------------------------------

domain_counts = Counter()

unavailable_entities = []
unknown_entities = []

updates_available = []

unavailable_by_platform = Counter()
unknown_by_platform = Counter()


def enrich_entity(state_entry):
    entity_id = state_entry.get("entity_id")
    attributes = state_entry.get("attributes", {})

    registry = entity_registry_by_id.get(
        entity_id,
        {},
    )

    platform = registry.get(
        "pl",
        "unregistered_or_unknown",
    )

    device_id = registry.get("di")
    device = device_by_id.get(device_id, {})

    area_id = (
        registry.get("ai")
        or device.get("area_id")
    )

    device_name = (
        device.get("name_by_user")
        or device.get("name")
    )

    return {
        "entity_id": entity_id,
        "name": (
            attributes.get("friendly_name")
            or registry.get("en")
        ),
        "platform": platform,
        "area": area_by_id.get(area_id),
        "device": device_name,
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
    }


for state_entry in states:
    entity_id = state_entry.get("entity_id", "")
    state = state_entry.get("state")
    attributes = state_entry.get("attributes", {})

    domain = (
        entity_id.split(".", 1)[0]
        if "." in entity_id
        else "other"
    )

    domain_counts[domain] += 1

    if state == "unavailable":
        enriched = enrich_entity(state_entry)
        unavailable_entities.append(enriched)

        unavailable_by_platform[
            enriched["platform"]
        ] += 1

    elif state == "unknown":
        enriched = enrich_entity(state_entry)
        unknown_entities.append(enriched)

        unknown_by_platform[
            enriched["platform"]
        ] += 1

    if domain == "update" and state == "on":
        updates_available.append(
            {
                "entity_id": entity_id,
                "name": attributes.get(
                    "friendly_name"
                ),
                "installed_version": attributes.get(
                    "installed_version"
                ),
                "latest_version": attributes.get(
                    "latest_version"
                ),
            }
        )


# ------------------------------------------------------------
# Registry statistics
# ------------------------------------------------------------

enabled_entities_by_platform = Counter()

for entry in entity_registry:
    enabled_entities_by_platform[
        entry.get("pl", "unknown")
    ] += 1


# Core 2026.9 introduces child devices.
# We deliberately recognise them separately rather than
# assuming every device has normal hardware metadata.

child_devices = [
    device
    for device in devices
    if device.get("parent_device_id")
]

regular_devices = [
    device
    for device in devices
    if not device.get("parent_device_id")
]


# ------------------------------------------------------------
# Snapshot
# ------------------------------------------------------------

snapshot = {
    "audit_version": "0.3.0",

    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "system": {
        "core_version": core.get("version"),
        "supervisor_version": supervisor.get("version"),
        "os_version": os_info.get("version"),
        "installation_type": ha_config.get(
            "installation_type"
        ),
        "timezone": ha_config.get("time_zone"),
    },

    "inventory": {
        "state_entities": len(states),
        "registered_enabled_entities": len(
            entity_registry
        ),
        "regular_devices": len(regular_devices),
        "child_devices": len(child_devices),
        "areas": len(areas),
    },

    "entities": {
        "by_domain": dict(
            sorted(domain_counts.items())
        ),

        "by_platform": dict(
            enabled_entities_by_platform.most_common()
        ),

        "unavailable": {
            "count": len(unavailable_entities),

            "by_platform": dict(
                unavailable_by_platform.most_common()
            ),

            "entities": sorted(
                unavailable_entities,
                key=lambda item: (
                    item["platform"],
                    item["entity_id"],
                ),
            ),
        },

        "unknown": {
            "count": len(unknown_entities),

            "by_platform": dict(
                unknown_by_platform.most_common()
            ),

            "entities": sorted(
                unknown_entities,
                key=lambda item: (
                    item["platform"],
                    item["entity_id"],
                ),
            ),
        },
    },

    "automations": {
        "count": domain_counts.get(
            "automation",
            0,
        ),
    },

    "scripts": {
        "count": domain_counts.get(
            "script",
            0,
        ),
    },

    "updates": {
        "available_count": len(
            updates_available
        ),

        "available": updates_available,
    },

    "configuration_check": config_check_result,

    "collector_status": {
        "supervisor": supervisor_result["status"],
        "core": core_result["status"],
        "os": os_result["status"],
        "ha_config": ha_config_result["status"],
        "states": states_result["status"],
        "registries": registry_result["status"],
        "config_check": config_check_result["status"],
    },
}


# ------------------------------------------------------------
# Save
# ------------------------------------------------------------

output_file = "/config/audit_snapshot.json"

with open(
    output_file,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        snapshot,
        file,
        indent=2,
    )


# ------------------------------------------------------------
# Console report
# ------------------------------------------------------------

print("")
print("==========================================")
print(" HA AUDIT v0.3.0")
print("==========================================")

print(
    f"Core:                "
    f"{snapshot['system']['core_version']}"
)

print(
    f"Supervisor:          "
    f"{snapshot['system']['supervisor_version']}"
)

print(
    f"OS:                  "
    f"{snapshot['system']['os_version']}"
)

print(
    f"Entities:            "
    f"{len(states)}"
)

print(
    f"Registered entities: "
    f"{len(entity_registry)}"
)

print(
    f"Devices:             "
    f"{len(regular_devices)}"
)

print(
    f"Child devices:       "
    f"{len(child_devices)}"
)

print(
    f"Unavailable:         "
    f"{len(unavailable_entities)}"
)

print(
    f"Unknown:             "
    f"{len(unknown_entities)}"
)

print(
    f"Automations:         "
    f"{domain_counts.get('automation', 0)}"
)

print(
    f"Scripts:             "
    f"{domain_counts.get('script', 0)}"
)

print(
    f"Updates available:   "
    f"{len(updates_available)}"
)

if config_check_result["status"] == "ok":
    print(
        f"Config check:        "
        f"{config_check_result['data'].get('result')}"
    )
else:
    print("Config check:        ERROR")


print("")
print("Unavailable by platform:")
print("------------------------------------------")

for platform, count in unavailable_by_platform.most_common(20):
    print(
        f"{platform:<28} {count:>5}"
    )


print("")
print("Unknown by platform:")
print("------------------------------------------")

for platform, count in unknown_by_platform.most_common(20):
    print(
        f"{platform:<28} {count:>5}"
    )


print("")
print("Collector status:")
print("------------------------------------------")

for collector, status in snapshot[
    "collector_status"
].items():
    print(
        f"{collector:<28} {status}"
    )


print("==========================================")
print("")
print(f"Full snapshot: {output_file}")
