import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from readiness_guidance import (
    STATE_BLOCKER,
    STATE_CLEAR,
    STATE_INCOMPLETE,
    STATE_NO_UPDATE,
    STATE_REVIEW,
    evaluate_core_update_guidance,
)
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
UPGRADE_IMPACT_FILE = "/config/upgrade_impact_audit.json"
UPGRADE_COMPATIBILITY_FILE = "/config/upgrade_compatibility_audit.json"
RELEASE_EVIDENCE_FILE = "/config/release_evidence_audit.json"
COMPATIBILITY_COVERAGE_FILE = "/config/compatibility_coverage_audit.json"
UPGRADE_CORRELATION_FILE = "/config/upgrade_correlation_audit.json"
CORRELATION_VALIDATION_FILE = "/config/correlation_validation_audit.json"
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
        return load_json(path)
    except Exception:
        return {}

def count_mapping(value):
    if isinstance(
        value,
        dict,
    ):
        return len(value)
    return 0

def parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            str(value).replace(
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
    stamp = parse_iso(value)
    if not stamp:
        if value:
            return str(value)
        return "unknown"
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
    return local_stamp.strftime(pattern)

def format_generated_time(audit):
    timezone_name = (
        audit.get(
            "system",
            {},
        ).get("timezone")
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
        number = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return str(value)
    if number < 10:
        return f"{number:.1f} days"
    return f"{number:.0f} days"

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
        item.get("title")
        or item.get("name")
        or item.get("entity_id")
        or "Unknown update"
    )

def format_rule_pack(rule_pack):
    value = str(
        rule_pack
        or "unknown"
    )
    prefix = "home_assistant_core_"
    if value.startswith(prefix):
        return value[
            len(prefix):
        ].replace(
            "_",
            ".",
        )
    return value

def pluralise(
    count,
    singular,
    plural=None,
):
    try:
        value = int(count)
    except (
        TypeError,
        ValueError,
    ):
        value = count
    if plural is None:
        plural = singular + "s"
    return (
        singular
        if value == 1
        else plural
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
upgrade_impact = load_json_optional(
    UPGRADE_IMPACT_FILE
)
upgrade_compatibility = load_json_optional(
    UPGRADE_COMPATIBILITY_FILE
)
release_evidence = load_json_optional(
    RELEASE_EVIDENCE_FILE
)
compatibility_coverage_report = load_json_optional(
    COMPATIBILITY_COVERAGE_FILE
)
upgrade_correlation_report = load_json_optional(
    UPGRADE_CORRELATION_FILE
)
correlation_validation_report = load_json_optional(
    CORRELATION_VALIDATION_FILE
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
readiness_verdict_produced = bool(
    readiness_scope.get(
        "readiness_verdict_produced",
        False,
    )
)

# ------------------------------------------------------------
# Upgrade compatibility data
# ------------------------------------------------------------

upgrade_compatibility_available = bool(
    upgrade_compatibility
)
compatibility_scope = upgrade_compatibility.get(
    "scope",
    {},
)
compatibility_window = upgrade_compatibility.get(
    "core_upgrade_window",
    {},
)
compatibility_scan_coverage = upgrade_compatibility.get(
    "coverage",
    {},
)
compatibility_summary = upgrade_compatibility.get(
    "summary",
    {},
)
if not isinstance(
    compatibility_scope,
    dict,
):
    compatibility_scope = {}
if not isinstance(
    compatibility_window,
    dict,
):
    compatibility_window = {}
if not isinstance(
    compatibility_scan_coverage,
    dict,
):
    compatibility_scan_coverage = {}
if not isinstance(
    compatibility_summary,
    dict,
):
    compatibility_summary = {}
compatibility_status_counts = compatibility_summary.get(
    "status_counts",
    {},
)
if not isinstance(
    compatibility_status_counts,
    dict,
):
    compatibility_status_counts = {}
compatibility_rule_count = compatibility_summary.get(
    "rule_count",
    0,
)
compatibility_review_required_count = compatibility_summary.get(
    "review_required_count",
    0,
)
compatibility_manual_review_count = compatibility_summary.get(
    "manual_review_count",
    0,
)
compatibility_no_local_match_count = compatibility_status_counts.get(
    "no_local_match",
    0,
)
compatibility_no_affected_statuses = (
    "local_match_no_active_yaml_usage_found",
    "local_match_no_affected_custom_usage_found",
    "local_match_no_affected_usage_found",
    "local_match_core_integrations_only",
)
compatibility_no_affected_count = sum(
    compatibility_status_counts.get(
        status,
        0,
    )
    for status
    in compatibility_no_affected_statuses
)
compatibility_other_outcome_count = max(
    0,
    compatibility_rule_count
    - compatibility_no_local_match_count
    - compatibility_no_affected_count
    - compatibility_review_required_count
    - compatibility_manual_review_count,
)
compatibility_rule_pack = compatibility_scope.get(
    "rule_pack"
)
compatibility_rule_pack_label = format_rule_pack(
    compatibility_rule_pack
)
compatibility_assessed = bool(
    upgrade_compatibility_available
    and compatibility_rule_count
)
compatibility_runtime_fetch = bool(
    compatibility_scope.get(
        "external_fetch_performed",
        False,
    )
)
compatibility_verdict_produced = bool(
    compatibility_scope.get(
        "readiness_verdict_produced",
        False,
    )
    or readiness_verdict_produced
)
compatibility_active_yaml_count = compatibility_scan_coverage.get(
    "active_yaml_file_count",
    0,
)
compatibility_yaml_failures = compatibility_scan_coverage.get(
    "active_yaml_read_failures",
    [],
)
if not isinstance(
    compatibility_yaml_failures,
    list,
):
    compatibility_yaml_failures = []
compatibility_ui_prompts_inspected = bool(
    compatibility_scan_coverage.get(
        "ui_managed_prompt_content_inspected",
        False,
    )
)

# ------------------------------------------------------------
# Official release evidence data
# ------------------------------------------------------------

release_evidence_available = bool(
    release_evidence
)
release_scope = release_evidence.get(
    "scope",
    {},
)
release_applicability = release_evidence.get(
    "applicability",
    {},
)
release_range = release_evidence.get(
    "release_range",
    {},
)
release_aggregate = release_evidence.get(
    "aggregate",
    {},
)
release_collector_status = release_evidence.get(
    "collector_status",
    {},
)
release_items = release_evidence.get(
    "releases",
    [],
)
if not isinstance(
    release_scope,
    dict,
):
    release_scope = {}
if not isinstance(
    release_applicability,
    dict,
):
    release_applicability = {}
if not isinstance(
    release_range,
    dict,
):
    release_range = {}
if not isinstance(
    release_aggregate,
    dict,
):
    release_aggregate = {}
if not isinstance(
    release_collector_status,
    dict,
):
    release_collector_status = {}
if not isinstance(
    release_items,
    list,
):
    release_items = []
release_applicable = bool(
    release_applicability.get(
        "applicable",
        False,
    )
)
release_applicability_reason = release_applicability.get(
    "reason"
)
release_external_fetch = bool(
    release_scope.get(
        "external_fetch_performed",
        False,
    )
)
release_official_sources_only = bool(
    release_scope.get(
        "official_sources_only",
        False,
    )
)
release_range_status = release_range.get(
    "status",
    "unknown",
)
release_range_complete = bool(
    release_range.get(
        "complete",
        False,
    )
)
release_same_family = bool(
    release_range.get(
        "same_release_family",
        False,
    )
)
release_requested_families = release_aggregate.get(
    "release_families_requested",
    [],
)
if not isinstance(
    release_requested_families,
    list,
):
    release_requested_families = []
release_crossed_families = release_aggregate.get(
    "crossed_release_families",
    [],
)
if not isinstance(
    release_crossed_families,
    list,
):
    release_crossed_families = []
release_family_count = release_aggregate.get(
    "release_family_count",
    len(
        release_requested_families
    ),
)
release_crossed_count = release_aggregate.get(
    "crossed_release_family_count",
    len(
        release_crossed_families
    ),
)
release_success_count = release_aggregate.get(
    "release_family_success_count",
    0,
)
release_partial_count = release_aggregate.get(
    "release_family_partial_count",
    0,
)
release_failure_count = release_aggregate.get(
    "release_family_failure_count",
    0,
)
release_breaking_group_count = release_aggregate.get(
    "breaking_change_group_count",
    0,
)
release_crossed_group_count = release_aggregate.get(
    "breaking_change_group_count_crossed_only",
    0,
)
release_fetch_success_count = 0
release_structured_parse_count = 0
for release_item in release_items:
    if not isinstance(
        release_item,
        dict,
    ):
        continue
    item_status = release_item.get(
        "collector_status",
        {},
    )
    if not isinstance(
        item_status,
        dict,
    ):
        item_status = {}
    if item_status.get(
        "release_notes_fetch"
    ) == "ok":
        release_fetch_success_count += 1
    item_backward = (
        release_item.get(
            "release_notes",
            {},
        ).get(
            "backward_incompatible_changes",
            {},
        )
    )
    if not isinstance(
        item_backward,
        dict,
    ):
        item_backward = {}
    if item_backward.get(
        "segmentation_status"
    ) == "structured":
        release_structured_parse_count += 1
release_overall_status = str(
    release_collector_status.get(
        "overall",
        "unknown",
    )
)
release_collection_complete = bool(
    release_evidence_available
    and release_applicable
    and release_range_complete
    and release_overall_status == "ok"
    and release_partial_count == 0
    and release_failure_count == 0
    and release_family_count > 0
    and release_fetch_success_count == release_family_count
)
if not release_evidence_available:
    release_status_label = "UNAVAILABLE"
elif release_collection_complete:
    release_status_label = "COMPLETE"
elif (
    not core_upgrade_window.get(
        "pending"
    )
    and release_overall_status == "not_applicable"
):
    release_status_label = "NOT APPLICABLE"
elif release_overall_status == "error":
    release_status_label = "ERROR"
else:
    release_status_label = "PARTIAL"

# ------------------------------------------------------------
# Compatibility coverage mapping data
# ------------------------------------------------------------

coverage_report_available = bool(
    compatibility_coverage_report
)
coverage_inputs = compatibility_coverage_report.get(
    "inputs",
    {},
)
coverage_summary = compatibility_coverage_report.get(
    "summary",
    {},
)
coverage_release_rows = compatibility_coverage_report.get(
    "release_coverage",
    [],
)
coverage_collector_status = compatibility_coverage_report.get(
    "collector_status",
    {},
)
if not isinstance(
    coverage_inputs,
    dict,
):
    coverage_inputs = {}
if not isinstance(
    coverage_summary,
    dict,
):
    coverage_summary = {}
if not isinstance(
    coverage_release_rows,
    list,
):
    coverage_release_rows = []
if not isinstance(
    coverage_collector_status,
    dict,
):
    coverage_collector_status = {}
coverage_status = str(
    coverage_summary.get(
        "coverage_status",
        "unknown",
    )
)
coverage_reference_status = str(
    coverage_summary.get(
        "deterministic_reference_status",
        "unknown",
    )
)
coverage_official_group_count = coverage_summary.get(
    "official_crossed_group_count",
    0,
)
coverage_registry_group_count = coverage_summary.get(
    "registry_group_count",
    0,
)
coverage_covered_group_count = coverage_summary.get(
    "covered_group_count",
    0,
)
coverage_partial_group_count = coverage_summary.get(
    "partial_group_count",
    0,
)
coverage_unmapped_group_count = coverage_summary.get(
    "unmapped_group_count",
    0,
)
coverage_no_reference_group_count = coverage_summary.get(
    "no_reference_group_count",
    0,
)
coverage_incomplete_reference_group_count = coverage_summary.get(
    "incomplete_reference_group_count",
    0,
)
coverage_mapped_rule_count = coverage_summary.get(
    "mapped_rule_count",
    0,
)
coverage_present_linked_rule_count = coverage_summary.get(
    "present_linked_rule_count",
    0,
)
coverage_missing_mapped_rule_count = coverage_summary.get(
    "missing_mapped_rule_count",
    0,
)
coverage_unlinked_rule_count = coverage_summary.get(
    "unlinked_compatibility_rule_count",
    0,
)
coverage_reported_rule_count = coverage_inputs.get(
    "compatibility_rule_count_reported",
    0,
)
coverage_overall_collector_status = str(
    coverage_collector_status.get(
        "overall",
        "unknown",
    )
)
coverage_status_labels = {
    "complete": "COMPLETE",
    "partial_reference": "PARTIAL REFERENCE",
    "no_reference": "NO REFERENCE",
    "incomplete": "INCOMPLETE",
    "partial": "PARTIAL",
    "none": "NONE",
    "not_applicable": "NOT APPLICABLE",
    "unavailable_release_evidence": "UNAVAILABLE",
    "unavailable_compatibility_report": "UNAVAILABLE",
    "release_evidence_incomplete": "INCOMPLETE",
}
coverage_reference_labels = {
    "complete": "COMPLETE",
    "partial": "PARTIAL",
    "not_available": "NOT AVAILABLE",
    "incomplete": "INCOMPLETE",
    "not_applicable": "NOT APPLICABLE",
    "unknown": "UNKNOWN",
}
coverage_status_label = coverage_status_labels.get(
    coverage_status,
    (
        "ERROR"
        if coverage_overall_collector_status == "error"
        else "UNKNOWN"
    ),
)
coverage_reference_status_label = coverage_reference_labels.get(
    coverage_reference_status,
    "UNKNOWN",
)
coverage_collector_label = {
    "ok": "OK",
    "partial": "PARTIAL",
    "error": "ERROR",
}.get(
    coverage_overall_collector_status,
    "UNKNOWN",
)
coverage_complete = bool(
    coverage_report_available
    and coverage_status == "complete"
    and coverage_reference_status == "complete"
    and coverage_overall_collector_status == "ok"
)

# ------------------------------------------------------------
# Dynamic upgrade correlation data
# ------------------------------------------------------------

correlation_report_available = bool(
    upgrade_correlation_report
)
correlation_scope = upgrade_correlation_report.get(
    "scope",
    {},
)
correlation_summary = upgrade_correlation_report.get(
    "summary",
    {},
)
correlation_rows = upgrade_correlation_report.get(
    "correlations",
    [],
)
correlation_collector_status = upgrade_correlation_report.get(
    "collector_status",
    {},
)
if not isinstance(
    correlation_scope,
    dict,
):
    correlation_scope = {}
if not isinstance(
    correlation_summary,
    dict,
):
    correlation_summary = {}
if not isinstance(
    correlation_rows,
    list,
):
    correlation_rows = []
if not isinstance(
    correlation_collector_status,
    dict,
):
    correlation_collector_status = {}
correlation_model_version = correlation_scope.get(
    "evidence_model_version"
)
correlation_official_count = correlation_summary.get(
    "official_crossed_group_count",
    0,
)
correlation_strong_count = correlation_summary.get(
    "strong_local_evidence_count",
    0,
)
correlation_surface_count = correlation_summary.get(
    "local_surface_evidence_count",
    0,
)
correlation_partial_count = correlation_summary.get(
    "partial_local_evidence_count",
    0,
)
correlation_no_local_count = correlation_summary.get(
    "no_local_evidence_count",
    0,
)
correlation_insufficient_count = correlation_summary.get(
    "insufficient_evidence_count",
    0,
)
correlation_any_count = correlation_summary.get(
    "groups_with_any_local_evidence_count",
    0,
)
correlation_overall_status = str(
    correlation_collector_status.get(
        "overall",
        "unknown",
    )
)
correlation_compatibility_assessed = bool(
    correlation_scope.get(
        "compatibility_assessed",
        False,
    )
)
correlation_verdict_produced = bool(
    correlation_scope.get(
        "readiness_verdict_produced",
        False,
    )
)
correlation_deterministic_influence = bool(
    correlation_scope.get(
        "deterministic_rule_outcomes_used_for_classification",
        False,
    )
)
if not correlation_report_available:
    correlation_status_label = "UNAVAILABLE"
elif correlation_overall_status == "ok":
    correlation_status_label = "COMPLETE"
elif correlation_overall_status == "partial":
    correlation_status_label = "PARTIAL"
elif correlation_overall_status == "error":
    correlation_status_label = "ERROR"
else:
    correlation_status_label = "UNKNOWN"
correlation_strong_groups = []
correlation_surface_groups = []
correlation_partial_groups = []
for item in correlation_rows:
    if not isinstance(
        item,
        dict,
    ):
        continue
    heading = item.get(
        "heading"
    )
    if not heading:
        continue
    status = item.get(
        "correlation_status"
    )
    if status == "strong_local_evidence":
        correlation_strong_groups.append(
            heading
        )
    elif status == "local_surface_evidence":
        correlation_surface_groups.append(
            heading
        )
    elif status == "partial_local_evidence":
        correlation_partial_groups.append(
            heading
        )

# ------------------------------------------------------------
# Correlation validation data
# ------------------------------------------------------------

validation_report_available = bool(
    correlation_validation_report
)
validation_scope = correlation_validation_report.get(
    "scope",
    {},
)
validation_summary = correlation_validation_report.get(
    "summary",
    {},
)
validation_precision_reviews = correlation_validation_report.get(
    "precision_reviews",
    [],
)
validation_collector_status = correlation_validation_report.get(
    "collector_status",
    {},
)
if not isinstance(
    validation_scope,
    dict,
):
    validation_scope = {}
if not isinstance(
    validation_summary,
    dict,
):
    validation_summary = {}
if not isinstance(
    validation_precision_reviews,
    list,
):
    validation_precision_reviews = []
if not isinstance(
    validation_collector_status,
    dict,
):
    validation_collector_status = {}
validation_groups_observed = validation_summary.get(
    "official_groups_observed",
    validation_summary.get(
        "official_groups_compared",
        0,
    ),
)
validation_groups_compared = validation_summary.get(
    "official_groups_compared",
    0,
)
validation_reference_count = validation_summary.get(
    "groups_with_deterministic_reference",
    0,
)
validation_missing_reference_count = validation_summary.get(
    "groups_without_deterministic_reference",
    validation_summary.get(
        "groups_without_complete_deterministic_reference",
        0,
    ),
)
validation_incomplete_reference_count = validation_summary.get(
    "groups_with_incomplete_deterministic_reference",
    0,
)
validation_reference_status = str(
    validation_summary.get(
        "validation_reference_status",
        "unknown",
    )
)
validation_aligned_count = validation_summary.get(
    "aligned_count",
    0,
)
validation_aligned_local_count = validation_summary.get(
    "aligned_local_count",
    0,
)
validation_aligned_no_local_count = validation_summary.get(
    "aligned_no_local_count",
    0,
)
validation_dynamic_gap_count = validation_summary.get(
    "dynamic_gap_count",
    0,
)
validation_deterministic_gap_count = validation_summary.get(
    "deterministic_gap_count",
    0,
)
validation_unresolved_count = validation_summary.get(
    "unresolved_count",
    0,
)
validation_precision_review_count = validation_summary.get(
    "precision_review_count",
    0,
)
validation_accuracy_score_produced = bool(
    validation_scope.get(
        "accuracy_score_produced",
        False,
    )
)
validation_compatibility_assessed = bool(
    validation_scope.get(
        "compatibility_assessed",
        False,
    )
)
validation_verdict_produced = bool(
    validation_scope.get(
        "readiness_verdict_produced",
        False,
    )
)
validation_overall_status = str(
    validation_collector_status.get(
        "overall",
        "unknown",
    )
)
validation_collector_label = {
    "ok": "OK",
    "partial": "PARTIAL",
    "error": "ERROR",
}.get(
    validation_overall_status,
    "UNKNOWN",
)
validation_reference_labels = {
    "complete": "COMPLETE",
    "partial_reference": "PARTIAL REFERENCE",
    "no_reference": "NO REFERENCE",
    "incomplete": "INCOMPLETE",
    "not_applicable": "NOT APPLICABLE",
}
if not validation_report_available:
    validation_status_label = "UNAVAILABLE"
elif validation_overall_status == "error":
    validation_status_label = "ERROR"
elif validation_overall_status == "partial":
    validation_status_label = validation_reference_labels.get(
        validation_reference_status,
        "PARTIAL",
    )
elif validation_overall_status == "ok":
    validation_status_label = validation_reference_labels.get(
        validation_reference_status,
        (
            "COMPLETE"
            if validation_reference_count
            else "UNKNOWN"
        ),
    )
else:
    validation_status_label = "UNKNOWN"
validation_precision_headings = []
for item in validation_precision_reviews:
    if not isinstance(
        item,
        dict,
    ):
        continue
    heading = item.get(
        "official_heading"
    )
    if heading:
        validation_precision_headings.append(
            str(
                heading
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
missing_includes = configuration_tree.get(
    "missing_include_count",
    0,
)
orphan_yaml = configuration_tree.get(
    "orphan_candidate_count",
    0,
)
missing_entities = entity_references.get(
    "missing_count",
    0,
)
duplicate_automation_ids = count_mapping(
    automations.get(
        "duplicate_ids"
    )
)
active_duplicate_automation_names = count_mapping(
    automations.get(
        "active_duplicate_aliases"
    )
)
unresolved_duplicate_automation_names = count_mapping(
    automations.get(
        "unresolved_duplicate_aliases"
    )
)
duplicate_script_names = count_mapping(
    scripts.get(
        "duplicate_aliases"
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
referenced_not_provided = reference_summary.get(
    "referenced_in_active_yaml",
    0,
)
template_review = reference_summary.get(
    "template_no_active_yaml_reference",
    0,
)
history_available = bool(
    history
)
requested_lookback_days = history_policy.get(
    "requested_lookback_days",
    recorder.get(
        "requested_history_lookback_days",
        90,
    ),
)
effective_lookback_days = history_policy.get(
    "effective_lookback_days",
    recorder_availability.get(
        "effective_lookback_days"
    ),
)
recent_activity_days = history_policy.get(
    "recent_activity_days",
    45,
)
history_window_source = history_policy.get(
    "history_window_source"
)
recorder_oldest_run = (
    history_policy.get(
        "recorder_oldest_run"
    )
    or recorder_info.get(
        "oldest_recorder_run"
    )
)
available_history_days = recorder_availability.get(
    "available_history_days"
)
history_recent = history_summary.get(
    "recent_activity",
    0,
)
history_recent_end_unknown = history_summary.get(
    "recent_activity_end_unknown",
    0,
)
history_older = history_summary.get(
    "older_activity",
    0,
)
history_none = history_summary.get(
    "no_usable_history_found",
    0,
)
history_failed = history_summary.get(
    "history_query_failed",
    0,
)

# ------------------------------------------------------------
# Top-level Core update guidance
# ------------------------------------------------------------

audit_available_updates = updates.get(
    "available",
    [],
)
if not isinstance(
    audit_available_updates,
    list,
):
    audit_available_updates = []

audit_core_update_item = next(
    (
        item
        for item in audit_available_updates
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "entity_id"
        )
        == "update.home_assistant_core_update"
    ),
    None,
)

core_update_pending = bool(
    core_upgrade_window.get(
        "pending"
    )
    or audit_core_update_item
)

core_installed_version = (
    core_upgrade_window.get(
        "installed_version"
    )
    or (
        audit_core_update_item.get(
            "installed_version"
        )
        if audit_core_update_item
        else None
    )
    or system.get(
        "core_version"
    )
)

core_target_version = (
    core_upgrade_window.get(
        "target_version"
    )
    or (
        audit_core_update_item.get(
            "latest_version"
        )
        if audit_core_update_item
        else None
    )
)

core_window_complete = bool(
    core_update_pending
    and core_installed_version
    and core_target_version
)

coverage_usable = bool(
    coverage_report_available
    and coverage_overall_collector_status
    in (
        "ok",
        "partial",
    )
    and coverage_status
    in (
        "complete",
        "partial_reference",
        "no_reference",
        "not_applicable",
    )
)

correlation_complete = bool(
    correlation_report_available
    and correlation_overall_status
    == "ok"
)

validation_usable = bool(
    validation_report_available
    and validation_overall_status
    in (
        "ok",
        "partial",
    )
    and validation_reference_status
    in (
        "complete",
        "partial_reference",
        "no_reference",
        "not_applicable",
    )
)

deterministic_compatibility_required = (
    coverage_reference_status
    in (
        "complete",
        "partial",
        "incomplete",
    )
)

core_guidance = evaluate_core_update_guidance(
    core_update_pending=core_update_pending,
    update_readiness_available=update_readiness_available,
    core_window_complete=core_window_complete,
    collector_error_count=len(
        collector_errors
    ),
    configuration_check_state=config_result,
    release_evidence_complete=release_collection_complete,
    compatibility_coverage_usable=coverage_usable,
    dynamic_correlation_complete=correlation_complete,
    dynamic_correlation_insufficient_count=(
        correlation_insufficient_count
    ),
    correlation_validation_usable=validation_usable,
    deterministic_compatibility_required=(
        deterministic_compatibility_required
    ),
    deterministic_compatibility_available=(
        compatibility_assessed
    ),
    deterministic_yaml_failure_count=len(
        compatibility_yaml_failures
    ),
    relevant_unignored_repair_count=(
        readiness_relevant_unignored_count
    ),
    compatibility_review_required_count=(
        compatibility_review_required_count
    ),
    compatibility_manual_review_count=(
        compatibility_manual_review_count
    ),
)

core_guidance_status = core_guidance.get(
    "status",
    STATE_INCOMPLETE,
)
core_assessment_complete = bool(
    core_guidance.get(
        "assessment_complete",
        False,
    )
)

# ------------------------------------------------------------
# Build summary
# ------------------------------------------------------------

lines = []

def add(text=""):
    lines.append(text)

add("=" * 58)
add(
    f"HA AUDIT v{VERSION} - "
    f"CURRENT RUN SUMMARY"
)
add(
    f"Generated: "
    f"{format_generated_time(audit)}"
)
add("=" * 58)

# ------------------------------------------------------------
# Overview
# ------------------------------------------------------------

add("")
add("OVERVIEW")
add("-" * 58)
add(
    f"Core update:                 "
    f"{core_guidance_status}"
)

if core_guidance_status == STATE_NO_UPDATE:
    assessment_label = "NOT APPLICABLE"
else:
    assessment_label = (
        "COMPLETE"
        if core_assessment_complete
        else "INCOMPLETE"
    )

add(
    f"Assessment completeness:     "
    f"{assessment_label}"
)
add(
    f"Config check:                "
    f"{str(config_result).upper()}"
)

if core_update_pending:
    add(
        f"Core:                        "
        f"{core_installed_version or 'unknown'}"
        " -> "
        f"{core_target_version or 'unknown'}"
    )
else:
    add(
        f"Core:                        "
        f"{system.get('core_version') or 'unknown'}"
    )

add("")

if core_guidance_status == STATE_CLEAR:
    add(
        "No known blockers were found in the evidence "
        "HA Audit inspected."
    )
    add(
        "This is not a guarantee that the update cannot "
        "cause a problem."
    )
elif core_guidance_status == STATE_REVIEW:
    add(
        "One or more findings should be reviewed before "
        "installing the Core update."
    )
    add(
        "See NEXT ACTIONS for the specific evidence."
    )
elif core_guidance_status == STATE_INCOMPLETE:
    add(
        "HA Audit could not complete every part of the "
        "Core update assessment."
    )
    add(
        "Review the evidence sections and NEXT ACTIONS "
        "before updating."
    )
elif core_guidance_status == STATE_BLOCKER:
    add(
        "HA Audit found explicit blocker evidence for "
        "this Core update."
    )
    add(
        "Review NEXT ACTIONS before updating."
    )
else:
    add(
        "No pending Home Assistant Core update was found."
    )

add(
    "Core update guidance is conservative evidence-based "
    "guidance, not a safe-to-update guarantee."
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
    if core_upgrade_window.get(
        "pending"
    ):
        add(
            "Deterministic reference:     "
            f"{coverage_reference_status_label}"
        )
        add(
            "Compatibility coverage:      "
            f"{coverage_status_label}"
        )
        add(
            "Dynamic correlation:         "
            f"{correlation_status_label}"
        )
        add(
            "Correlation validation:      "
            f"{validation_status_label}"
        )
    else:
        add(
            "Deterministic reference:     "
            "NOT APPLICABLE"
        )
        add(
            "Compatibility coverage:      "
            "NOT APPLICABLE"
        )
        add(
            "Dynamic correlation:         "
            "NOT APPLICABLE"
        )
        add(
            "Correlation validation:      "
            "NOT APPLICABLE"
        )
    add(
        "Official release evidence:    "
        f"{release_status_label}"
    )
    add(
        "Readiness verdict:           "
        + (
            "PRODUCED"
            if compatibility_verdict_produced
            else "NOT PRODUCED"
        )
    )
    add("")
    add(
        "Update and Repair evidence is local. "
        "Official release evidence, deterministic reference "
        "availability, dynamic correlation, correlation validation, "
        "and deterministic compatibility results are shown "
        "separately below."
    )
else:
    add(
        "Update readiness report unavailable."
    )

# ------------------------------------------------------------
# Official release evidence
# ------------------------------------------------------------

add("")
add("OFFICIAL RELEASE EVIDENCE")
add("-" * 58)
if release_evidence_available:
    if release_applicable:
        add(
            "Upgrade window:              "
            f"{core_upgrade_window.get('installed_version')}"
            " -> "
            f"{core_upgrade_window.get('target_version')}"
        )
        if release_same_family:
            add(
                "Core releases crossed:       "
                "0 (same-family update)"
            )
        else:
            add(
                f"Core releases crossed:       "
                f"{release_crossed_count}"
            )
        if release_requested_families:
            add(
                "Release families:            "
                + ", ".join(
                    str(item)
                    for item
                    in release_requested_families
                )
            )
        add(
            f"Official releases fetched:   "
            f"{release_fetch_success_count} / "
            f"{release_family_count}"
        )
        add(
            f"Breaking-change groups:      "
            f"{release_breaking_group_count}"
        )
        add(
            f"Crossed change groups:       "
            f"{release_crossed_group_count}"
        )
        add("")
        add(
            f"Successful parses:           "
            f"{release_success_count}"
        )
        add(
            f"Structured BIC parses:       "
            f"{release_structured_parse_count}"
        )
        add(
            f"Partial parses:              "
            f"{release_partial_count}"
        )
        add(
            f"Failed parses:               "
            f"{release_failure_count}"
        )
        add("")
        add(
            "Official sources only:       "
            + (
                "YES"
                if release_official_sources_only
                else "NO"
            )
        )
        add(
            "Runtime fetch:               "
            + (
                "PERFORMED"
                if release_external_fetch
                else "NOT PERFORMED"
            )
        )
        add(
            f"Evidence collection:         "
            f"{release_status_label}"
        )
        add(
            "Compatibility matching:      SEPARATE"
        )
        add(
            "Readiness verdict:           NOT PRODUCED"
        )
        add("")
        add(
            "Official evidence is collected release by release. "
            "Evidence completeness does not mean compatibility "
            "assessment is complete."
        )
        if release_same_family:
            add(
                "Same-family monthly change groups are retained "
                "as evidence but are not counted as newly crossed."
            )
    else:
        add(
            f"Evidence collection:         "
            f"{release_status_label}"
        )
        add(
            f"Release-range status:        "
            f"{release_range_status}"
        )
        if release_applicability_reason:
            add(
                "Reason:                     "
                f"{release_applicability_reason}"
            )
else:
    add(
        "Official release evidence report unavailable."
    )

# ------------------------------------------------------------
# Compatibility coverage
# ------------------------------------------------------------

add("")
add("COMPATIBILITY COVERAGE")
add("-" * 58)
if coverage_report_available:
    add(
        f"Official crossed groups:      "
        f"{coverage_official_group_count}"
    )
    add(
        f"Registry-backed groups:       "
        f"{coverage_registry_group_count}"
    )
    add(
        f"Groups with rule coverage:    "
        f"{coverage_covered_group_count}"
    )
    add(
        f"Partially covered groups:     "
        f"{coverage_partial_group_count}"
    )
    add(
        f"Unmapped registry groups:     "
        f"{coverage_unmapped_group_count}"
    )
    add(
        f"No-reference groups:          "
        f"{coverage_no_reference_group_count}"
    )
    if coverage_incomplete_reference_group_count:
        add(
            f"Incomplete reference groups:  "
            f"{coverage_incomplete_reference_group_count}"
        )
    add("")
    add(
        f"Deterministic rules:          "
        f"{coverage_reported_rule_count}"
    )
    add(
        f"Mapped rules:                 "
        f"{coverage_mapped_rule_count}"
    )
    add(
        f"Linked rules present:         "
        f"{coverage_present_linked_rule_count}"
    )
    add(
        f"Missing mapped rules:         "
        f"{coverage_missing_mapped_rule_count}"
    )
    add(
        f"Unlinked rules:               "
        f"{coverage_unlinked_rule_count}"
    )
    if coverage_release_rows:
        add("")
        add("Release coverage:")
        for item in coverage_release_rows:
            if not isinstance(
                item,
                dict,
            ):
                continue
            release_family = item.get(
                "release_family",
                "unknown",
            )
            covered = item.get(
                "covered_group_count",
                0,
            )
            total = item.get(
                "official_group_count",
                0,
            )
            item_status = str(
                item.get(
                    "coverage_status",
                    "unknown",
                )
            ).replace(
                "_",
                " ",
            ).upper()
            item_reference_status = str(
                item.get(
                    "reference_status",
                    "unknown",
                )
            ).replace(
                "_",
                " ",
            ).upper()
            add(
                f"  {release_family}: "
                f"{covered} / {total} "
                f"({item_status}; "
                f"reference {item_reference_status})"
            )
    add("")
    add(
        f"Reference status:             "
        f"{coverage_reference_status_label}"
    )
    add(
        f"Coverage/reference state:     "
        f"{coverage_status_label}"
    )
    add(
        f"Collector health:             "
        f"{coverage_collector_label}"
    )
    add(
        "Readiness verdict:            NOT PRODUCED"
    )
    add("")
    add(
        "Coverage describes deterministic reference availability "
        "for official backward-incompatible change groups."
    )
    if coverage_status == "no_reference":
        add(
            "No deterministic reference exists for this release "
            "family. This is a supported dynamic-only state, not "
            "a collector failure."
        )
    elif coverage_status == "partial_reference":
        add(
            "Deterministic reference coverage exists for some "
            "crossed release families; remaining groups are "
            "dynamic-only."
        )
    elif coverage_status == "incomplete":
        add(
            "A deterministic registry exists, but expected mapping "
            "or rule evidence is incomplete and should be reviewed."
        )
    else:
        add(
            "A covered group means deterministic rules are linked; "
            "it does not mean every configuration path was inspected "
            "or that the installation is safe to update."
        )
else:
    add(
        "Compatibility coverage report unavailable."
    )

# ------------------------------------------------------------
# Dynamic upgrade correlation
# ------------------------------------------------------------

add("")
add("DYNAMIC UPGRADE CORRELATION")
add("-" * 58)
if correlation_report_available:
    add(
        f"Official change groups:       "
        f"{correlation_official_count}"
    )
    add(
        f"Specific code evidence:       "
        f"{correlation_strong_count}"
    )
    add(
        f"Local surface evidence:       "
        f"{correlation_surface_count}"
    )
    add(
        f"Partial evidence:             "
        f"{correlation_partial_count}"
    )
    add(
        f"No local evidence:            "
        f"{correlation_no_local_count}"
    )
    add(
        f"Insufficient evidence:        "
        f"{correlation_insufficient_count}"
    )
    add("")
    add(
        f"Groups with local evidence:   "
        f"{correlation_any_count} / "
        f"{correlation_official_count}"
    )
    add(
        "Evidence model:               "
        + (
            f"v{correlation_model_version}"
            if correlation_model_version is not None
            else "unknown"
        )
    )
    add(
        f"Correlation collection:       "
        f"{correlation_status_label}"
    )
    add(
        "Compatibility assessed:       "
        + (
            "YES"
            if correlation_compatibility_assessed
            else "NO"
        )
    )
    add(
        "Readiness verdict:            "
        + (
            "PRODUCED"
            if correlation_verdict_produced
            else "NOT PRODUCED"
        )
    )
    add(
        "Deterministic outcomes used:  "
        + (
            "YES"
            if correlation_deterministic_influence
            else "NO"
        )
    )
    if (
        correlation_strong_groups
        or correlation_surface_groups
        or correlation_partial_groups
    ):
        add("")
    if correlation_strong_groups:
        add("Specific:")
        for heading in correlation_strong_groups:
            add(
                f"  {heading}"
            )
    if correlation_surface_groups:
        add("Local surface:")
        for heading in correlation_surface_groups:
            add(
                f"  {heading}"
            )
    if correlation_partial_groups:
        add("Partial:")
        for heading in correlation_partial_groups:
            add(
                f"  {heading}"
            )
    add("")
    add(
        "Dynamic correlation identifies local evidence related "
        "to official change groups."
    )
    add(
        "It does not decide whether the installation is affected, "
        "compatible, incompatible, or safe to update."
    )
else:
    add(
        "Dynamic upgrade correlation report unavailable."
    )

# ------------------------------------------------------------
# Correlation validation
# ------------------------------------------------------------

add("")
add("CORRELATION VALIDATION")
add("-" * 58)
if validation_report_available:
    add(
        f"Official groups observed:      "
        f"{validation_groups_observed}"
    )
    add(
        f"Official groups compared:      "
        f"{validation_groups_compared}"
    )
    add(
        f"Deterministic references:      "
        f"{validation_reference_count}"
    )
    add(
        f"Groups without reference:      "
        f"{validation_missing_reference_count}"
    )
    if validation_incomplete_reference_count:
        add(
            f"Incomplete references:         "
            f"{validation_incomplete_reference_count}"
        )
    if validation_groups_compared:
        add("")
        add(
            f"Aligned local relevance:       "
            f"{validation_aligned_count} / "
            f"{validation_groups_compared}"
        )
        add(
            f"  Local evidence:              "
            f"{validation_aligned_local_count}"
        )
        add(
            f"  No local evidence:           "
            f"{validation_aligned_no_local_count}"
        )
        add("")
        add(
            f"Dynamic gaps:                  "
            f"{validation_dynamic_gap_count}"
        )
        add(
            f"Deterministic gaps:            "
            f"{validation_deterministic_gap_count}"
        )
        add(
            f"Unresolved comparisons:        "
            f"{validation_unresolved_count}"
        )
        add(
            f"Precision reviews:             "
            f"{validation_precision_review_count}"
        )
    add("")
    add(
        f"Reference validation:          "
        f"{validation_status_label}"
    )
    add(
        f"Collector health:              "
        f"{validation_collector_label}"
    )
    add(
        "Accuracy score:                "
        + (
            "PRODUCED"
            if validation_accuracy_score_produced
            else "NOT PRODUCED"
        )
    )
    add(
        "Compatibility assessed:        "
        + (
            "YES"
            if validation_compatibility_assessed
            else "NO"
        )
    )
    add(
        "Readiness verdict:             "
        + (
            "PRODUCED"
            if validation_verdict_produced
            else "NOT PRODUCED"
        )
    )
    if validation_precision_headings:
        add("")
        add("Precision review:")
        for heading in validation_precision_headings:
            add(
                f"  {heading}"
            )
    add("")
    if validation_reference_status == "no_reference":
        add(
            "No deterministic reference exists for this release "
            "family. Dynamic correlation remains valid and "
            "independent."
        )
    elif validation_reference_status == "partial_reference":
        add(
            "Validation covers only official groups with a "
            "deterministic reference; remaining groups are "
            "dynamic-only."
        )
    elif validation_reference_status == "incomplete":
        add(
            "Expected deterministic reference material is "
            "incomplete, so the affected comparisons require "
            "review."
        )
    else:
        add(
            "Validation compares local-relevance alignment between "
            "the dynamic and deterministic paths."
        )
        add(
            "Alignment is reference evidence only. It is not an "
            "accuracy score, compatibility verdict, or proof that "
            "either path is correct."
        )
else:
    add(
        "Correlation validation report unavailable."
    )

# ------------------------------------------------------------
# Upgrade compatibility
# ------------------------------------------------------------

add("")
add("UPGRADE COMPATIBILITY")
add("-" * 58)
if upgrade_compatibility_available:
    if compatibility_rule_count:
        add(
            f"Core rule pack:              "
            f"{compatibility_rule_pack_label}"
        )
        add(
            "Upgrade window:              "
            f"{compatibility_window.get('installed_version')}"
            " -> "
            f"{compatibility_window.get('target_version')}"
        )
        add(
            f"Rules assessed:              "
            f"{compatibility_rule_count}"
        )
        add("")
        add(
            f"No local match:              "
            f"{compatibility_no_local_match_count}"
        )
        add(
            f"Local match, no affected use: "
            f"{compatibility_no_affected_count}"
        )
        add(
            f"Review required:             "
            f"{compatibility_review_required_count}"
        )
        add(
            f"Manual review:               "
            f"{compatibility_manual_review_count}"
        )
        if compatibility_other_outcome_count:
            add(
                f"Other local outcomes:        "
                f"{compatibility_other_outcome_count}"
            )
        add("")
        add(
            f"Active YAML checked:         "
            f"{compatibility_active_yaml_count}"
        )
        add(
            f"YAML scan failures:          "
            f"{len(compatibility_yaml_failures)}"
        )
        add("")
        add(
            "LLM UI-managed prompts:      "
            + (
                "INSPECTED"
                if compatibility_ui_prompts_inspected
                else "NOT INSPECTED"
            )
        )
        add(
            "Compatibility scanner fetch: "
            + (
                "PERFORMED"
                if compatibility_runtime_fetch
                else "NOT PERFORMED"
            )
        )
        add(
            "Readiness verdict:           "
            + (
                "PRODUCED"
                if compatibility_verdict_produced
                else "NOT PRODUCED"
            )
        )
        add("")
        add(
            "Rule results are evidence for review, not a "
            "safe-to-update verdict."
        )
        if not compatibility_ui_prompts_inspected:
            add(
                "UI-managed LLM prompt content is outside "
                "the current local scan scope."
            )
    else:
        if coverage_status == "no_reference":
            add(
                "No deterministic Core compatibility rule pack "
                "is available for this upgrade window."
            )
            add(
                "This is a supported dynamic-only state. "
                "See DYNAMIC UPGRADE CORRELATION for the "
                "available local evidence."
            )
        else:
            add(
                "No version-specific Core compatibility "
                "rule pack is applicable to this run."
            )
else:
    add(
        "Upgrade compatibility report unavailable."
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
    if core_upgrade_window.get(
        "pending"
    ):
        if release_status_label != "COMPLETE":
            actions += 1
            add(
                f"[!] Official Core release evidence is "
                f"{release_status_label.lower()}."
            )
            if release_applicability_reason:
                add(
                    f"    {release_applicability_reason}"
                )
            add(
                "    Review release_evidence_audit.json before "
                "treating upgrade evidence as complete."
            )
        if (
            coverage_status_label
            not in (
                "COMPLETE",
                "PARTIAL REFERENCE",
                "NO REFERENCE",
                "NOT APPLICABLE",
            )
            or coverage_collector_label != "OK"
        ):
            actions += 1
            add(
                f"[!] Deterministic reference coverage is "
                f"{coverage_status_label.lower()}."
            )
            add(
                f"    Registry-backed groups: "
                f"{coverage_registry_group_count}/"
                f"{coverage_official_group_count}; "
                f"covered: {coverage_covered_group_count}; "
                f"partial: {coverage_partial_group_count}; "
                f"unmapped: {coverage_unmapped_group_count}."
            )
            add(
                "    Review compatibility_coverage_audit.json "
                "for incomplete deterministic reference evidence."
            )
        if correlation_status_label not in (
            "COMPLETE",
            "NOT APPLICABLE",
        ):
            actions += 1
            add(
                f"[!] Dynamic upgrade correlation is "
                f"{correlation_status_label.lower()}."
            )
            add(
                "    Review upgrade_correlation_audit.json "
                "for missing or incomplete evidence collection."
            )
        if validation_status_label not in (
            "COMPLETE",
            "PARTIAL REFERENCE",
            "NO REFERENCE",
            "NOT APPLICABLE",
        ):
            actions += 1
            add(
                f"[!] Correlation reference validation is "
                f"{validation_status_label.lower()}."
            )
            add(
                "    Review correlation_validation_audit.json "
                "for incomplete or failed reference comparison."
            )
        if compatibility_assessed:
            actions += 1
            if (
                compatibility_review_required_count
                or compatibility_manual_review_count
            ):
                add(
                    f"[!] Core {compatibility_rule_pack_label} "
                    "compatibility rules found items that "
                    "need review."
                )
                add(
                    f"    Review required: "
                    f"{compatibility_review_required_count}; "
                    f"manual review: "
                    f"{compatibility_manual_review_count}."
                )
                add(
                    "    Review upgrade_compatibility_audit.json "
                    "before installing the Core update."
                )
            else:
                add(
                    f"[i] Core {compatibility_rule_pack_label} "
                    "compatibility rules were assessed "
                    "against this installation."
                )
                add(
                    f"    {compatibility_rule_count} documented "
                    "change rule(s) were checked."
                )
                if release_collection_complete:
                    family_word = pluralise(
                        release_family_count,
                        "release family",
                        "release families",
                    )
                    add(
                        f"    Official release evidence was collected "
                        f"for {release_family_count} {family_word}."
                    )
                if coverage_complete:
                    add(
                        f"    Deterministic reference covers "
                        f"{coverage_covered_group_count}/"
                        f"{coverage_official_group_count} official "
                        "crossed change groups."
                    )
                elif coverage_status == "partial_reference":
                    add(
                        f"    Deterministic reference covers "
                        f"{coverage_covered_group_count}/"
                        f"{coverage_official_group_count} official "
                        "crossed change groups."
                    )
                    add(
                        f"    {coverage_no_reference_group_count} "
                        "official group(s) have no deterministic "
                        "reference and remain dynamic-only."
                    )
                elif coverage_status == "no_reference":
                    add(
                        "    No deterministic reference is available "
                        "for the crossed release family."
                    )
                    add(
                        "    This is a supported dynamic-only state, "
                        "not a collector failure."
                    )
                if correlation_status_label == "COMPLETE":
                    add(
                        f"    Dynamic correlation found local evidence "
                        f"for {correlation_any_count}/"
                        f"{correlation_official_count} official "
                        "change groups."
                    )
                    add(
                        f"    Evidence split: "
                        f"{correlation_strong_count} specific, "
                        f"{correlation_surface_count} local surface, "
                        f"{correlation_partial_count} partial."
                    )
                add(
                    "    No affected local usage requiring "
                    "review was detected by this rule pack."
                )
                if coverage_status == "incomplete":
                    add(
                        "    Deterministic reference coverage is "
                        "incomplete; expected mapping or rule evidence "
                        "requires review."
                    )
                add(
                    "    Dynamic correlation and deterministic "
                    "rule results are evidence only; this is not "
                    "a safe-to-update verdict."
                )
        else:
            actions += 1
            if coverage_status == "no_reference":
                add(
                    "[i] No deterministic reference is available "
                    "for this Core upgrade window."
                )
                add(
                    "    This is a supported dynamic-only state, "
                    "not a scanner failure."
                )
                if correlation_status_label == "COMPLETE":
                    add(
                        f"    Dynamic correlation collected evidence "
                        f"for {correlation_official_count} official "
                        "change group(s), with local evidence for "
                        f"{correlation_any_count}."
                    )
                add(
                    "    No compatibility or safe-to-update verdict "
                    "is produced."
                )
            elif coverage_status == "partial_reference":
                add(
                    "[i] Deterministic reference is available for "
                    "only part of this Core upgrade window."
                )
                add(
                    f"    Covered groups: "
                    f"{coverage_covered_group_count}/"
                    f"{coverage_official_group_count}; "
                    f"dynamic-only groups: "
                    f"{coverage_no_reference_group_count}."
                )
                add(
                    "    Dynamic correlation remains available for "
                    "groups without deterministic reference."
                )
                add(
                    "    No safe-to-update verdict is produced."
                )
            else:
                add(
                    f"[i] {readiness_pending_count} update(s) "
                    "are pending."
                )
                add(
                    "    Local update and Repair evidence has "
                    "been collected, but version-specific Core "
                    "compatibility rules are not assessed."
                )
                add(
                    "    Do not interpret this result "
                    "as a safe-to-update verdict."
                )
    elif readiness_pending_count:
        actions += 1
        add(
            f"[i] {readiness_pending_count} non-Core "
            "update(s) are pending."
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
        "update-readiness, release-evidence, deterministic-reference, "
        "dynamic-correlation, correlation-validation, "
        "or compatibility-review actions were identified "
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
    "upgrade_impact_audit.json",
    "upgrade_compatibility_audit.json",
    "release_evidence_audit.json",
    "compatibility_coverage_audit.json",
    "upgrade_correlation_audit.json",
    "correlation_validation_audit.json",
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
add("=" * 58)
summary = (
    "\n".join(lines)
    + "\n"
)
with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:
    handle.write(summary)
print(
    summary,
    end="",
)
