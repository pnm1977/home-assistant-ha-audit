import json
import os
from collections import Counter, defaultdict

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

OUTPUT_FILE = "/config/availability_audit.json"


EXPECTED_OFFLINE_LABEL = (
    "HA Audit - Expected Offline"
)

MAINTENANCE_LABEL = (
    "HA Audit - Maintenance"
)


HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def normalise_label_name(value):
    return str(
        value or ""
    ).strip().casefold()


def get_registry_payload():
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

        next_id = 1

        def command(command_type):
            nonlocal next_id

            message_id = next_id
            next_id += 1

            ws.send(
                json.dumps(
                    {
                        "id": message_id,
                        "type": command_type,
                    }
                )
            )

            while True:
                response = json.loads(
                    ws.recv()
                )

                if response.get("id") != message_id:
                    continue

                if response.get("type") != "result":
                    continue

                if not response.get("success"):
                    raise RuntimeError(
                        f"{command_type} failed: "
                        f"{response.get('error')}"
                    )

                return response.get(
                    "result",
                    [],
                )

        labels = command(
            "config/label_registry/list"
        )

        devices = command(
            "config/device_registry/list"
        )

        entities = command(
            "config/entity_registry/list"
        )

        return {
            "labels": labels,
            "devices": devices,
            "entities": entities,
        }

    finally:
        ws.close()


def get_states():
    response = requests.get(
        f"{SUPERVISOR}/core/api/states",
        headers=HEADERS,
        timeout=60,
    )

    response.raise_for_status()

    payload = response.json()

    if not isinstance(
        payload,
        list,
    ):
        raise RuntimeError(
            "States API returned an "
            "unexpected response"
        )

    return payload


def entity_ids_from_snapshot_section(
    section,
):
    result = set()

    if not isinstance(
        section,
        dict,
    ):
        return result

    items = section.get(
        "entities",
        [],
    )

    if not isinstance(
        items,
        list,
    ):
        return result

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        entity_id = item.get(
            "entity_id"
        )

        if entity_id:
            result.add(
                entity_id
            )

    return result


# ------------------------------------------------------------
# Collect data
# ------------------------------------------------------------

audit = load_json(
    AUDIT_FILE
)

registry = get_registry_payload()

states = get_states()


label_entries = registry.get(
    "labels",
    [],
)

device_entries = registry.get(
    "devices",
    [],
)

entity_entries = registry.get(
    "entities",
    [],
)


label_name_by_id = {}

for item in label_entries:
    if not isinstance(
        item,
        dict,
    ):
        continue

    label_id = (
        item.get("label_id")
        or item.get("id")
    )

    name = item.get(
        "name"
    )

    if label_id and name:
        label_name_by_id[
            label_id
        ] = name


expected_label_key = (
    normalise_label_name(
        EXPECTED_OFFLINE_LABEL
    )
)

maintenance_label_key = (
    normalise_label_name(
        MAINTENANCE_LABEL
    )
)


available_label_keys = {
    normalise_label_name(
        name
    )
    for name in label_name_by_id.values()
}


expected_label_found = (
    expected_label_key
    in available_label_keys
)

maintenance_label_found = (
    maintenance_label_key
    in available_label_keys
)


devices_by_id = {
    item.get("id"): item
    for item in device_entries
    if isinstance(
        item,
        dict,
    )
    and item.get("id")
}


entities_by_id = {
    item.get("entity_id"): item
    for item in entity_entries
    if isinstance(
        item,
        dict,
    )
    and item.get("entity_id")
}


states_by_id = {
    item.get("entity_id"): item
    for item in states
    if isinstance(
        item,
        dict,
    )
    and item.get("entity_id")
}


not_provided_ids = (
    entity_ids_from_snapshot_section(
        audit.get(
            "entities",
            {},
        ).get(
            "not_currently_provided",
            {},
        )
    )
)


# ------------------------------------------------------------
# Build device state picture
# ------------------------------------------------------------

device_state_entity_ids = defaultdict(
    list
)

for entity_id, registry_entry in (
    entities_by_id.items()
):
    device_id = registry_entry.get(
        "device_id"
    )

    if (
        device_id
        and entity_id in states_by_id
    ):
        device_state_entity_ids[
            device_id
        ].append(
            entity_id
        )


device_health = {}

