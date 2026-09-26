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
RECORDER_FILE = "/config/recorder_health_audit.json"
HISTORY_FILE = "/config/not_provided_history_audit.json"
AVAILABILITY_FILE = "/config/availability_audit.json"

OUTPUT_FILE = "/config/ha_audit_latest.txt"


def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def load_json_optional(path):
    try:
        return load_json(
            path
        )
    except Exception:
        return {}


def count_mapping(value):
    if isinstance(
        value,
        dict,
    ):
        return len(
            value
        )

    return 0


def parse_iso(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(
                value
            ).replace(
                "Z",
                "+00:00",
            )
        )

    except Exception:
        return None


def format_local_time(
    value,
    timezone_name,
    include_seconds=False,
):
    stamp = parse_iso(
        value
    )

    if not stamp:
        if value:
            return str(
                value
            )

        return "unknown"

    try:
        local_stamp = stamp.astimezone(
            ZoneInfo(
                timezone_name
            )
        )

    except Exception:
        local_stamp = stamp

    pattern = (
        "%d %b %Y %H:%M:%S"
        if include_seconds
        else "%d %b %Y %H:%M"
    )

    return local_stamp.strftime(
        pattern
    )


def format_generated_time(audit):
    timezone_name = (
        audit.get(
            "system",
            {},
        ).get(
            "timezone"
        )
        or "UTC"
    )

    generated_at = audit.get(
        "generated_at"
    )

    if not generated_at:
        return "unknown"

    formatted = format_local_time(
        generated_at,
        timezone_name,
        include_seconds=True,
    )

    return (
        f"{formatted} "
        f"({timezone_name})"
    )


def format_days(value):
    if value is None:
        return "unknown"

    try:
        number = float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return str(
            value
        )

    if number < 10:
        return (
            f"{number:.1f} days"
        )

    return (
        f"{number:.0f} days"
    )


# ------------------------------------------------------------
# Load reports
# ------------------------------------------------------------

audit = load_json(
    AUDIT_FILE
)

quality = load_json(
    QUALITY_FILE
)

reference = load_json(
    REFERENCE_FILE
)

recorder = load_json_optional(
    RECORDER_FILE
)

history = load_json_optional(
    HISTORY_FILE
)

availability = load_json_optional(
    AVAILABILITY_FILE
)


# ------------------------------------------------------------
# Main audit data
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Quality report data
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Reference report data
# ------------------------------------------------------------

reference_summary = reference.get(
    "summary",
    {},
)


# ------------------------------------------------------------
# History report data
# ------------------------------------------------------------

history_summary = history.get(
    "summary",
    {},
)

history_policy = history.get(
    "history_policy",
    {},
)

recent_history_entities = history.get(
    "recent_activity_entities",
    [],
)


# ------------------------------------------------------------
# Recorder report data
# ------------------------------------------------------------

recorder_status = recorder.get(
    "status"
)

recorder_info = recorder.get(
    "recorder",
    {},
)

recorder_availability = recorder.get(
    "history_availability",
    {},
)


# ------------------------------------------------------------
# Availability classification data
# ------------------------------------------------------------

availability_summary = availability.get(
    "summary",
    {},
)

availability_labels = availability.get(
    "labels",
    {},
)

availability_entity_counts = (
    availability_summary.get(
        "entity_classification_counts",
        {},
    )
)

availability_device_counts = (
    availability_summary.get(
        "device_classification_counts",
        {},
    )
)


availability_available = bool(
    availability
)


expected_label = (
    availability_labels.get(
        "expected_offline",
        {},
    )
)

maintenance_label = (
    availability_labels.get(
        "maintenance",
        {},
    )
)


expected_label_name = (
    expected_label.get(
        "name"
    )
    or "HA Audit - Expected Offline"
)

maintenance_label_name = (
    maintenance_label.get(
        "name"
    )
    or "HA Audit - Maintenance"
)


expected_label_exists = bool(
    expected_label.get(
        "exists",
        False,
    )
)

maintenance_label_exists = bool(
    maintenance_label.get(
        "exists",
        False,
    )
)


availability_classified = (
    availability_summary.get(
        "unavailable_entities_classified",
        0,
    )
)

availability_excluded = (
    availability_summary.get(
        "excluded_not_currently_provided",
        0,
    )
)


expected_offline_entities = (
    availability_entity_counts.get(
        "expected_offline",
        0,
    )
)

maintenance_entities = (
    availability_entity_counts.get(
        "maintenance",
        0,
    )
)

partial_entities = (
    availability_entity_counts.get(
        "partial_availability",
        0,
    )
)

whole_device_entities = (
    availability_entity_counts.get(
        "whole_device_unavailable_unlabelled",
        0,
    )
)

ungrouped_entities = (
    availability_entity_counts.get(
        "ungrouped_unavailable",
        0,
    )
)


expected_offline_devices = (
    availability_device_counts.get(
        "expected_offline",
        0,
    )
)

maintenance_devices = (
    availability_device_counts.get(
        "maintenance",
        0,
    )
)

partial_devices = (
    availability_device_counts.get(
        "partial_availability",
        0,
    )
)

