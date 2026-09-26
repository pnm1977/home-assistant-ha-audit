import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo


VERSION = os.environ.get("HA_AUDIT_VERSION", "unknown")

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"
REFERENCE_FILE = "/config/not_provided_reference_audit.json"
RECORDER_FILE = "/config/recorder_health_audit.json"
HISTORY_FILE = "/config/not_provided_history_audit.json"

OUTPUT_FILE = "/config/ha_audit_latest.txt"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_json_optional(path):
    try:
        return load_json(path)
    except Exception:
        return {}


def count_mapping(value):
    return len(value) if isinstance(value, dict) else 0


def parse_iso(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
    except Exception:
        return None


def format_local_time(
    value,
    timezone_name,
    include_seconds=False,
):
    stamp = parse_iso(value)

    if not stamp:
        return "unknown" if not value else str(value)

    try:
        local_stamp = stamp.astimezone(
            ZoneInfo(timezone_name)
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
    f"Template review candidates: "
    f"{template_review}"
)


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
        "your Home Assistant "
        "configuration editor."
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
        "and line number in your "
        "Home Assistant "
        "configuration editor."
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
        "    Review the listed YAML "
        "file and line before "
        "removing or renaming "
        "anything."
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

    add(
        "    Check "
        "recorder_health_audit.json "
        "for details."
    )


if history_failed:

    actions += 1

    add(
        f"[!] History could not be "
        f"checked for "
        f"{history_failed} "
        "entity/entities."
    )

    add(
        "    Do not use history as "
        "cleanup evidence for "
        "those entities."
    )

    add(
        "    Check "
        "not_provided_history_"
        "audit.json."
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
        "usable history within the "
        "available Recorder window."
    )

    add(
        "    Review before deleting; "
        "older activity is still "
        "evidence that the entity "
        "was used."
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

    add(
        "    Recorder retention, "
        "exclusions, or "
        "entity-specific gaps may "
        "limit evidence."
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

    add(
        "    Open an entity and "
        "confirm Home Assistant "
        "says it is no longer "
        "provided."
    )

    add(
        "    Check history context "
        "before deleting anything."
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
        "inactive_classification > "
        "orphan_candidate."
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