for device_id, entity_ids in (
    device_state_entity_ids.items()
):
    healthy = []
    unavailable = []
    unknown = []

    for entity_id in entity_ids:
        state = str(
            states_by_id[
                entity_id
            ].get(
                "state",
                "",
            )
        ).strip().lower()

        if state == "unavailable":
            unavailable.append(
                entity_id
            )

        elif state == "unknown":
            unknown.append(
                entity_id
            )

        else:
            healthy.append(
                entity_id
            )

    device_health[
        device_id
    ] = {
        "healthy_entity_ids":
            healthy,

        "unavailable_entity_ids":
            unavailable,

        "unknown_entity_ids":
            unknown,

        "healthy_count":
            len(
                healthy
            ),

        "unavailable_count":
            len(
                unavailable
            ),

        "unknown_count":
            len(
                unknown
            ),
    }


# ------------------------------------------------------------
# Label helpers
# ------------------------------------------------------------

def label_names(label_ids):
    result = []

    for label_id in (
        label_ids or []
    ):
        name = label_name_by_id.get(
            label_id
        )

        if name:
            result.append(
                name
            )

    return sorted(
        set(
            result
        )
    )


def device_labels(device_id):
    device = devices_by_id.get(
        device_id,
        {},
    )

    return label_names(
        device.get(
            "labels",
            [],
        )
    )


def entity_labels(entity_id):
    entity = entities_by_id.get(
        entity_id,
        {},
    )

    return label_names(
        entity.get(
            "labels",
            [],
        )
    )


def has_label(
    labels,
    target_key,
):
    return any(
        normalise_label_name(
            item
        ) == target_key
        for item in labels
    )


# ------------------------------------------------------------
# Classify unavailable entities
# ------------------------------------------------------------

classification_counts = Counter()

classified_entities = []

platform_counts = defaultdict(
    Counter
)

device_classifications = defaultdict(
    lambda: {
        "entity_ids": [],
        "classifications": Counter(),
    }
)


for entity_id, state_entry in (
    states_by_id.items()
):
    state = str(
        state_entry.get(
            "state",
            "",
        )
    ).strip().lower()

    if state != "unavailable":
        continue

    # Not-currently-provided entities already have their own
    # cleanup and history-safety audit. Do not mix them into
    # normal availability classification.
    if entity_id in not_provided_ids:
        continue

    registry_entry = entities_by_id.get(
        entity_id,
        {},
    )

    device_id = registry_entry.get(
        "device_id"
    )

    platform = (
        registry_entry.get(
            "platform"
        )
        or "unknown"
    )

    assigned_labels = sorted(
        set(
            device_labels(
                device_id
            )
            + entity_labels(
                entity_id
            )
        )
    )

    health = device_health.get(
        device_id,
        {},
    )

    healthy_count = health.get(
        "healthy_count",
        0,
    )


    if has_label(
        assigned_labels,
        maintenance_label_key,
    ):
        classification = (
            "maintenance"
        )

    elif has_label(
        assigned_labels,
        expected_label_key,
    ):
        classification = (
            "expected_offline"
        )

    elif (
        device_id
        and healthy_count > 0
    ):
        classification = (
            "partial_availability"
        )

    elif device_id:
        classification = (
            "whole_device_unavailable_unlabelled"
        )

    else:
        classification = (
            "ungrouped_unavailable"
        )


    device = devices_by_id.get(
        device_id,
        {},
    )

    device_name = (
        device.get(
            "name_by_user"
        )
        or device.get(
            "name"
        )
    )


    item = {
        "entity_id":
            entity_id,

        "name":
            registry_entry.get(
                "name"
            )
            or registry_entry.get(
                "original_name"
            )
            or state_entry.get(
                "attributes",
                {},
            ).get(
                "friendly_name"
            ),

        "platform":
            platform,

        "device_id":
            device_id,

        "device":
            device_name,

        "area_id":
            registry_entry.get(
                "area_id"
            )
            or device.get(
                "area_id"
            ),

        "labels":
            assigned_labels,

        "classification":
            classification,

        "device_state_summary":
            health
            if device_id
            else None,
    }


    classified_entities.append(
        item
    )

    classification_counts[
        classification
    ] += 1

    platform_counts[
        platform
    ][
        classification
    ] += 1


    device_key = (
        device_id
        or f"entity:{entity_id}"
    )

    device_group = (
        device_classifications[
            device_key
        ]
    )

    device_group[
        "entity_ids"
    ].append(
        entity_id
    )

    device_group[
        "classifications"
    ][
        classification
    ] += 1

    device_group[
        "device_id"
    ] = device_id

    device_group[
        "device"
    ] = device_name

    device_group[
        "labels"
    ] = assigned_labels

    device_group[
        "platforms"
    ] = sorted(
        set(
            device_group.get(
                "platforms",
                []
            )
            + [
                platform
            ]
        )
    )

    device_group[
        "device_state_summary"
    ] = (
        health
        if device_id
        else None
    )


