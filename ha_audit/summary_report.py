import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"
REFERENCE_FILE = "/config/not_provided_reference_audit.json"

OUTPUT_FILE = "/config/ha_audit_latest.txt"


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def count_mapping(value):
    if isinstance(value, dict):
        return len(value)

    return 0


def format_generated_time(audit):
    generated_at = audit.get(
        "generated_at"
    )

    timezone_name = (
        audit.get(
            "system",
            {},
        ).get(
            "timezone"
        )
        or "UTC"
    )

    if not generated_at:
        return "unknown"

    try:
        stamp = datetime.fromisoformat(
            generated_at.replace(
                "Z",
                "+00:00",
            )
        )

        local_stamp = stamp.astimezone(
            ZoneInfo(
                timezone_name
            )
        )

        return (
            local_stamp.strftime(
                "%d %b %Y %H:%M:%S"
            )
            + f" ({timezone_name})"
        )

    except Exception:
        return generated_at


audit = load_json(
    AUDIT_FILE
)

quality = load_json(
    QUALITY_FILE
)

reference = load_json(
    REFERENCE_FILE
)


system = audit.get(
    "system",
    {},
)

inventory = audit.get(
    "inventory",
    {},
)

entities = audit.get(
    "entities",
    {},
)

changes = audit.get(
    "changes_since_previous",
    {},
)

updates = audit.get(
    "updates",
    {},
)

collectors = audit.get(
    "collector_status",
    {},
)


configuration_tree = quality.get(
    "configuration_tree",
    {},
)

automations = quality.get(
    "automations",
    {},
)

scripts = quality.get(
    "scripts",
    {},
)

entity_references = quality.get(
    "entity_references",
    {},
)


reference_summary = reference.get(
    "summary",
    {},
)


config_check = audit.get(
    "configuration_check",
    {},
)

if config_check.get(
    "status"
) == "ok":

    config_result = (
        config_check.get(
            "data",
            {},
        ).get(
            "result"
        )
        or "unknown"
    )

else:
    config_result = "ERROR"


collector_errors = [
    name
    for name, status
    in collectors.items()
    if status != "ok"
]


missing_includes = (
    configuration_tree.get(
        "missing_include_count",
        0,
    )
)

orphan_yaml = (
    configuration_tree.get(
        "orphan_candidate_count",
        0,
    )
)

missing_entities = (
    entity_references.get(
        "missing_count",
        0,
    )
)


duplicate_automation_ids = (
    count_mapping(
        automations.get(
            "duplicate_ids"
        )
    )
)

duplicate_automation_names = (
    count_mapping(
        automations.get(
            "duplicate_aliases"
        )
    )
)

duplicate_script_names = (
    count_mapping(
        scripts.get(
            "duplicate_aliases"
        )
    )
)


unavailable = (
    entities.get(
        "unavailable",
        {},
    ).get(
        "count",
        0,
    )
)

unknown = (
    entities.get(
        "unknown",
        {},
    ).get(
        "count",
        0,
    )
)

not_provided = (
    entities.get(
        "not_currently_provided",
        {},
    ).get(
        "count",
        0,
    )
)


referenced_not_provided = (
    reference_summary.get(
        "referenced_in_active_yaml",
        0,
    )
)

template_cleanup = (
    reference_summary.get(
        "template_no_active_yaml_reference",
        0,
    )
)


lines = []


def add(text=""):
    lines.append(
        text
    )


add(
    "=" * 58
)

add(
    f"HA AUDIT v{VERSION} - "
    f"CURRENT RUN SUMMARY"
)

add(
    f"Generated: "
    f"{format_generated_time(audit)}"
)

add(
    "=" * 58
)


add("")
add("SYSTEM")
add("-" * 58)

add(
    f"Core:                       "
    f"{system.get('core_version')}"
)

add(
    f"Supervisor:                 "
    f"{system.get('supervisor_version')}"
)

add(
    f"OS:                         "
    f"{system.get('os_version')}"
)

add(
    f"Config check:               "
    f"{str(config_result).upper()}"
)

add(
    f"Updates available:          "
    f"{updates.get('available_count', 0)}"
)

add(
    f"Collector errors:           "
    f"{len(collector_errors)}"
)


add("")
add("CONFIGURATION")
add("-" * 58)

add(
    f"Active YAML files:          "
    f"{configuration_tree.get('active_yaml_count', 0)}"
)

add(
    f"Missing active includes:    "
    f"{missing_includes}"
)

add(
    f"Missing entity candidates:  "
    f"{missing_entities}"
)

add(
    f"Orphan YAML candidates:     "
    f"{orphan_yaml}"
)

add(
    f"Duplicate automation IDs:   "
    f"{duplicate_automation_ids}"
)

add(
    f"Duplicate automation names: "
    f"{duplicate_automation_names}"
)

