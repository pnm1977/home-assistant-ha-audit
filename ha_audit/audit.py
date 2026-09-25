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


# ------------------------------------------------------------------
# Basic system information
# ------------------------------------------------------------------

supervisor = get_json("/supervisor/info")
core = get_json("/core/info")
os_info = get_json("/os/info")
ha_config = get_json("/core/api/config")


# ------------------------------------------------------------------
# Apps / add-ons
# ------------------------------------------------------------------

addons_raw = get_json("/addons")

if isinstance(addons_raw, dict):
    addons_raw = addons_raw.get("addons", [])

installed_addons = []

for addon in addons_raw:
    if addon.get("installed"):
        installed_addons.append(
            {
                "name": addon.get("name"),
                "slug": addon.get("slug"),
                "version": addon.get("version"),
                "version_latest": addon.get("version_latest"),
                "update_available": addon.get("update_available"),
                "state": addon.get("state"),
                "repository": addon.get("repository"),
            }
        )


# ------------------------------------------------------------------
# Home Assistant entity states
# ------------------------------------------------------------------

states = get_json("/core/api/states")

domain_counts = Counter()
unavailable_entities = []
unknown_entities = []
updates_available = []

for entity in states:
    entity_id = entity.get("entity_id", "")
    state = entity.get("state")
    attributes = entity.get("attributes", {})

    domain = entity_id.split(".", 1)[0] if "." in entity_id else "other"
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
                "installed_version": attributes.get("installed_version"),
                "latest_version": attributes.get("latest_version"),
            }
        )


# ------------------------------------------------------------------
# Home Assistant configuration validation
# ------------------------------------------------------------------

try:
    config_check = post_json("/core/api/config/core/check_config")
except Exception as error:
    config_check = {
        "result": "error",
        "errors": str(error),
    }


# ------------------------------------------------------------------
# Recent Core logs
# ------------------------------------------------------------------

try:
    raw_logs = get_text("/core/logs/latest?lines=500")

    interesting_logs = []

    for line in raw_logs.splitlines():
        upper = line.upper()

        if (
            " ERROR " in upper
            or " WARNING " in upper
            or " CRITICAL " in upper
            or "[ERROR]" in upper
            or "[WARNING]" in upper
        ):
            interesting_logs.append(line)

    # Keep only the most recent 100 matching lines.
    interesting_logs = interesting_logs[-100:]

except Exception as error:
    interesting_logs = [
        f"Unable to retrieve Core logs: {error}"
    ]


# ------------------------------------------------------------------
# Build snapshot
# ------------------------------------------------------------------

snapshot = {
    "audit_version": "0.2.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),

    "system": {
        "core_version": core.get("version"),
        "supervisor_version": supervisor.get("version"),
        "os_version": os_info.get("version"),
        "installation_type": ha_config.get("installation_type"),
        "timezone": ha_config.get("time_zone"),
    },

    "addons": {
        "count": len(installed_addons),
        "installed": installed_addons,
    },

    "entities": {
        "total": len(states),
        "by_domain": dict(sorted(domain_counts.items())),
        "unavailable_count": len(unavailable_entities),
        "unavailable": sorted(unavailable_entities),
        "unknown_count": len(unknown_entities),
        "unknown": sorted(unknown_entities),
    },

    "automations": {
        "count": domain_counts.get("automation", 0),
    },

    "scripts": {
        "count": domain_counts.get("script", 0),
    },

    "updates": {
        "available_count": len(updates_available),
        "available": updates_available,
    },

    "configuration_check": config_check,

    "recent_core_log_findings": {
        "count": len(interesting_logs),
        "lines": interesting_logs,
    },
}


# ------------------------------------------------------------------
# Save locally
# ------------------------------------------------------------------

output_file = "/config/audit_snapshot.json"

with open(output_file, "w", encoding="utf-8") as file:
    json.dump(snapshot, file, indent=2)


# ------------------------------------------------------------------
# Useful summary in the app log
# ------------------------------------------------------------------

print("")
print("==========================================")
print(" HA AUDIT v0.2.0")
print("==========================================")
print(f"Core:              {snapshot['system']['core_version']}")
print(f"Supervisor:        {snapshot['system']['supervisor_version']}")
print(f"OS:                {snapshot['system']['os_version']}")
print(f"Installed apps:    {snapshot['addons']['count']}")
print(f"Entities:          {snapshot['entities']['total']}")
print(f"Unavailable:       {snapshot['entities']['unavailable_count']}")
print(f"Unknown:           {snapshot['entities']['unknown_count']}")
print(f"Automations:       {snapshot['automations']['count']}")
print(f"Scripts:           {snapshot['scripts']['count']}")
print(f"Updates available: {snapshot['updates']['available_count']}")
print(
    f"Config check:      "
    f"{snapshot['configuration_check'].get('result', 'unknown')}"
)
print(
    f"Log findings:      "
    f"{snapshot['recent_core_log_findings']['count']}"
)
print("==========================================")
print("")
print(f"Full snapshot: {output_file}")