classified_entities.sort(
    key=lambda item: (
        item.get(
            "classification",
            "",
        ),
        item.get(
            "device",
            "",
        )
        or "",
        item.get(
            "entity_id",
            "",
        ),
    )
)


# ------------------------------------------------------------
# Device-level summary
# ------------------------------------------------------------

device_results = []

device_classification_counts = Counter()


for device_key, group in (
    device_classifications.items()
):
    classifications = (
        group[
            "classifications"
        ]
    )

    if classifications.get(
        "maintenance"
    ):
        device_classification = (
            "maintenance"
        )

    elif classifications.get(
        "expected_offline"
    ):
        device_classification = (
            "expected_offline"
        )

    elif classifications.get(
        "partial_availability"
    ):
        device_classification = (
            "partial_availability"
        )

    elif classifications.get(
        "whole_device_unavailable_unlabelled"
    ):
        device_classification = (
            "whole_device_unavailable_unlabelled"
        )

    else:
        device_classification = (
            "ungrouped_unavailable"
        )


    device_classification_counts[
        device_classification
    ] += 1


    device_results.append(
        {
            "device_key":
                device_key,

            "device_id":
                group.get(
                    "device_id"
                ),

            "device":
                group.get(
                    "device"
                ),

            "platforms":
                group.get(
                    "platforms",
                    [],
                ),

            "labels":
                group.get(
                    "labels",
                    [],
                ),

            "classification":
                device_classification,

            "unavailable_entity_count":
                len(
                    group.get(
                        "entity_ids",
                        [],
                    )
                ),

            "unavailable_entity_ids":
                sorted(
                    group.get(
                        "entity_ids",
                        [],
                    )
                ),

            "device_state_summary":
                group.get(
                    "device_state_summary"
                ),
        }
    )


device_results.sort(
    key=lambda item: (
        item.get(
            "classification",
            "",
        ),
        item.get(
            "device",
            "",
        )
        or "",
        item.get(
            "device_key",
            "",
        ),
    )
)


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

report = {
    "audit_version":
        VERSION,

    "labels": {
        "expected_offline": {
            "name":
                EXPECTED_OFFLINE_LABEL,

            "exists":
                expected_label_found,
        },

        "maintenance": {
            "name":
                MAINTENANCE_LABEL,

            "exists":
                maintenance_label_found,
        },
    },

    "policy": {
        "important":
            (
                "Unavailable does not automatically mean "
                "faulty. Explicit HA Audit labels take "
                "priority. Unlabelled devices with some "
                "healthy entities are classified as partial "
                "availability. Unlabelled devices with no "
                "healthy state entities are review items, "
                "not automatic faults."
            ),

        "not_currently_provided":
            (
                "Entities already classified as not "
                "currently provided are excluded here "
                "because they have a separate cleanup "
                "and history-safety audit."
            ),
    },

    "summary": {
        "unavailable_entities_classified":
            len(
                classified_entities
            ),

        "excluded_not_currently_provided":
            len(
                not_provided_ids
            ),

        "entity_classification_counts":
            dict(
                classification_counts
            ),

        "device_classification_counts":
            dict(
                device_classification_counts
            ),
    },

    "status_by_platform": {
        platform:
            dict(
                counts
            )
        for platform, counts
        in sorted(
            platform_counts.items()
        )
    },

    "devices":
        device_results,

    "entities":
        classified_entities,
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


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")

print(
    "Unavailable entity availability audit"
)

print(
    "------------------------------------------"
)

print(
    f"Unavailable entities classified: "
    f"{len(classified_entities)}"
)

print(
    f"Expected offline:               "
    f"{classification_counts.get('expected_offline', 0)}"
)

print(
    f"Maintenance:                    "
    f"{classification_counts.get('maintenance', 0)}"
)

print(
    f"Partial availability:           "
    f"{classification_counts.get('partial_availability', 0)}"
)

print(
    f"Whole device unavailable "
    f"(unlabelled): "
    f"{classification_counts.get('whole_device_unavailable_unlabelled', 0)}"
)

print(
    f"Ungrouped unavailable:          "
    f"{classification_counts.get('ungrouped_unavailable', 0)}"
)

print("")

print(
    f"Expected-offline label exists:  "
    f"{expected_label_found}"
)

print(
    f"Maintenance label exists:       "
    f"{maintenance_label_found}"
)

print("")

print(
    "Unavailable does not automatically "
    "mean faulty."
)

print(
    "Unlabelled whole-device outages are "
    "review items until their expected "
    "behaviour is known."
)

print("")

print(
    f"Availability report saved: "
    f"{OUTPUT_FILE}"
)