whole_device_devices = (
    availability_device_counts.get(
        "whole_device_unavailable_unlabelled",
        0,
    )
)

ungrouped_devices = (
    availability_device_counts.get(
        "ungrouped_unavailable",
        0,
    )
)


# ------------------------------------------------------------
# General values
# ------------------------------------------------------------

timezone_name = (
    system.get(
        "timezone"
    )
    or "UTC"
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

template_review = (
    reference_summary.get(
        "template_no_active_yaml_reference",
        0,
    )
)


history_available = bool(
    history
)


requested_lookback_days = (
    history_policy.get(
        "requested_lookback_days",
        recorder.get(
            "requested_history_lookback_days",
            90,
        ),
    )
)

effective_lookback_days = (
    history_policy.get(
        "effective_lookback_days",
        recorder_availability.get(
            "effective_lookback_days"
        ),
    )
)

recent_activity_days = (
    history_policy.get(
        "recent_activity_days",
        45,
    )
)

history_window_source = (
    history_policy.get(
        "history_window_source"
    )
)


recorder_oldest_run = (
    history_policy.get(
        "recorder_oldest_run"
    )
    or recorder_info.get(
        "oldest_recorder_run"
    )
)

available_history_days = (
    recorder_availability.get(
        "available_history_days"
    )
)


history_recent = (
    history_summary.get(
        "recent_activity",
        0,
    )
)

history_older = (
    history_summary.get(
        "older_activity",
        0,
    )
)

history_none = (
    history_summary.get(
        "no_usable_history_found",
        0,
    )
)

history_failed = (
    history_summary.get(
        "history_query_failed",
        0,
    )
)


# ------------------------------------------------------------
# Build summary
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# System
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Entity health
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Availability context
# ------------------------------------------------------------

add("")
add("AVAILABILITY CONTEXT")
add("-" * 58)

if availability_available:

    add(
        f"Unavailable classified:     "
        f"{availability_classified}"
    )

    add(
        f"Not-provided excluded:      "
        f"{availability_excluded}"
    )

    add("")

    add(
        f"Expected offline:           "
        f"{expected_offline_entities} entities / "
        f"{expected_offline_devices} devices"
    )

    add(
        f"Maintenance:                "
        f"{maintenance_entities} entities / "
        f"{maintenance_devices} devices"
    )

    add(
        f"Partial availability:       "
        f"{partial_entities} entities / "
        f"{partial_devices} devices"
    )

    add(
        f"Whole device unavailable:   "
        f"{whole_device_entities} entities / "
        f"{whole_device_devices} devices"
    )

    add(
        f"Ungrouped unavailable:      "
        f"{ungrouped_entities} entities / "
        f"{ungrouped_devices} items"
    )

    add("")

    add(
        f"Expected-offline label:     "
        f"{'FOUND' if expected_label_exists else 'NOT FOUND'}"
    )

    add(
        f"Maintenance label:          "
        f"{'FOUND' if maintenance_label_exists else 'NOT FOUND'}"
    )

    add("")

    add(
        "Unavailable does not automatically "
        "mean faulty."
    )

else:

    add(
        "Availability classification "
        "report unavailable."
    )


# ------------------------------------------------------------
# Review
# ------------------------------------------------------------

add("")
add("REVIEW")
add("-" * 58)

add(
    f"Not provided + active YAML: "
    f"{referenced_not_provided}"
)

add(
    f"Template review candidates: "
    f"{template_review}"
)


# ------------------------------------------------------------
# History safety
# ------------------------------------------------------------

add("")
add("HISTORY SAFETY")
add("-" * 58)

if history_available:

    add(
        f"Requested lookback:          "
        f"{requested_lookback_days} days"
    )

    if (
        recorder_status == "ok"
        and recorder_oldest_run
    ):

        add(
            "Recorder history starts:     "
            + format_local_time(
                recorder_oldest_run,
                timezone_name,
            )
        )

        add(
            "Recorder history available:  "
            + format_days(
                available_history_days
            )
        )

    else:

        add(
            "Recorder history available:  "
            "unknown"
        )

    add(
        "Effective history checked:   "
        + format_days(
            effective_lookback_days
        )
    )

    add(
        f"Recent activity "
        f"(<= {recent_activity_days}d): "
        f"{history_recent}"
    )

    add(
        f"Older activity found:        "
        f"{history_older}"
    )

    add(
        f"No usable history found:     "
        f"{history_none}"
    )

    add(
        f"History query failures:      "
        f"{history_failed}"
    )

    add("")

    add(
        "History is protective "
        "context only."
    )

    add(
        "No history does NOT mean "
        "an entity is safe to delete."
    )

    if (
        history_window_source
        == "requested_lookback_fallback"
    ):

        add(
            "Recorder availability "
            "could not be confirmed "
            "for this run."
        )

else:

    add(
        "History report unavailable."
    )

    add(
        "Do not use absence of "
        "history as cleanup evidence."
    )


# ------------------------------------------------------------
# Next actions
# ------------------------------------------------------------

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


if availability_available:

    if (
        not expected_label_exists
        or not maintenance_label_exists
    ):

        actions += 1

        add(
            "[i] HA Audit availability "
            "labels are not fully configured."
        )

        add(
            "    In Home Assistant go to "
            "Settings > Areas, labels & zones "
            "> Labels."
        )

        if not expected_label_exists:

            add(
                "    Create label: "
                f"{expected_label_name}"
            )

        if not maintenance_label_exists:

            add(
                "    Create label: "
                f"{maintenance_label_name}"
            )

        add(
            "    Apply labels only to devices "
            "whose normal behaviour you know."
        )


    if whole_device_devices:

        actions += 1

        add(
            f"[i] {whole_device_devices} "
            "unlabelled device(s) currently "
            "have no healthy state entities."
        )

        add(
            "    This does NOT automatically "
            "mean they are faulty."
        )

        add(
            "    Review "
            "availability_audit.json > devices."
        )

        add(
            "    If deliberately power-managed, "
            f"apply '{expected_label_name}'."
        )

        add(
            "    If temporarily offline for work "
            "or repairs, apply "
            f"'{maintenance_label_name}'."
        )


    if partial_devices:

        actions += 1

        add(
            f"[i] {partial_devices} device(s) "
            "have partial availability."
        )

        add(
            "    At least one entity is healthy "
            "while other entities are unavailable."
        )

        add(
            "    Treat these as feature-level "
            "review items rather than whole-device "
            "failures."
        )


    if ungrouped_entities:

        actions += 1

        add(
            f"[i] {ungrouped_entities} "
            "unavailable entity/entities are "
            "not attached to a device."
        )

        add(
            "    Review "
            "availability_audit.json > entities."
        )

else:

    actions += 1

    add(
        "[!] Availability classification "
        "was not available for this run."
    )

    add(
        "    Check the HA Audit log for an "
        "availability scanner failure."
    )


if (
    recorder_status
    not in (
        None,
        "ok",
    )
):

    actions += 1

    add(
        "[!] Recorder history "
        "availability could not "
        "be determined."
    )

    add(
        "    Do not treat absence "
        "of entity history as "
        "cleanup evidence."
    )


if history_failed:

    actions += 1

    add(
        f"[!] History could not be "
        f"checked for "
        f"{history_failed} "
        "entity/entities."
    )


if history_recent:

    actions += 1

    add(
        f"[i] {history_recent} "
        "not-currently-provided "
        "entity/entities had usable "
        f"activity within the last "
        f"{recent_activity_days} days."
    )

    add(
        "    Treat these as KEEP / "
        "REVIEW rather than cleanup "
        "candidates."
    )

    if len(
        recent_history_entities
    ) <= 10:

        for item in recent_history_entities:

            entity_id = item.get(
                "entity_id",
                "unknown",
            )

            last_at = format_local_time(
                item.get(
                    "last_usable_state_at"
                ),
                timezone_name,
            )

            add(
                f"    - {entity_id} "
                f"(last usable: "
                f"{last_at})"
            )

    else:

        add(
            "    See "
            "not_provided_history_"
            "audit.json > "
            "recent_activity_entities "
            "for the full list."
        )


if history_older:

    actions += 1

    add(
        f"[i] {history_older} "
        "not-currently-provided "
        "entity/entities have older "
        "usable history."
    )

    add(
        "    Review before deleting."
    )


if history_none:

    actions += 1

    add(
        f"[i] {history_none} "
        "not-currently-provided "
        "entity/entities have no "
        "usable history in the "
        "effective Recorder window."
    )

    add(
        "    This is UNKNOWN, not "
        "approval to delete."
    )


if template_review:

    actions += 1

    add(
        f"[i] {template_review} "
        "Template entity/entities "
        "are review candidates."
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


if orphan_yaml:

    actions += 1

    add(
        f"[i] {orphan_yaml} YAML "
        "file(s) are not in the "
        "active include tree."
    )


if actions == 0:

    add(
        "No immediate "
        "configuration or availability "
        "actions were identified "
        "by this audit."
    )


# ------------------------------------------------------------
# Detailed reports
# ------------------------------------------------------------

add("")
add("DETAILED REPORTS")
add("-" * 58)

add(
    "Stored in HA Audit's "
    "app-config folder."
)

add("")

add(
    "If your Home Assistant "
    "file-access tool can browse "
    "/addon_configs:"
)

add(
    "  Open /addon_configs"
)

add(
    "  Then open the folder whose "
    "name ends in _ha_audit"
)

add("")

add(
    "Studio Code Server example:"
)

add(
    "  File > Open Folder..."
)

add(
    "  Enter: /addon_configs"
)

add(
    "  Open the folder ending "
    "in _ha_audit"
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
    "  recorder_health_audit.json"
)

add(
    "  not_provided_history_audit.json"
)

add(
    "  availability_audit.json"
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
    "  Reopen your previous "
    "folder/workspace using your "
    "file-access tool."
)

add(
    "  In Studio Code Server, "
    "File > Open Recent is usually "
    "the quickest option."
)

add(
    "  Otherwise use "
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
