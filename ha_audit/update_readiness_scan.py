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

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"

OUTPUT_FILE = "/config/update_readiness_audit.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_json_optional(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(handle)
    except Exception:
        return {}


def get_json(
    path,
    timeout=30,
):
    response = requests.get(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=timeout,
    )

    response.raise_for_status()

    payload = response.json()

    if (
        isinstance(payload, dict)
        and "data" in payload
    ):
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
# WebSocket collector
# ------------------------------------------------------------

def collect_websocket_data():
    ws = websocket.create_connection(
        WS_URL,
        timeout=30,
        suppress_origin=True,
    )

    try:
        greeting = json.loads(
            ws.recv()
        )

        if (
            greeting.get("type")
            != "auth_required"
        ):
            raise RuntimeError(
                "Unexpected WebSocket greeting: "
                f"{greeting}"
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

        if (
            authentication.get("type")
            != "auth_ok"
        ):
            raise RuntimeError(
                "WebSocket authentication failed: "
                f"{authentication}"
            )

        commands = [
            "config/entity_registry/list_for_display",
            "config/device_registry/list",
            "config/area_registry/list",
            "entity/source",
            "repairs/list_issues",
        ]

        results = {}
        errors = {}

        for command_id, command in enumerate(
            commands,
            start=1,
        ):
            ws.send(
                json.dumps(
                    {
                        "id": command_id,
                        "type": command,
                    }
                )
            )

            while True:
                response = json.loads(
                    ws.recv()
                )

                if (
                    response.get("type")
                    != "result"
                    or response.get("id")
                    != command_id
                ):
                    continue

                if response.get("success"):
                    results[
                        command
                    ] = response.get(
                        "result"
                    )
                else:
                    errors[
                        command
                    ] = response.get(
                        "error"
                    )

                break

        return {
            "results": results,
            "errors": errors,
        }

    finally:
        ws.close()


# ------------------------------------------------------------
# Existing HA Audit evidence
# ------------------------------------------------------------

audit = load_json_optional(
    AUDIT_FILE
)

quality = load_json_optional(
    QUALITY_FILE
)


# ------------------------------------------------------------
# Current Home Assistant data
# ------------------------------------------------------------

states_result = safe_collect(
    lambda: get_json(
        "/core/api/states"
    )
)

websocket_result = safe_collect(
    collect_websocket_data
)

states = (
    states_result.get(
        "data",
        [],
    )
    if states_result.get("status") == "ok"
    else []
)

if not isinstance(
    states,
    list,
):
    states = []


ws_payload = (
    websocket_result.get(
        "data",
        {},
    )
    if websocket_result.get("status") == "ok"
    else {}
)

ws_results = ws_payload.get(
    "results",
    {},
)

ws_errors = ws_payload.get(
    "errors",
    {},
)


# ------------------------------------------------------------
# Registries
# ------------------------------------------------------------

entity_display = ws_results.get(
    "config/entity_registry/list_for_display",
    {},
)

if not isinstance(
    entity_display,
    dict,
):
    entity_display = {}

entity_registry = entity_display.get(
    "entities",
    [],
)

if not isinstance(
    entity_registry,
    list,
):
    entity_registry = []


entity_registry_by_id = {
    entry.get("ei"): entry
    for entry in entity_registry
    if isinstance(
        entry,
        dict,
    )
    and entry.get("ei")
}


devices = ws_results.get(
    "config/device_registry/list",
    [],
)

if not isinstance(
    devices,
    list,
):
    devices = []

device_by_id = {
    device.get("id"): device
    for device in devices
    if isinstance(
        device,
        dict,
    )
    and device.get("id")
}


areas = ws_results.get(
    "config/area_registry/list",
    [],
)

if not isinstance(
    areas,
    list,
):
    areas = []

area_by_id = {
    area.get("area_id"): area.get(
        "name"
    )
    for area in areas
    if isinstance(
        area,
        dict,
    )
    and area.get("area_id")
}


entity_sources = ws_results.get(
    "entity/source",
    {},
)

if not isinstance(
    entity_sources,
    dict,
):
    entity_sources = {}


# ------------------------------------------------------------
# Update entities
# ------------------------------------------------------------

all_update_entities = []

available_updates = []

unavailable_updates = []

updates_in_progress = []


for state_entry in states:
    if not isinstance(
        state_entry,
        dict,
    ):
        continue

    entity_id = state_entry.get(
        "entity_id",
        "",
    )

    if not entity_id.startswith(
        "update."
    ):
        continue

    state = state_entry.get(
        "state"
    )

    attributes = state_entry.get(
        "attributes",
        {},
    )

    if not isinstance(
        attributes,
        dict,
    ):
        attributes = {}

    registry = entity_registry_by_id.get(
        entity_id,
        {},
    )

    if not isinstance(
        registry,
        dict,
    ):
        registry = {}

    platform = registry.get(
        "pl"
    )

    device_id = registry.get(
        "di"
    )

    device = device_by_id.get(
        device_id,
        {},
    )

    if not isinstance(
        device,
        dict,
    ):
        device = {}

    area_id = (
        registry.get("ai")
        or device.get("area_id")
    )

    source = entity_sources.get(
        entity_id
    )

    if not isinstance(
        source,
        dict,
    ):
        source = {}

    device_name = (
        device.get(
            "name_by_user"
        )
        or device.get(
            "name"
        )
    )

    item = {
        "entity_id": entity_id,
        "state": state,
        "update_available": (
            state == "on"
        ),
        "name": attributes.get(
            "friendly_name"
        ),
        "title": attributes.get(
            "title"
        ),
        "installed_version":
            attributes.get(
                "installed_version"
            ),
        "latest_version":
            attributes.get(
                "latest_version"
            ),
        "release_summary":
            attributes.get(
                "release_summary"
            ),
        "release_url":
            attributes.get(
                "release_url"
            ),
        "device_class":
            attributes.get(
                "device_class"
            ),
        "in_progress":
            attributes.get(
                "in_progress"
            ),
        "update_percentage":
            attributes.get(
                "update_percentage"
            ),
        "auto_update":
            attributes.get(
                "auto_update"
            ),
        "skipped_version":
            attributes.get(
                "skipped_version"
            ),
        "supported_features":
            attributes.get(
                "supported_features"
            ),
        "platform": platform,
        "source": source,
        "device_id": device_id,
        "device": device_name,
        "manufacturer":
            device.get(
                "manufacturer"
            ),
        "model": device.get(
            "model"
        ),
        "area": area_by_id.get(
            area_id
        ),
        "last_changed":
            state_entry.get(
                "last_changed"
            ),
        "last_updated":
            state_entry.get(
                "last_updated"
            ),
    }

    all_update_entities.append(
        item
    )

    if state == "on":
        available_updates.append(
            item
        )

    if state == "unavailable":
        unavailable_updates.append(
            item
        )

    if attributes.get(
        "in_progress"
    ):
        updates_in_progress.append(
            item
        )


def update_sort_key(item):
    return (
        str(
            item.get(
                "platform"
            )
            or ""
        ).lower(),
        str(
            item.get(
                "title"
            )
            or item.get(
                "name"
            )
            or ""
        ).lower(),
        item.get(
            "entity_id",
            "",
        ),
    )


all_update_entities.sort(
    key=update_sort_key
)

available_updates.sort(
    key=update_sort_key
)

unavailable_updates.sort(
    key=update_sort_key
)

updates_in_progress.sort(
    key=update_sort_key
)


updates_by_platform = Counter(
    str(
        item.get("platform")
        or "unknown"
    )
    for item in available_updates
)

updates_by_device_class = Counter(
    str(
        item.get("device_class")
        or "none"
    )
    for item in available_updates
)


# ------------------------------------------------------------
# Repairs
# ------------------------------------------------------------

repairs_payload = ws_results.get(
    "repairs/list_issues",
    {},
)

if not isinstance(
    repairs_payload,
    dict,
):
    repairs_payload = {}

repairs = repairs_payload.get(
    "issues",
    [],
)

if not isinstance(
    repairs,
    list,
):
    repairs = []


normalised_repairs = []

for issue in repairs:
    if not isinstance(
        issue,
        dict,
    ):
        continue

    normalised_repairs.append(
        {
            "domain":
                issue.get(
                    "domain"
                ),
            "issue_domain":
                issue.get(
                    "issue_domain"
                ),
            "issue_id":
                issue.get(
                    "issue_id"
                ),
            "severity":
                issue.get(
                    "severity"
                ),
            "breaks_in_ha_version":
                issue.get(
                    "breaks_in_ha_version"
                ),
            "is_fixable":
                bool(
                    issue.get(
                        "is_fixable"
                    )
                ),
            "ignored":
                bool(
                    issue.get(
                        "ignored"
                    )
                ),
            "dismissed_version":
                issue.get(
                    "dismissed_version"
                ),
            "created":
                issue.get(
                    "created"
                ),
            "learn_more_url":
                issue.get(
                    "learn_more_url"
                ),
            "translation_key":
                issue.get(
                    "translation_key"
                ),
            "translation_placeholders":
                issue.get(
                    "translation_placeholders"
                ),
        }
    )


severity_order = {
    "critical": 0,
    "error": 1,
    "warning": 2,
}


def repair_sort_key(item):
    severity = str(
        item.get(
            "severity"
        )
        or ""
    ).lower()

    return (
        bool(
            item.get(
                "ignored"
            )
        ),
        severity_order.get(
            severity,
            99,
        ),
        str(
            item.get(
                "domain"
            )
            or ""
        ),
        str(
            item.get(
                "issue_id"
            )
            or ""
        ),
    )


normalised_repairs.sort(
    key=repair_sort_key
)


repairs_by_severity = Counter(
    str(
        item.get(
            "severity"
        )
        or "unknown"
    ).lower()
    for item in normalised_repairs
)

unignored_repairs = [
    item
    for item in normalised_repairs
    if not item.get(
        "ignored"
    )
]

ignored_repairs = [
    item
    for item in normalised_repairs
    if item.get(
        "ignored"
    )
]

breaking_repairs = [
    item
    for item in normalised_repairs
    if item.get(
        "breaks_in_ha_version"
    )
]

fixable_repairs = [
    item
    for item in normalised_repairs
    if item.get(
        "is_fixable"
    )
]


# ------------------------------------------------------------
# Existing audit/configuration foundation
# ------------------------------------------------------------

system = audit.get(
    "system",
    {},
)

if not isinstance(
    system,
    dict,
):
    system = {}


configuration_check = audit.get(
    "configuration_check",
    {},
)

if not isinstance(
    configuration_check,
    dict,
):
    configuration_check = {}

config_check_result = None

if (
    configuration_check.get(
        "status"
    )
    == "ok"
):
    config_check_data = (
        configuration_check.get(
            "data",
            {}
        )
    )

    if isinstance(
        config_check_data,
        dict,
    ):
        config_check_result = (
            config_check_data.get(
                "result"
            )
        )


existing_collector_status = audit.get(
    "collector_status",
    {},
)

if not isinstance(
    existing_collector_status,
    dict,
):
    existing_collector_status = {}

existing_collector_errors = sorted(
    collector
    for collector, status
    in existing_collector_status.items()
    if status != "ok"
)


configuration_tree = quality.get(
    "configuration_tree",
    {},
)

if not isinstance(
    configuration_tree,
    dict,
):
    configuration_tree = {}


entity_references = quality.get(
    "entity_references",
    {},
)

if not isinstance(
    entity_references,
    dict,
):
    entity_references = {}


automation_quality = quality.get(
    "automations",
    {},
)

if not isinstance(
    automation_quality,
    dict,
):
    automation_quality = {}


duplicate_ids = automation_quality.get(
    "duplicate_ids",
    {},
)

if not isinstance(
    duplicate_ids,
    dict,
):
    duplicate_ids = {}


# ------------------------------------------------------------
# Build report
# ------------------------------------------------------------

report = {
    "audit_version": VERSION,

    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "scope": {
        "phase":
            "update_readiness_foundation",
        "local_evidence_only":
            True,
        "external_release_notes_fetched":
            False,
        "compatibility_assessed":
            False,
        "readiness_verdict_produced":
            False,
        "note": (
            "This report collects local update "
            "and Repairs evidence. It does not "
            "yet decide whether an update is "
            "safe to install."
        ),
    },

    "system": {
        "core_version":
            system.get(
                "core_version"
            ),
        "supervisor_version":
            system.get(
                "supervisor_version"
            ),
        "os_version":
            system.get(
                "os_version"
            ),
        "installation_type":
            system.get(
                "installation_type"
            ),
    },

    "foundation_health": {
        "config_check":
            config_check_result,

        "existing_collector_error_count":
            len(
                existing_collector_errors
            ),

        "existing_collector_errors":
            existing_collector_errors,

        "missing_active_include_count":
            configuration_tree.get(
                "missing_include_count"
            ),

        "missing_entity_candidate_count":
            entity_references.get(
                "missing_count"
            ),

        "orphan_yaml_candidate_count":
            configuration_tree.get(
                "orphan_candidate_count"
            ),

        "duplicate_automation_id_group_count":
            len(
                duplicate_ids
            ),
    },

    "updates": {
        "entity_count":
            len(
                all_update_entities
            ),

        "available_count":
            len(
                available_updates
            ),

        "unavailable_count":
            len(
                unavailable_updates
            ),

        "in_progress_count":
            len(
                updates_in_progress
            ),

        "available_by_platform":
            dict(
                sorted(
                    updates_by_platform.items()
                )
            ),

        "available_by_device_class":
            dict(
                sorted(
                    updates_by_device_class.items()
                )
            ),

        "available":
            available_updates,

        "unavailable":
            unavailable_updates,

        "in_progress":
            updates_in_progress,

        "all":
            all_update_entities,
    },

    "repairs": {
        "active_count":
            len(
                normalised_repairs
            ),

        "unignored_count":
            len(
                unignored_repairs
            ),

        "ignored_count":
            len(
                ignored_repairs
            ),

        "breaking_version_count":
            len(
                breaking_repairs
            ),

        "fixable_count":
            len(
                fixable_repairs
            ),

        "by_severity":
            dict(
                sorted(
                    repairs_by_severity.items()
                )
            ),

        "active":
            normalised_repairs,

        "unignored":
            unignored_repairs,

        "ignored":
            ignored_repairs,

        "with_breaks_in_ha_version":
            breaking_repairs,

        "fixable":
            fixable_repairs,
    },

    "collector_status": {
        "states":
            states_result.get(
                "status"
            ),

        "websocket":
            websocket_result.get(
                "status"
            ),

        "websocket_command_errors":
            ws_errors,

        "audit_snapshot":
            (
                "ok"
                if audit
                else "unavailable"
            ),

        "quality_audit":
            (
                "ok"
                if quality
                else "unavailable"
            ),
    },
}


if states_result.get(
    "status"
) != "ok":
    report[
        "collector_status"
    ][
        "states_error"
    ] = states_result.get(
        "error"
    )


if websocket_result.get(
    "status"
) != "ok":
    report[
        "collector_status"
    ][
        "websocket_error"
    ] = websocket_result.get(
        "error"
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
    )


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")
print(
    "Update readiness foundation"
)
print(
    "------------------------------------------"
)

print(
    f"Update entities:              "
    f"{len(all_update_entities)}"
)

print(
    f"Updates available:            "
    f"{len(available_updates)}"
)

print(
    f"Update entities unavailable:  "
    f"{len(unavailable_updates)}"
)

print(
    f"Updates in progress:          "
    f"{len(updates_in_progress)}"
)

print(
    f"Active Repairs:               "
    f"{len(normalised_repairs)}"
)

print(
    f"Unignored Repairs:            "
    f"{len(unignored_repairs)}"
)

print(
    f"Repairs with breaking version:"
    f" {len(breaking_repairs)}"
)

print(
    f"Fixable Repairs:              "
    f"{len(fixable_repairs)}"
)

print(
    f"Config check:                 "
    f"{config_check_result}"
)

print(
    f"Existing collector errors:    "
    f"{len(existing_collector_errors)}"
)

print("")
print(
    "Available updates:"
)
print(
    "------------------------------------------"
)

if available_updates:
    for item in available_updates:
        name = (
            item.get("title")
            or item.get("name")
            or item.get("entity_id")
        )

        installed = (
            item.get(
                "installed_version"
            )
            or "unknown"
        )

        latest = (
            item.get(
                "latest_version"
            )
            or "unknown"
        )

        platform = (
            item.get(
                "platform"
            )
            or "unknown"
        )

        print(
            f"{name}: "
            f"{installed} -> {latest} "
            f"[{platform}]"
        )
else:
    print(
        "None"
    )


print("")
print(
    "Active unignored Repairs:"
)
print(
    "------------------------------------------"
)

if unignored_repairs:
    for issue in unignored_repairs:
        severity = (
            issue.get(
                "severity"
            )
            or "unknown"
        )

        domain = (
            issue.get(
                "domain"
            )
            or "unknown"
        )

        issue_id = (
            issue.get(
                "issue_id"
            )
            or "unknown"
        )

        breaks = issue.get(
            "breaks_in_ha_version"
        )

        line = (
            f"[{severity}] "
            f"{domain}.{issue_id}"
        )

        if breaks:
            line += (
                f" "
                f"(breaks in {breaks})"
            )

        print(
            line
        )
else:
    print(
        "None"
    )


print("")
print(
    f"Detailed report: {OUTPUT_FILE}"
)
