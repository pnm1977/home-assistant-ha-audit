import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

import requests
import yaml


CONFIG_ROOT = "/homeassistant"
OUTPUT_FILE = "/config/quality_audit.json"

TOKEN = os.environ["SUPERVISOR_TOKEN"]

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ------------------------------------------------------------
# Files/directories deliberately excluded
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

ENTITY_ID_PATTERN = re.compile(
    r"\b[a-z0-9_]+\.[a-z0-9_]+\b",
    re.IGNORECASE,
)

INCLUDE_PATTERN = re.compile(
    r"!(include(?:_dir_(?:list|named|merge_list|merge_named))?)"
    r"\s+([^\s#]+)"
)


# ------------------------------------------------------------
# Home Assistant-friendly YAML loader
#
# Unknown HA tags such as !secret are accepted without
# attempting to resolve their values.
# ------------------------------------------------------------

class HALoader(yaml.SafeLoader):
    pass


def unknown_tag(loader, tag_suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)

    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)

    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)

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


def discover_yaml_files():
    results = []

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

            # Never inspect secret-named files.
            if "secret" in lower:
                continue

            if not lower.endswith(
                (".yaml", ".yml")
            ):
                continue

            results.append(
                os.path.join(
                    root,
                    filename,
                )
            )

    return sorted(results)


def get_ha_json(path, timeout=30):
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


# ------------------------------------------------------------
# Discover configuration
# ------------------------------------------------------------

files = discover_yaml_files()

file_text = {
    path: read_text(path)
    for path in files
}


# ------------------------------------------------------------
# Automation audit
# ------------------------------------------------------------

automation_file = os.path.join(
    CONFIG_ROOT,
    "automations.yaml",
)

automations = safe_load_yaml(
    automation_file
)

if not isinstance(
    automations,
    list,
):
    automations = []


automation_ids = defaultdict(list)
automation_aliases = defaultdict(list)

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

    automation_id = automation.get("id")
    alias = automation.get("alias")

    if automation_id:
        automation_ids[
            str(automation_id)
        ].append(index)

    if alias:
        automation_aliases[
            str(alias).strip()
        ].append(index)

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
    for key, indexes in automation_ids.items()
    if len(indexes) > 1
}

duplicate_automation_aliases = {
    key: indexes
    for key, indexes in automation_aliases.items()
    if len(indexes) > 1
}


# ------------------------------------------------------------
# Script audit
# ------------------------------------------------------------

script_file = os.path.join(
    CONFIG_ROOT,
    "scripts.yaml",
)

scripts = safe_load_yaml(
    script_file
)

if not isinstance(
    scripts,
    dict,
):
    scripts = {}


script_aliases = defaultdict(list)
large_scripts = []


for script_key, script in scripts.items():
    if not isinstance(
        script,
        dict,
    ):
        continue

    alias = script.get("alias")

    if alias:
        script_aliases[
            str(alias).strip()
        ].append(script_key)

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
    for key, values in script_aliases.items()
    if len(values) > 1
}


# ------------------------------------------------------------
# Include audit
#
# Fully commented lines are ignored.
# ------------------------------------------------------------

include_references = []
missing_include_targets = []


for path, text in file_text.items():

    active_lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    ]

    active_text = "\n".join(
        active_lines
    )

    for match in INCLUDE_PATTERN.finditer(
        active_text
    ):
        include_type = match.group(1)
        target = match.group(2)

        resolved = os.path.normpath(
            os.path.join(
                os.path.dirname(path),
                target,
            )
        )

        exists = os.path.exists(
            resolved
        )

        record = {
            "source": relative(path),
            "type": include_type,
            "target": target,
            "exists": exists,
        }

        include_references.append(
            record
        )

        if not exists:
            missing_include_targets.append(
                record
            )


# ------------------------------------------------------------
# Current entities and services
#
# Services are collected so calls such as light.turn_on
# are not falsely reported as missing entities.
# ------------------------------------------------------------

existing_entities = set()
known_services = set()


try:
    states = get_ha_json(
        "states"
    )

    existing_entities = {
        item.get("entity_id")
        for item in states
        if isinstance(item, dict)
        and item.get("entity_id")
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
                f"{domain_name}.{service_name}"
            )

except Exception:
    known_services = set()


# ------------------------------------------------------------
# Active entity references
#
# Fully commented backup blocks are ignored.
# ------------------------------------------------------------

entity_reference_locations = defaultdict(
    set
)


