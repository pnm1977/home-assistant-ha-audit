import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import requests
import yaml


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

CONFIG_ROOT = "/homeassistant"

ROOT_CONFIG = os.path.join(
    CONFIG_ROOT,
    "configuration.yaml",
)

OUTPUT_FILE = "/config/quality_audit.json"

TOKEN = os.environ["SUPERVISOR_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Exclusions
# ------------------------------------------------------------

EXCLUDED_DIRS = {
    ".git",
    ".storage",
    ".cloud",
    "backup",
    "backups",
    "custom_components",
    "deps",
    "esphome",
    "media",
    "tts",
    "www",
}

ENTITY_SCAN_EXCLUDED_TOP_LEVEL = {
    "themes",
    "blueprints",
}

INCLUDE_PATTERN = re.compile(
    r"!(include(?:_dir_(?:list|named|merge_list|merge_named))?)"
    r"\s+([^\s#]+)"
)

DIRECT_ENTITY_PATTERN = re.compile(
    r"(?<![\w.])"
    r"([a-z_][a-z0-9_]*)"
    r"\."
    r"([a-z0-9_]+)"
    r"\b",
    re.IGNORECASE,
)

STATES_ENTITY_PATTERN = re.compile(
    r"\bstates\."
    r"([a-z_][a-z0-9_]*)"
    r"\."
    r"([a-z0-9_]+)"
    r"\b",
    re.IGNORECASE,
)


COMMON_ENTITY_DOMAINS = {
    "alarm_control_panel",
    "automation",
    "binary_sensor",
    "button",
    "calendar",
    "camera",
    "climate",
    "cover",
    "device_tracker",
    "event",
    "fan",
    "humidifier",
    "image",
    "input_boolean",
    "input_button",
    "input_datetime",
    "input_number",
    "input_select",
    "input_text",
    "light",
    "lock",
    "media_player",
    "number",
    "person",
    "remote",
    "scene",
    "script",
    "select",
    "sensor",
    "siren",
    "sun",
    "switch",
    "text",
    "time",
    "timer",
    "update",
    "vacuum",
    "valve",
    "water_heater",
    "weather",
    "zone",
}


# ------------------------------------------------------------
# Home Assistant-friendly YAML loader
# ------------------------------------------------------------

class HALoader(yaml.SafeLoader):
    pass


def unknown_tag(
    loader,
    tag_suffix,
    node,
):
    if isinstance(
        node,
        yaml.ScalarNode,
    ):
        return loader.construct_scalar(
            node
        )

    if isinstance(
        node,
        yaml.SequenceNode,
    ):
        return loader.construct_sequence(
            node
        )

    if isinstance(
        node,
        yaml.MappingNode,
    ):
        return loader.construct_mapping(
            node
        )

    return None


HALoader.add_multi_constructor(
    "!",
    unknown_tag,
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def relative(path):
    return os.path.relpath(
        path,
        CONFIG_ROOT,
    )


def read_text(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return handle.read()

    except Exception:
        return ""


def safe_load_yaml(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return yaml.load(
                handle,
                Loader=HALoader,
            )

    except Exception:
        return None


def discover_all_yaml_files():
    results = set()

    for root, dirs, filenames in os.walk(
        CONFIG_ROOT
    ):
        dirs[:] = [
            directory
            for directory in dirs
            if directory not in EXCLUDED_DIRS
            and not directory.startswith(".")
        ]

        for filename in filenames:
            lower = filename.lower()

            if "secret" in lower:
                continue

            if not lower.endswith(
                (".yaml", ".yml")
            ):
                continue

            results.add(
                os.path.normpath(
                    os.path.join(
                        root,
                        filename,
                    )
                )
            )

    return results


def yaml_files_in_directory(
    directory,
):
    found = set()

    if not os.path.isdir(
        directory
    ):
        return found

    for root, dirs, filenames in os.walk(
        directory
    ):
        dirs[:] = [
            item
            for item in dirs
            if item not in EXCLUDED_DIRS
            and not item.startswith(".")
        ]

        for filename in filenames:
            lower = filename.lower()

            if "secret" in lower:
                continue

            if lower.endswith(
                (".yaml", ".yml")
            ):
                found.add(
                    os.path.normpath(
                        os.path.join(
                            root,
                            filename,
                        )
                    )
                )

    return found


def get_ha_json(
    path,
    timeout=30,
):
    response = requests.get(
        f"http://supervisor/core/api/{path}",
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


def classify_inactive_file(
    path,
):
    rel = relative(
        path
    )

    rel_lower = rel.lower()

    filename = os.path.basename(
        rel_lower
    )

    if rel_lower.startswith(
        "blueprints/"
    ):
        return "blueprint"

    if rel_lower.startswith(
        "zigbee2mqtt/"
    ):
        return "zigbee2mqtt"

    backup_markers = (
        "backup",
        "_old",
        "-old",
        ".old",
        "_copy",
        "-copy",
    )

    if any(
        marker in filename
        for marker in backup_markers
    ):
        return "backup_or_archive"

    return "orphan_candidate"


# ------------------------------------------------------------
# Discover all YAML
# ------------------------------------------------------------

all_yaml_files = (
    discover_all_yaml_files()
)


# ------------------------------------------------------------
# Discover ACTIVE include tree
# ------------------------------------------------------------

active_files = set()

missing_include_targets = []

include_references = []

files_to_process = []


if os.path.isfile(
    ROOT_CONFIG
):
    files_to_process.append(
        ROOT_CONFIG
    )


while files_to_process:

    current_file = os.path.normpath(
        files_to_process.pop()
    )

    if current_file in active_files:
        continue

    if not os.path.isfile(
        current_file
    ):
        continue

    active_files.add(
        current_file
    )

    text = read_text(
        current_file
    )

    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):
        if line.lstrip().startswith(
            "#"
        ):
            continue

        for match in INCLUDE_PATTERN.finditer(
            line
        ):
            include_type = match.group(1)

            target = match.group(2)

            resolved = os.path.normpath(
                os.path.join(
                    os.path.dirname(
                        current_file
                    ),
                    target,
                )
            )

            is_directory_include = (
                include_type.startswith(
                    "include_dir_"
                )
            )

            exists = (
                os.path.isdir(
                    resolved
                )
                if is_directory_include
                else os.path.isfile(
                    resolved
                )
            )

            record = {
                "source": relative(
                    current_file
                ),
                "line": line_number,
                "type": include_type,
                "target": target,
                "resolved": (
                    relative(
                        resolved
                    )
                    if resolved.startswith(
                        CONFIG_ROOT
                    )
                    else resolved
                ),
                "exists": exists,
            }

            include_references.append(
                record
            )

            if not exists:
                missing_include_targets.append(
                    record
                )

                continue

            if is_directory_include:
                files_to_process.extend(
                    yaml_files_in_directory(
                        resolved
                    )
                )

            else:
                files_to_process.append(
                    resolved
                )


inactive_files = (
    all_yaml_files
    - active_files
)


# ------------------------------------------------------------
# Classify inactive YAML
# ------------------------------------------------------------

inactive_by_type = {
    "blueprint": [],
    "zigbee2mqtt": [],
    "backup_or_archive": [],
    "orphan_candidate": [],
}


for path in sorted(
    inactive_files
):
    category = (
        classify_inactive_file(
            path
        )
    )

    inactive_by_type[
        category
    ].append(
        relative(
            path
        )
    )


# ------------------------------------------------------------
# Automation audit
# ------------------------------------------------------------

automation_file = os.path.join(
    CONFIG_ROOT,
    "automations.yaml",
)

automations = []


if automation_file in active_files:

    loaded = safe_load_yaml(
        automation_file
    )

    if isinstance(
        loaded,
        list,
    ):
        automations = loaded


automation_ids = defaultdict(
    list
)

automation_aliases = defaultdict(
    list
)

large_automations = []


for index, automation in enumerate(
    automations,
    start=1,
):
    if not isinstance(
        automation,
        dict,
    ):
        continue

    automation_id = automation.get(
        "id"
    )

    alias = automation.get(
        "alias"
    )

    if automation_id:
        automation_ids[
            str(
                automation_id
            )
        ].append(
            index
        )

    if alias:
        automation_aliases[
            str(
                alias
            ).strip()
        ].append(
            index
        )

    rendered = yaml.safe_dump(
        automation,
        sort_keys=False,
        allow_unicode=True,
    )

    line_count = len(
        rendered.splitlines()
    )

    if line_count >= 100:
        large_automations.append(
            {
                "index": index,
                "id": automation_id,
                "alias": alias,
                "lines": line_count,
            }
        )


duplicate_automation_ids = {
    key: indexes
    for key, indexes in (
        automation_ids.items()
    )
    if len(
        indexes
    ) > 1
}


duplicate_automation_aliases = {
    key: indexes
    for key, indexes in (
        automation_aliases.items()
    )
    if len(
        indexes
    ) > 1
}


# ------------------------------------------------------------
# Script audit
# ------------------------------------------------------------

script_file = os.path.join(
    CONFIG_ROOT,
    "scripts.yaml",
)

scripts = {}


if script_file in active_files:

    loaded = safe_load_yaml(
        script_file
    )

    if isinstance(
        loaded,
        dict,
    ):
        scripts = loaded


script_aliases = defaultdict(
    list
)

large_scripts = []


for script_key, script in (
    scripts.items()
):
    if not isinstance(
        script,
        dict,
    ):
        continue

    alias = script.get(
        "alias"
    )

    if alias:
        script_aliases[
            str(
                alias
            ).strip()
        ].append(
            script_key
        )

    rendered = yaml.safe_dump(
        script,
        sort_keys=False,
        allow_unicode=True,
    )

    line_count = len(
        rendered.splitlines()
    )

    if line_count >= 100:
        large_scripts.append(
            {
                "key": script_key,
                "alias": alias,
                "lines": line_count,
            }
        )


duplicate_script_aliases = {
    key: values
    for key, values in (
        script_aliases.items()
    )
    if len(
        values
    ) > 1
}


# ------------------------------------------------------------
# Current HA entities and services
# ------------------------------------------------------------

existing_entities = set()

known_services = set()

live_entity_domains = set()


try:
    states = get_ha_json(
        "states"
    )

    existing_entities = {
        item.get(
            "entity_id"
        )
        for item in states
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "entity_id"
        )
    }

    live_entity_domains = {
        entity_id.split(
            ".",
            1,
        )[0]
        for entity_id in existing_entities
        if "." in entity_id
    }

except Exception:
    states = []


try:
    services = get_ha_json(
        "services"
    )

    for domain in services:
        domain_name = domain.get(
            "domain"
        )

        for service_name in domain.get(
            "services",
            {}
        ):
            known_services.add(
                (
                    f"{domain_name}."
                    f"{service_name}"
                ).lower()
            )

except Exception:
    known_services = set()


allowed_entity_domains = (
    COMMON_ENTITY_DOMAINS
    | live_entity_domains
)


# ------------------------------------------------------------
# Active entity-reference audit WITH line numbers
# ------------------------------------------------------------

entity_reference_locations = defaultdict(
    lambda: defaultdict(set)
)


for path in sorted(
    active_files
):

    relative_path = relative(
        path
    )

    top_level = relative_path.split(
        os.sep,
        1,
    )[0]


    if (
        top_level
        in ENTITY_SCAN_EXCLUDED_TOP_LEVEL
    ):
        continue


    text = read_text(
        path
    )


    for line_number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if line.lstrip().startswith(
            "#"
        ):
            continue


        candidates = set()


        for match in (
            DIRECT_ENTITY_PATTERN.finditer(
                line
            )
        ):
            domain = (
                match.group(1).lower()
            )

            object_id = (
                match.group(2).lower()
            )

            if domain == "states":
                continue

            candidates.add(
                f"{domain}.{object_id}"
            )


        for match in (
            STATES_ENTITY_PATTERN.finditer(
                line
            )
        ):
            domain = (
                match.group(1).lower()
            )

            object_id = (
                match.group(2).lower()
            )

            candidates.add(
                f"{domain}.{object_id}"
            )


        for candidate in candidates:

            if candidate in known_services:
                continue

            domain = candidate.split(
                ".",
                1,
            )[0]

            if (
                domain
                not in allowed_entity_domains
            ):
                continue

            entity_reference_locations[
                candidate
            ][
                relative_path
            ].add(
                line_number
            )


# ------------------------------------------------------------
# Missing entity candidates
# ------------------------------------------------------------

missing_entity_references = []


if existing_entities:

    for entity_id, locations in (
        entity_reference_locations.items()
    ):

        if (
            entity_id
            in existing_entities
        ):
            continue


        formatted_locations = []


        for file_path in sorted(
            locations
        ):
            formatted_locations.append(
                {
                    "file": file_path,
                    "lines": sorted(
                        locations[
                            file_path
                        ]
                    ),
                }
            )


        missing_entity_references.append(
            {
                "entity_id":
                    entity_id,

                "locations":
                    formatted_locations,
            }
        )


missing_entity_references.sort(
    key=lambda item:
        item[
            "entity_id"
        ]
)


# ------------------------------------------------------------
# Comment-heavy ACTIVE files
# ------------------------------------------------------------

comment_stats = []


for path in sorted(
    active_files
):

    text = read_text(
        path
    )

    lines = text.splitlines()

    if not lines:
        continue


    comment_lines = sum(
        1
        for line in lines
        if line.lstrip().startswith(
            "#"
        )
    )


    ratio = (
        comment_lines
        / len(
            lines
        )
    )


    if (
        comment_lines >= 50
        and ratio >= 0.20
    ):

        comment_stats.append(
            {
                "file":
                    relative(
                        path
                    ),

                "lines":
                    len(
                        lines
                    ),

                "comment_lines":
                    comment_lines,

                "comment_ratio":
                    round(
                        ratio,
                        3,
                    ),
            }
        )


comment_stats.sort(
    key=lambda item:
        item[
            "comment_lines"
        ],
    reverse=True,
)


# ------------------------------------------------------------
# Build report
# ------------------------------------------------------------

quality = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "configuration_tree": {
        "root":
            "configuration.yaml",

        "active_yaml_count":
            len(
                active_files
            ),

        "inactive_yaml_count":
            len(
                inactive_files
            ),

        "active_yaml":
            sorted(
                relative(
                    path
                )
                for path
                in active_files
            ),

        "inactive_classification":
            inactive_by_type,

        "orphan_candidate_count":
            len(
                inactive_by_type[
                    "orphan_candidate"
                ]
            ),

        "include_count":
            len(
                include_references
            ),

        "missing_include_count":
            len(
                missing_include_targets
            ),

        "missing_includes":
            missing_include_targets,
    },

    "automations": {
        "count":
            len(
                automations
            ),

        "duplicate_ids":
            duplicate_automation_ids,

        "duplicate_aliases":
            duplicate_automation_aliases,

        "large":
            sorted(
                large_automations,
                key=lambda item:
                    item[
                        "lines"
                    ],
                reverse=True,
            ),
    },

    "scripts": {
        "count":
            len(
                scripts
            ),

        "duplicate_aliases":
            duplicate_script_aliases,

        "large":
            sorted(
                large_scripts,
                key=lambda item:
                    item[
                        "lines"
                    ],
                reverse=True,
            ),
    },

    "entity_references": {
        "unique_active_references":
            len(
                entity_reference_locations
            ),

        "missing_count":
            len(
                missing_entity_references
            ),

        "missing_candidates":
            missing_entity_references,

        "note":
            (
                "Candidates are for review. "
                "A missing reference is not "
                "automatically a fault."
            ),
    },

    "comment_heavy_active_files":
        comment_stats,

    "notes": {
        "fully_commented_lines_ignored":
            True,

        "commented_backup_blocks":
            (
                "Commented backup YAML is "
                "not treated as active."
            ),

        "blueprints_classified_separately":
            True,

        "zigbee2mqtt_classified_separately":
            True,

        "backup_yaml_classified_separately":
            True,

        "themes_and_blueprints_excluded_from_entity_check":
            True,

        "secret_named_files_excluded":
            True,

        "storage_directory_excluded":
            True,

        "configuration_is_read_only":
            True,
    },
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:

    json.dump(
        quality,
        handle,
        indent=2,
    )


# ------------------------------------------------------------
# Console summary
# ------------------------------------------------------------

print("")
print(
    "Configuration quality audit"
)

print(
    "------------------------------------------"
)

print(
    f"Active YAML files:           "
    f"{len(active_files)}"
)

print(
    f"Blueprint YAML files:        "
    f"{len(inactive_by_type['blueprint'])}"
)

print(
    f"Zigbee2MQTT YAML files:      "
    f"{len(inactive_by_type['zigbee2mqtt'])}"
)

print(
    f"Backup/archive YAML files:   "
    f"{len(inactive_by_type['backup_or_archive'])}"
)

print(
    f"Orphan YAML candidates:      "
    f"{len(inactive_by_type['orphan_candidate'])}"
)

print(
    f"Missing active includes:     "
    f"{len(missing_include_targets)}"
)

print(
    f"Automations:                 "
    f"{len(automations)}"
)

print(
    f"Duplicate automation IDs:    "
    f"{len(duplicate_automation_ids)}"
)

print(
    f"Duplicate automation names:  "
    f"{len(duplicate_automation_aliases)}"
)

print(
    f"Large automations:           "
    f"{len(large_automations)}"
)

print(
    f"Scripts:                     "
    f"{len(scripts)}"
)

print(
    f"Duplicate script names:      "
    f"{len(duplicate_script_aliases)}"
)

print(
    f"Large scripts:               "
    f"{len(large_scripts)}"
)

print(
    f"Active entity references:    "
    f"{len(entity_reference_locations)}"
)

print(
    f"Missing entity candidates:   "
    f"{len(missing_entity_references)}"
)

print(
    f"Comment-heavy active files:  "
    f"{len(comment_stats)}"
)


if missing_include_targets:

    print("")

    print(
        "Missing ACTIVE include targets:"
    )

    for item in (
        missing_include_targets[
            :20
        ]
    ):
        print(
            f"  {item['source']}:"
            f"{item['line']} -> "
            f"{item['target']}"
        )


if inactive_by_type[
    "orphan_candidate"
]:

    print("")

    print(
        "Orphan YAML candidates:"
    )

    for path in (
        inactive_by_type[
            "orphan_candidate"
        ][
            :20
        ]
    ):
        print(
            f"  {path}"
        )


if inactive_by_type[
    "backup_or_archive"
]:

    print("")

    print(
        "Backup/archive YAML:"
    )

    for path in (
        inactive_by_type[
            "backup_or_archive"
        ][
            :20
        ]
    ):
        print(
            f"  {path}"
        )


if duplicate_automation_ids:

    print("")

    print(
        "Duplicate automation IDs:"
    )

    for automation_id, indexes in (
        duplicate_automation_ids.items()
    ):
        print(
            f"  {automation_id}: "
            f"{indexes}"
        )


if duplicate_automation_aliases:

    print("")

    print(
        "Duplicate automation names:"
    )

    for alias, indexes in (
        duplicate_automation_aliases.items()
    ):
        print(
            f"  {alias}: "
            f"{indexes}"
        )


if duplicate_script_aliases:

    print("")

    print(
        "Duplicate script names:"
    )

    for alias, keys in (
        duplicate_script_aliases.items()
    ):
        print(
            f"  {alias}: "
            f"{keys}"
        )


if missing_entity_references:

    print("")

    print(
        "First missing entity candidates:"
    )

    for item in (
        missing_entity_references[
            :25
        ]
    ):

        print(
            f"  {item['entity_id']}"
        )

        for location in (
            item[
                "locations"
            ]
        ):

            line_text = ",".join(
                str(
                    line
                )
                for line in location[
                    "lines"
                ]
            )

            print(
                f"    "
                f"{location['file']}:"
                f"{line_text}"
            )


if comment_stats:

    print("")

    print(
        "Comment-heavy active files:"
    )

    for item in (
        comment_stats[
            :15
        ]
    ):

        percentage = (
            item[
                "comment_ratio"
            ]
            * 100
        )

        print(
            f"  {item['file']}: "
            f"{item['comment_lines']} "
            f"comment lines "
            f"({percentage:.0f}%)"
        )


print("")

print(
    f"Quality report saved: "
    f"{OUTPUT_FILE}"
)