add(
    f"Duplicate script names:     "
    f"{duplicate_script_names}"
)


add("")
add("ENTITY HEALTH")
add("-" * 58)

add(
    f"Entities:                   "
    f"{inventory.get('state_entities', 0)}"
)

add(
    f"Unavailable:                "
    f"{unavailable}"
)

add(
    f"Unknown:                    "
    f"{unknown}"
)

add(
    f"Not currently provided:     "
    f"{not_provided}"
)

add(
    f"New unavailable:            "
    f"{changes.get('new_unavailable_count', 0)}"
)

add(
    f"Recovered unavailable:      "
    f"{changes.get('resolved_unavailable_count', 0)}"
)


add("")
add("REVIEW")
add("-" * 58)

add(
    f"Not provided + active YAML: "
    f"{referenced_not_provided}"
)

add(
    f"Template cleanup candidates:"
    f" {template_cleanup}"
)


add("")
add("NEXT ACTIONS")
add("-" * 58)


actions = 0


if str(
    config_result
).lower() != "valid":

    actions += 1

    add(
        "[!] Configuration check "
        "is not valid."
    )

    add(
        "    Review the detailed "
        "audit report before "
        "restarting Home Assistant."
    )


if collector_errors:

    actions += 1

    add(
        "[!] One or more audit "
        "collectors failed: "
        + ", ".join(
            collector_errors
        )
    )

    add(
        "    Review the HA Audit "
        "app log for the collector "
        "failure."
    )


if missing_includes:

    actions += 1

    add(
        f"[!] {missing_includes} "
        "active YAML include "
        "target(s) are missing."
    )

    add(
        "    Check "
        "quality_audit.json > "
        "configuration_tree > "
        "missing_includes."
    )

    add(
        "    Then open the listed "
        "source file and line in "
        "Studio Code Server."
    )


if missing_entities:

    actions += 1

    add(
        f"[!] {missing_entities} "
        "active YAML entity "
        "reference candidate(s) "
        "need review."
    )

    add(
        "    Check "
        "quality_audit.json > "
        "entity_references > "
        "missing_candidates."
    )

    add(
        "    Use the listed file "
        "and line number in "
        "Studio Code Server."
    )


if referenced_not_provided:

    actions += 1

    add(
        f"[!] "
        f"{referenced_not_provided} "
        "entity/entities are not "
        "currently provided but "
        "are still referenced in "
        "active YAML."
    )

    add(
        "    Check "
        "not_provided_reference_"
        "audit.json > "
        "referenced_entities."
    )

    add(
        "    Review the listed "
        "YAML file and line before "
        "removing or renaming "
        "anything."
    )


if template_cleanup:

    actions += 1

    add(
        f"[i] {template_cleanup} "
        "Template entity/entities "
        "are cleanup candidates."
    )

    add(
        "    In Home Assistant go "
        "to Settings > "
        "Devices & services > "
        "Entities."
    )

    add(
        "    Filter "
        "Status = Unavailable "
        "and "
        "Integration = Template."
    )

    add(
        "    Open an entity and "
        "confirm Home Assistant "
        "says it is no longer "
        "provided before deleting "
        "it."
    )


if orphan_yaml:

    actions += 1

    add(
        f"[i] {orphan_yaml} YAML "
        "file(s) are not in the "
        "active include tree."
    )

    add(
        "    Check "
        "quality_audit.json > "
        "configuration_tree > "
        "inactive_classification "
        "> orphan_candidate."
    )


if actions == 0:

    add(
        "No immediate "
        "configuration cleanup "
        "actions were identified "
        "by this audit."
    )


add("")
add("DETAILED REPORTS")
add("-" * 58)

add(
    "Stored in HA Audit's "
    "app-config folder."
)

add("")

add(
    "To open them in "
    "Studio Code Server:"
)

add(
    "  File > Open Folder..."
)

add(
    "  Enter: /addon_configs"
)

add(
    "  Open the folder whose "
    "name ends in _ha_audit"
)

add("")

add("Files:")

add(
    "  audit_snapshot.json"
)

add(
    "  audit_snapshot_previous.json"
)

add(
    "  config_inventory.json"
)

add(
    "  quality_audit.json"
)

add(
    "  not_provided_reference_audit.json"
)

add(
    "  ha_audit_latest.txt"
)

add("")

add(
    "ha_audit_latest.txt is "
    "overwritten on every run."
)

add("")

add(
    "To return to what you "
    "were previously working on:"
)

add(
    "  Use File > Open Recent "
    "and reopen your previous "
    "folder/workspace."
)

add(
    "  If it is not listed, use "
    "File > Open Folder... and "
    "select the folder you were "
    "using before."
)

add(
    "=" * 58
)


summary = (
    "\n".join(
        lines
    )
    + "\n"
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:

    handle.write(
        summary
    )


print(
    summary,
    end="",
)