for path, text in file_text.items():

    active_lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    ]

    active_text = "\n".join(
        active_lines
    )

    for candidate in ENTITY_ID_PATTERN.findall(
        active_text
    ):

        candidate = candidate.lower()

        # Service calls are not entity IDs.
        if candidate in known_services:
            continue

        # Obvious filenames / non-entity strings.
        if candidate.endswith(
            (
                ".yaml",
                ".yml",
                ".json",
                ".local",
                ".com",
                ".co",
                ".uk",
            )
        ):
            continue

        entity_reference_locations[
            candidate
        ].add(
            relative(path)
        )


missing_entity_references = []


if existing_entities:

    for entity_id, locations in (
        entity_reference_locations.items()
    ):
        if entity_id not in existing_entities:
            missing_entity_references.append(
                {
                    "entity_id": entity_id,
                    "files": sorted(
                        locations
                    ),
                }
            )


missing_entity_references.sort(
    key=lambda item:
        item["entity_id"]
)


# ------------------------------------------------------------
# Comment-heavy files
#
# Informational only. This is useful because old versions are
# intentionally sometimes retained as commented rollback code.
# ------------------------------------------------------------

comment_stats = []


for path, text in file_text.items():

    lines = text.splitlines()

    if not lines:
        continue

    comment_lines = sum(
        1
        for line in lines
        if line.lstrip().startswith("#")
    )

    ratio = (
        comment_lines / len(lines)
    )

    if (
        comment_lines >= 50
        and ratio >= 0.20
    ):
        comment_stats.append(
            {
                "file": relative(path),
                "lines": len(lines),
                "comment_lines":
                    comment_lines,
                "comment_ratio":
                    round(ratio, 3),
            }
        )


comment_stats.sort(
    key=lambda item:
        item["comment_lines"],
    reverse=True,
)


# ------------------------------------------------------------
# Build report
# ------------------------------------------------------------

quality = {
    "audit_version": "0.6.0",

    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),

    "automations": {
        "count":
            len(automations),

        "duplicate_ids":
            duplicate_automation_ids,

        "duplicate_aliases":
            duplicate_automation_aliases,

        "large":
            sorted(
                large_automations,
                key=lambda item:
                    item["lines"],
                reverse=True,
            ),
    },

    "scripts": {
        "count":
            len(scripts),

        "duplicate_aliases":
            duplicate_script_aliases,

        "large":
            sorted(
                large_scripts,
                key=lambda item:
                    item["lines"],
                reverse=True,
            ),
    },

    "includes": {
        "count":
            len(include_references),

        "missing_count":
            len(
                missing_include_targets
            ),

        "missing":
            missing_include_targets,
    },

    "entity_references": {
        "unique_candidates":
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
                "Missing entity references are candidates "
                "for review, not automatically faults."
            ),
    },

    "comment_heavy_files":
        comment_stats,

    "notes": {
        "fully_commented_lines_ignored":
            True,

        "commented_backup_blocks":
            (
                "Commented backup YAML is not treated "
                "as active configuration."
            ),

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
print("Configuration quality audit")
print("------------------------------------------")

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
    f"Missing include targets:     "
    f"{len(missing_include_targets)}"
)

print(
    f"Entity reference candidates: "
    f"{len(entity_reference_locations)}"
)

print(
    f"Missing entity candidates:   "
    f"{len(missing_entity_references)}"
)

print(
    f"Comment-heavy YAML files:    "
    f"{len(comment_stats)}"
)


if duplicate_automation_ids:
    print("")
    print("Duplicate automation IDs:")

    for automation_id, indexes in (
        duplicate_automation_ids.items()
    ):
        print(
            f"  {automation_id}: "
            f"{indexes}"
        )


if duplicate_automation_aliases:
    print("")
    print("Duplicate automation names:")

    for alias, indexes in (
        duplicate_automation_aliases.items()
    ):
        print(
            f"  {alias}: "
            f"{indexes}"
        )


if duplicate_script_aliases:
    print("")
    print("Duplicate script names:")

    for alias, keys in (
        duplicate_script_aliases.items()
    ):
        print(
            f"  {alias}: "
            f"{keys}"
        )


if missing_include_targets:
    print("")
    print("Missing include targets:")

    for item in (
        missing_include_targets[:20]
    ):
        print(
            f"  {item['source']} -> "
            f"{item['target']}"
        )


if missing_entity_references:
    print("")
    print("First missing entity candidates:")

    for item in (
        missing_entity_references[:25]
    ):
        print(
            f"  {item['entity_id']} "
            f"({', '.join(item['files'])})"
        )


if comment_stats:
    print("")
    print("Comment-heavy files:")

    for item in (
        comment_stats[:15]
    ):
        percentage = (
            item["comment_ratio"]
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
