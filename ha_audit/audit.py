import json
import os
from collections import Counter
from datetime import datetime, timezone

import requests
import websocket

VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ["SUPERVISOR_TOKEN"]

SUPERVISOR = "http://supervisor"
WS_URL = "ws://supervisor/core/websocket"

OUTPUT_FILE = "/config/audit_snapshot.json"
PREVIOUS_FILE = "/config/audit_snapshot_previous.json"

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
# WebSocket registry collector
# ------------------------------------------------------------

def collect_registries():
    ws = websocket.create_connection(
        WS_URL,
        timeout=30,
        suppress_origin=True,
    )

    try:
        greeting = json.loads(ws.recv())

        if greeting.get("type") != "auth_required":
            raise RuntimeError(
                f"Unexpected WebSocket greeting: {greeting}"
            )

        ws.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": TOKEN,
                }
            )
        )

        authentication = json.loads(ws.recv())

        if authentication.get("type") != "auth_ok":
            raise RuntimeError(
                f"WebSocket authentication failed: {authentication}"
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
# Load previous audit
# ------------------------------------------------------------

previous_snapshot = None

if os.path.exists(OUTPUT_FILE):
    try:
        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            previous_snapshot = json.load(file)
    except Exception:
        previous_snapshot = None


# ------------------------------------------------------------
# Collect HA information
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
# Safe extraction
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
# Registries
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


devices = registry_data.get(
    "config/device_registry/list",
    [],
)

device_by_id = {
    device["id"]: device
    for device in devices
    if device.get("id")
}


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
# Entity analysis
# ------------------------------------------------------------

domain_counts = Counter()

unavailable_entities = []
unknown_entities = []

unavailable_by_platform = Counter()
unknown_by_platform = Counter()

unavailable_by_device = Counter()
unknown_by_device = Counter()

updates_available = []


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
        "device": device_name,
        "device_id": device_id,
        "area": area_by_id.get(area_id),
        "manufacturer": device.get("manufacturer"),
        "model": device.get("model"),
        "last_changed": state_entry.get("last_changed"),
    }


def device_label(entity):
    device_name = entity.get("device")
    platform = entity.get("platform")

    if device_name:
        return f"{device_name} [{platform}]"

    return f"No device [{platform}]"


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

        unavailable_by_device[
            device_label(enriched)
        ] += 1

    elif state == "unknown":
        enriched = enrich_entity(state_entry)

        unknown_entities.append(enriched)

        unknown_by_platform[
            enriched["platform"]
        ] += 1

        unknown_by_device[
            device_label(enriched)
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
# Device structure
# ------------------------------------------------------------

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
# Compare against previous audit
# ------------------------------------------------------------

current_unavailable_ids = {
    item["entity_id"]
    for item in unavailable_entities
}

current_unknown_ids = {
    item["entity_id"]
    for item in unknown_entities
}


previous_unavailable_ids = set()
previous_unknown_ids = set()

previous_generated_at = None


if previous_snapshot:
    previous_generated_at = previous_snapshot.get(
        "generated_at"
    )

    try:
        previous_unavailable_ids = {
            item["entity_id"]
            for item in previous_snapshot[
                "entities"
            ][
                "unavailable"
            ][
                "entities"
            ]
        }
    except Exception:
        previous_unavailable_ids = set()

    try:
        previous_unknown_ids = {
            item["entity_id"]
            for item in previous_snapshot[
                "entities"
            ][
                "unknown"
            ][
                "entities"
            ]
        }
    except Exception:
        previous_unknown_ids = set()


new_unavailable = sorted(
    current_unavailable_ids
    - previous_unavailable_ids
)

resolved_unavailable = sorted(
    previous_unavailable_ids
    - current_unavailable_ids
)

new_unknown = sorted(
    current_unknown_ids
    - previous_unknown_ids
)

resolved_unknown = sorted(
    previous_unknown_ids
    - current_unknown_ids
)


# ------------------------------------------------------------
# Snapshot
# ------------------------------------------------------------

snapshot = {
    "audit_version": VERSION,

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
        "registered_entities": len(
            entity_registry
        ),
        "regular_devices": len(
            regular_devices
        ),
        "child_devices": len(
            child_devices
        ),
        "areas": len(areas),
    },

    "entities": {
        "by_domain": dict(
            sorted(domain_counts.items())
        ),

        "unavailable": {
            "count": len(
                unavailable_entities
            ),

            "by_platform": dict(
                unavailable_by_platform.most_common()
            ),

            "by_device": dict(
                unavailable_by_device.most_common()
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
            "count": len(
                unknown_entities
            ),

            "by_platform": dict(
                unknown_by_platform.most_common()
            ),

            "by_device": dict(
                unknown_by_device.most_common()
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

    "changes_since_previous": {
        "previous_generated_at": previous_generated_at,

        "new_unavailable_count": len(
            new_unavailable
        ),
        "new_unavailable": new_unavailable,

        "resolved_unavailable_count": len(
            resolved_unavailable
        ),
        "resolved_unavailable": resolved_unavailable,

        "new_unknown_count": len(
            new_unknown
        ),
        "new_unknown": new_unknown,

        "resolved_unknown_count": len(
            resolved_unknown
        ),
        "resolved_unknown": resolved_unknown,
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
# Preserve previous report
# ------------------------------------------------------------

if previous_snapshot:
    try:
        with open(
            PREVIOUS_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                previous_snapshot,
                file,
                indent=2,
            )
    except Exception:
        pass


# ------------------------------------------------------------
# Save latest report
# ------------------------------------------------------------

with open(
    OUTPUT_FILE,
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
print(f" HA AUDIT v{VERSION}")
print("==========================================")

print(f"Core:                {core.get('version')}")
print(f"Supervisor:          {supervisor.get('version')}")
print(f"OS:                  {os_info.get('version')}")

print(f"Entities:            {len(states)}")
print(f"Devices:             {len(regular_devices)}")

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

for platform, count in unavailable_by_platform.most_common(15):
    print(f"{platform:<28} {count:>5}")


print("")
print("Top unavailable devices:")
print("------------------------------------------")

for device, count in unavailable_by_device.most_common(20):
    print(f"{device:<48} {count:>5}")


print("")
print("Top unknown devices:")
print("------------------------------------------")

for device, count in unknown_by_device.most_common(15):
    print(f"{device:<48} {count:>5}")


print("")
print("Changes since previous audit:")
print("------------------------------------------")

if previous_snapshot:
    print(
        f"New unavailable:      "
        f"{len(new_unavailable)}"
    )

    print(
        f"Recovered unavailable:"
        f" {len(resolved_unavailable)}"
    )

    print(
        f"New unknown:          "
        f"{len(new_unknown)}"
    )

    print(
        f"Resolved unknown:     "
        f"{len(resolved_unknown)}"
    )
else:
    print("No previous audit available.")


print("")
print("Collector status:")
print("------------------------------------------")

for collector, status in snapshot[
    "collector_status"
].items():
    print(f"{collector:<28} {status}")


print("==========================================")
print("")
print(f"Latest snapshot:   {OUTPUT_FILE}")
print(f"Previous snapshot: {PREVIOUS_FILE}")
