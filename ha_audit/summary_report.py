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
UNAVAILABLE_HISTORY_FILE = "/config/unavailable_history_audit.json"
UPDATE_READINESS_FILE = "/config/update_readiness_audit.json"

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


def format_update_category(category):
    labels = {
        "core": "Core",
        "os": "OS",
        "supervisor": "Supervisor",
        "app": "App",
        "hacs": "HACS",
        "firmware": "Firmware",
        "other": "Other",
    }

    return labels.get(
        str(
            category
            or "other"
        ).lower(),
        str(
            category
            or "Other"
        ),
    )


def format_update_name(item):
    return (
        item.get(
            "title"
        )
        or item.get(
            "name"
        )
        or item.get(
            "entity_id"
        )
        or "Unknown update"
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

unavailable_history = load_json_optional(
    UNAVAILABLE_HISTORY_FILE
)

update_readiness = load_json_optional(
    UPDATE_READINESS_FILE
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
# Unavailable history context data
# ------------------------------------------------------------

unavailable_history_available = bool(
    unavailable_history
)

unavailable_history_summary = unavailable_history.get(
    "summary",
    {},
)

unavailable_history_policy = unavailable_history.get(
    "history_policy",
    {},
)

unavailable_history_diagnostics = unavailable_history.get(
    "query_diagnostics",
    {},
)

unavailable_history_checked = (
    unavailable_history_summary.get(
        "currently_unavailable_checked",
        0,
    )
)

unavailable_history_usable = (
    unavailable_history_summary.get(
        "usable_history_found",
        0,
    )
)

unavailable_history_no_usable = (
    unavailable_history_summary.get(
        "history_found_no_usable_state",
        0,
    )
)

unavailable_history_none = (
    unavailable_history_summary.get(
        "no_history_returned",
        0,
    )
)

unavailable_history_failed = (
    unavailable_history_summary.get(
        "history_query_failed",
        0,
    )
)

unavailable_history_effective_days = (
    unavailable_history_policy.get(
        "effective_lookback_days"
    )
)

unavailable_history_observed_at = (
    unavailable_history.get(
        "source_availability_observed_at"
    )
)

unavailable_history_batch_failures = (
    unavailable_history_diagnostics.get(
        "batch_query_failures",
        0,
    )
)

unavailable_history_retry_failures = (
    unavailable_history_diagnostics.get(
        "individual_retry_failures",
        0,
    )
)


# ------------------------------------------------------------
# Update readiness data
# ------------------------------------------------------------

update_readiness_available = bool(
    update_readiness
)

readiness_scope = update_readiness.get(
    "scope",
    {},
)

readiness_updates = update_readiness.get(
    "updates",
    {},
)

readiness_repairs = update_readiness.get(
    "repairs",
    {},
)

core_upgrade_window = update_readiness.get(
    "core_upgrade_window",
    {},
)

readiness_available_updates = readiness_updates.get(
    "available",
    [],
)

if not isinstance(
    readiness_available_updates,
    list,
):
    readiness_available_updates = []

readiness_pending_count = readiness_updates.get(
    "available_count",
    0,
)

readiness_unavailable_count = readiness_updates.get(
    "unavailable_count",
    0,
)

readiness_in_progress_count = readiness_updates.get(
    "in_progress_count",
    0,
)

readiness_issue_count = readiness_repairs.get(
    "issue_count",
    0,
)

readiness_unignored_count = readiness_repairs.get(
    "unignored_count",
    0,
)

readiness_ignored_count = readiness_repairs.get(
    "ignored_count",
    0,
)

readiness_relevant_count = readiness_repairs.get(
    "relevant_to_pending_upgrade_count",
    0,
)

readiness_relevant_unignored_count = readiness_repairs.get(
    "relevant_unignored_count",
    0,
)

readiness_relevant_ignored_count = readiness_repairs.get(
    "relevant_ignored_count",
    0,
)

readiness_already_crossed_count = readiness_repairs.get(
    "already_crossed_count",
    0,
)

readiness_beyond_target_count = readiness_repairs.get(
    "beyond_pending_target_count",
    0,
)

readiness_compatibility_assessed = bool(
    readiness_scope.get(
        "compatibility_assessed",
        False,
    )
)

readiness_external_release_notes = bool(
    readiness_scope.get(
        "external_release_notes_fetched",
        False,
    )
)

readiness_verdict_produced = bool(
    readiness_scope.get(
        "readiness_verdict_produced",
        False,
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

active_duplicate_automation_names = (
    count_mapping(
        automations.get(
            "active_duplicate_aliases"
        )
    )
)

unresolved_duplicate_automation_names = (
    count_mapping(
        automations.get(
            "unresolved_duplicate_aliases"
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

history_recent_end_unknown = (
    history_summary.get(
        "recent_activity_end_unknown",
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
# Update readiness
# ------------------------------------------------------------

add("")
add("UPDATE READINESS")
add("-" * 58)

if update_readiness_available:

    add(
        f"Pending updates:             "
        f"{readiness_pending_count}"
    )

    if readiness_available_updates:
        add("")

        for item in readiness_available_updates:
            category = format_update_category(
                item.get(
                    "category"
                )
            )

            name = format_update_name(
                item
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

            if category in (
                "Core",
                "OS",
                "Supervisor",
            ):
                add(
                    f"{category}: "
                    f"{installed} -> {latest}"
                )
            else:
                add(
                    f"{category}: "
                    f"{name} "
                    f"{installed} -> {latest}"
                )

    if core_upgrade_window.get(
        "pending"
    ):
        add("")
        add(
            "Core upgrade window:         "
            f"{core_upgrade_window.get('installed_version')}"
            " -> "
            f"{core_upgrade_window.get('target_version')}"
        )

    add("")
    add(
        f"Repair issues:               "
        f"{readiness_issue_count}"
    )

    add(
        f"Unignored Repairs:           "
        f"{readiness_unignored_count}"
    )

    add(
        f"Ignored Repairs:             "
        f"{readiness_ignored_count}"
    )

    add(
        f"Relevant to Core upgrade:    "
        f"{readiness_relevant_count}"
    )

    add(
        f"Relevant + unignored:        "
        f"{readiness_relevant_unignored_count}"
    )

    add(
        f"Relevant + ignored:          "
        f"{readiness_relevant_ignored_count}"
    )

    add(
        f"Already-crossed Repairs:     "
        f"{readiness_already_crossed_count}"
    )

    if readiness_beyond_target_count:
        add(
            f"Beyond pending target:       "
            f"{readiness_beyond_target_count}"
        )

    if readiness_unavailable_count:
        add(
            f"Unavailable update entities: "
            f"{readiness_unavailable_count}"
        )

    if readiness_in_progress_count:
        add(
            f"Updates in progress:         "
            f"{readiness_in_progress_count}"
        )

    add("")

    add(
        "Compatibility research:      "
        + (
            "ASSESSED"
            if readiness_compatibility_assessed
            else "NOT YET ASSESSED"
        )
    )

    add(
        "External release notes:      "
        + (
            "FETCHED"
            if readiness_external_release_notes
            else "NOT YET FETCHED"
        )
    )

    add(
        "Readiness verdict:           "
        + (
            "PRODUCED"
            if readiness_verdict_produced
            else "NOT PRODUCED"
        )
    )

    add("")

    add(
        "This section is local evidence only unless "
        "compatibility research is explicitly shown as assessed."
    )

else:

    add(
        "Update readiness report unavailable."
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
    f"Active duplicate auto names: "
    f"{active_duplicate_automation_names}"
)

add(
    f"Unresolved duplicate names:  "
    f"{unresolved_duplicate_automation_names}"
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
        "Availability classifications are "
        "observational context, not fault verdicts."
    )

    add(
        "Expected-offline and maintenance labels "
        "are optional context when users choose to use them."
    )

else:

    add(
        "Availability classification "
        "report unavailable."
    )


# ------------------------------------------------------------
# Unavailable history context
# ------------------------------------------------------------

add("")
add("UNAVAILABLE HISTORY CONTEXT")
add("-" * 58)

if unavailable_history_available:

    add(
        f"Unavailable entities checked: "
        f"{unavailable_history_checked}"
    )

    if unavailable_history_observed_at:
        add(
            "Availability snapshot:       "
            + format_local_time(
                unavailable_history_observed_at,
                timezone_name,
            )
        )

    add(
        "Effective history checked:   "
        + format_days(
            unavailable_history_effective_days
        )
    )

    add(
        f"Usable history found:        "
        f"{unavailable_history_usable}"
    )

    add(
        f"History, no usable state:    "
        f"{unavailable_history_no_usable}"
    )

    add(
        f"No history returned:         "
        f"{unavailable_history_none}"
    )

    add(
        f"History query failures:      "
        f"{unavailable_history_failed}"
    )

    if unavailable_history_batch_failures:

        add(
            f"Batch queries retried:       "
            f"{unavailable_history_batch_failures}"
        )

        add(
            f"Individual retry failures:   "
            f"{unavailable_history_retry_failures}"
        )

    add("")

    add(
        "Recorder history is observational "
        "context only."
    )

    add(
        "Old, recent, or absent usable history "
        "does not by itself indicate a fault "
        "or required action."
    )

else:

    add(
        "Unavailable history context "
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
add("NOT-PROVIDED HISTORY SAFETY")
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
        f"Recent/protective activity:  "
        f"{history_recent}"
    )

    add(
        f"Recent window:               "
        f"{recent_activity_days} days"
    )

    if history_recent_end_unknown:

        add(
            f"Usable interval end unknown: "
            f"{history_recent_end_unknown}"
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
        "A usable interval with no recorded end "
        "is kept protective rather than assumed old."
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


if duplicate_automation_ids:

    actions += 1

    add(
        f"[!] {duplicate_automation_ids} duplicate "
        "automation ID group(s) need review."
    )

    add(
        "    Automation IDs should be unique. "
        "Check quality_audit.json > automations > "
        "duplicate_id_details."
    )


if active_duplicate_automation_names:

    actions += 1

    add(
        f"[i] {active_duplicate_automation_names} "
        "automation alias group(s) are shared by "
        "two or more currently-on automations."
    )

    add(
        "    This is a maintainability finding, not "
        "an automation ID collision."
    )

    add(
        "    Check quality_audit.json > automations > "
        "active_duplicate_aliases."
    )


if unresolved_duplicate_automation_names:

    actions += 1

    add(
        f"[i] {unresolved_duplicate_automation_names} "
        "duplicate automation alias group(s) could "
        "not be fully classified from live state."
    )

    add(
        "    Check quality_audit.json > automations > "
        "unresolved_duplicate_aliases."
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


if update_readiness_available:

    if readiness_relevant_unignored_count:

        actions += 1

        add(
            f"[!] {readiness_relevant_unignored_count} "
            "unignored Repair issue(s) are relevant "
            "to the pending Core upgrade window."
        )

        add(
            "    Review update_readiness_audit.json > "
            "repairs > relevant_unignored before "
            "installing the Core update."
        )

    if (
        readiness_pending_count
        and not readiness_compatibility_assessed
    ):

        actions += 1

        add(
            f"[i] {readiness_pending_count} update(s) "
            "are pending."
        )

        add(
            "    Local update and Repair evidence has "
            "been collected, but external release-note "
            "and compatibility analysis is not yet assessed."
        )

        add(
            "    Do not interpret this local-only result "
            "as a safe-to-update verdict."
        )

else:

    if updates.get(
        "available_count",
        0,
    ):

        actions += 1

        add(
            "[!] Update readiness context was not "
            "available for pending updates."
        )

        add(
            "    Check the HA Audit log for an "
            "update readiness scanner failure."
        )


if availability_available:

    if whole_device_devices:

        actions += 1

        add(
            f"[i] {whole_device_devices} "
            "device(s) currently have no "
            "healthy state entities."
        )

        add(
            "    This is observational and may "
            "be intentional or temporary."
        )

        add(
            "    Review availability_audit.json "
            "and unavailable_history_audit.json "
            "if more context is needed."
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
            "    Treat this as feature-level "
            "availability context rather than a "
            "whole-device fault verdict."
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
            "availability_audit.json > entities "
            "if context is needed."
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


if availability_available:

    if not unavailable_history_available:

        actions += 1

        add(
            "[!] Unavailable entity history "
            "context was not available for this run."
        )

        add(
            "    Check the HA Audit log for an "
            "unavailable history scanner failure."
        )

    elif unavailable_history_failed:

        actions += 1

        add(
            f"[!] Recorder history could not be "
            f"checked for {unavailable_history_failed} "
            "currently unavailable entity/entities."
        )

        add(
            "    Review unavailable_history_audit.json > "
            "entities for the failed checks."
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
        "    History evidence may be incomplete; "
        "treat absent history as unknown context."
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
        "entity/entities have recent "
        "or conservatively protective "
        "usable history."
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

            ended_at = item.get(
                "last_usable_state_ended_at"
            )

            started_at = (
                item.get(
                    "last_usable_state_started_at"
                )
                or item.get(
                    "last_usable_state_at"
                )
            )

            if ended_at:

                last_at = format_local_time(
                    ended_at,
                    timezone_name,
                )

                add(
                    f"    - {entity_id} "
                    f"(last usable until: "
                    f"{last_at})"
                )

            else:

                started = format_local_time(
                    started_at,
                    timezone_name,
                )

                add(
                    f"    - {entity_id} "
                    f"(usable state recorded from: "
                    f"{started}; end not recorded)"
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
        "entity/entities have a final "
        "usable interval that Recorder "
        "shows ended before the recent window."
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
        "No immediate configuration, availability, "
        "or update-readiness actions were identified "
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

for report_file in (
    "audit_snapshot.json",
    "audit_snapshot_previous.json",
    "config_inventory.json",
    "quality_audit.json",
    "not_provided_reference_audit.json",
    "recorder_health_audit.json",
    "not_provided_history_audit.json",
    "availability_audit.json",
    "unavailable_history_audit.json",
    "update_readiness_audit.json",
    "ha_audit_latest.txt",
):

    add(
        f"  {report_file}"
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
