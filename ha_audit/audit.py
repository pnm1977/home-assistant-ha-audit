import json
import os
from collections import Counter
from datetime import datetime, timezone

import requests

TOKEN = os.environ["SUPERVISOR_TOKEN"]
SUPERVISOR = "http://supervisor"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


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


def get_text(path, timeout=30):
    response = requests.get(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.text


def safe_collect(name, function):
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
# Core system information
# ------------------------------------------------------------

supervisor_result = safe_collect(
    "supervisor",
    lambda: get_json("/supervisor/info"),
)

core_result = safe_collect(
    "core",
    lambda: get_json("/core/info"),
)

os_result = safe_collect(
    "os",
    lambda: get_json("/os/info"),
)

ha_config_result = safe_collect(
    "home_assistant_config",
    lambda: get_json("/core/api/config"),
)


# ------------------------------------------------------------
# Entity states
# ------------------------------------------------------------

states_result = safe_collect(
    "states",
    lambda: get_json("/core/api/states"),
)

states = (
    states_result["data"]
    if states_result["status"] == "ok"
    else []
)

domain_counts = Counter()
unavailable_entities = []
unknown_entities = []
updates_available = []

for entity in states:
    entity_id = entity.get("entity_id", "")
    state = entity.get("state")
    attributes = entity.get("attributes", {})

    domain = (
        entity_id.split(".", 1)[0]
        if "." in entity_id
        else "other"
    )

    domain_counts[domain] += 1

    if state == "unavailable":
        unavailable_entities.append(entity_id)

    if state == "unknown":
        unknown_entities.append(entity_id)

    if domain == "update" and state == "on":
        updates_available.append(
            {
                "entity_id": entity_id,
                "name": attributes.get("friendly_name"),
                "installed_version": attributes.get(
                    "installed_version"
                ),
                "latest_version": attributes.get(
                    "latest_version"
                ),
            }
        )


# ------------------------------------------------------------
# Configuration validation
# ------------------------------------------------------------

config_check_result = safe_collect(
    "configuration_check",
    lambda: post_json(
        "/core/api/config/core/check_config",
        timeout=120,
    ),
)


# ------------------------------------------------------------
# Home Assistant error log
# ------------------------------------------------------------

error_log_result = safe_collect(
    "error_log",
    lambda: get_text("/core/api/error_log"),
)

interesting_logs = []

if error_log_result["status"] == "ok":
    raw_logs = error_log_result["data"]

    for line in raw_logs.splitlines():
        if line.strip():
            interesting_logs.append(line)

    interesting_logs = interesting_logs[-100:]


# ------------------------------------------------------------
# Extract basic system versions
# ------------------------------------------------------------

core = (
    core_result["data"]
    if core_result["status"] == "ok"
    else {}
)

supervisor = (
    supervisor_result["data"]
    if supervisor_result["status"] == "ok"
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


# ------------------------------------------------------------
# Build audit snapshot
# ------------------------------------------------------------

snapshot = {
    "audit_version": "0.2.1",
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

    "entities": {
        "total": len(states),
        "by_domain": dict(
            sorted(domain_counts.items())
        ),
        "unavailable_count": len(
            unavailable_entities
        ),
        "unavailable": sorted(
            unavailable_entities
        ),
        "unknown_count": len(
            unknown_entities
        ),
        "unknown": sorted(
            unknown_entities
        ),
    },

    "automations": {
        "count": domain_counts.get(
            "automation", 0
        ),
    },

    "scripts": {
        "count": domain_counts.get(
            "script", 0
        ),
    },

    "updates": {
        "available_count": len(
            updates_available
        ),
        "available": updates_available,
    },

    "configuration_check": config_check_result,

    "recent_core_log_findings": {
        "status": error_log_result["status"],
        "count": len(interesting_logs),
        "lines": interesting_logs,
    },

    "collector_status": {
        "supervisor": supervisor_result["status"],
        "core": core_result["status"],
        "os": os_result["status"],
        "ha_config": ha_config_result["status"],
        "states": states_result["status"],
        "config_check": config_check_result["status"],
        "error_log": error_log_result["status"],
    },
}


# ------------------------------------------------------------
# Save locally
# ------------------------------------------------------------

output_file = "/config/audit_snapshot.json"

with open(
    output_file,
    "w",
    encoding="utf-8",
) as file:
    json.dump(snapshot, file, indent=2)


# ------------------------------------------------------------
# Console summary
# ------------------------------------------------------------

print("")
print("==========================================")
print(" HA AUDIT v0.2.1")
print("==========================================")
print(
    f"Core:              "
    f"{snapshot['system']['core_version']}"
)
print(
    f"Supervisor:        "
    f"{snapshot['system']['supervisor_version']}"
)
print(
    f"OS:                "
    f"{snapshot['system']['os_version']}"
)
print(
    f"Entities:          "
    f"{snapshot['entities']['total']}"
)
print(
    f"Unavailable:       "
    f"{snapshot['entities']['unavailable_count']}"
)
print(
    f"Unknown:           "
    f"{snapshot['entities']['unknown_count']}"
)
print(
    f"Automations:       "
    f"{snapshot['automations']['count']}"
)
print(
    f"Scripts:           "
    f"{snapshot['scripts']['count']}"
)
print(
    f"Updates available: "
    f"{snapshot['updates']['available_count']}"
)

if config_check_result["status"] == "ok":
    print(
        f"Config check:      "
        f"{config_check_result['data'].get('result')}"
    )
else:
    print("Config check:      ERROR")

print(
    f"Log lines:         "
    f"{len(interesting_logs)}"
)
print("==========================================")
print("")
print(f"Full snapshot: {output_file}")
