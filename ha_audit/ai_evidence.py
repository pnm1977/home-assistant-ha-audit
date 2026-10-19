import json
import os
import re
from datetime import datetime, timezone


VERSION = os.environ.get("HA_AUDIT_VERSION", "unknown")
SCHEMA_VERSION = 1

AUDIT_FILE = "/config/audit_snapshot.json"
QUALITY_FILE = "/config/quality_audit.json"
LOG_FAMILY_FILE = "/config/log_issue_families.json"
LOG_PRIORITY_FINAL_FILE = "/config/log_priority_final.json"
LOG_CORRELATION_FILE = "/config/log_correlation.json"
OUTPUT_FILE = "/config/ha_audit_ai_evidence.json"

MAX_REPRESENTATIVE_MESSAGES = 3
PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "VERY LOW": 3}

ENTITY_LIST_RE = re.compile(r"entity_id=\[([^\]]+)\]", re.IGNORECASE)
ENTITY_SINGLE_RE = re.compile(
    r"entity_id=['\"]?([a-z_][a-z0-9_]*\.[a-z0-9_]+)", re.IGNORECASE
)
REFERENCED_ENTITIES_RE = re.compile(
    r"Referenced entities?\s+(.+?)\s+are missing", re.IGNORECASE
)
ENTITY_QUOTED_RE = re.compile(
    r"\bentity\s+['\"]([a-z_][a-z0-9_]*\.[a-z0-9_]+)['\"]", re.IGNORECASE
)
TEMPLATE_ENTITY_RE = re.compile(
    r"(?:states\[|states\(|state_attr\(|is_state\()\s*['\"]"
    r"([a-z_][a-z0-9_]*\.[a-z0-9_]+)['\"]",
    re.IGNORECASE,
)
QUOTED_ID_RE = re.compile(
    r"['\"]([a-z_][a-z0-9_]*\.[a-z0-9_]+)['\"]", re.IGNORECASE
)
DEVICE_ID_RE = re.compile(
    r"\bReferenced devices?\s+([0-9a-f]{32})\b", re.IGNORECASE
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
MAC_RE = re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b")
IEEE_RE = re.compile(r"\b0x[0-9a-fA-F]{16}\b")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_json_optional(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=False)
        handle.write("\n")


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def unique_strings(values):
    result = []
    seen = set()
    for value in values:
        text = " ".join(str(value or "").split())
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def redact_message(value):
    text = str(value or "")
    text = MAC_RE.sub("<MAC_ADDRESS>", text)
    text = IEEE_RE.sub("<IEEE_ADDRESS>", text)
    return IPV4_RE.sub("<IP_ADDRESS>", text)


def extract_entity_ids(messages):
    values = []
    for message in messages:
        text = str(message or "")

        for match in ENTITY_LIST_RE.finditer(text):
            values.extend(QUOTED_ID_RE.findall(match.group(1)))

        values.extend(ENTITY_SINGLE_RE.findall(text))

        for match in REFERENCED_ENTITIES_RE.finditer(text):
            chunk = match.group(1)
            quoted = QUOTED_ID_RE.findall(chunk)
            if quoted:
                values.extend(quoted)
            else:
                values.extend(
                    re.findall(
                        r"\b[a-z_][a-z0-9_]*\.[a-z0-9_]+\b",
                        chunk,
                        flags=re.IGNORECASE,
                    )
                )

        values.extend(ENTITY_QUOTED_RE.findall(text))
        values.extend(TEMPLATE_ENTITY_RE.findall(text))

    return unique_strings(values)


def extract_device_ids(messages):
    values = []
    for message in messages:
        values.extend(DEVICE_ID_RE.findall(str(message or "")))
    return unique_strings(values)


def logger_entity_ids(logger_names, integration):
    prefix = f"homeassistant.components.{integration}."
    values = []
    for logger in logger_names:
        logger = str(logger or "")
        if logger.startswith(prefix):
            suffix = logger[len(prefix):]
            if suffix:
                values.append(f"{integration}.{suffix}")
    return unique_strings(values)


def family_index(report):
    result = {}
    for item in as_list(as_dict(report).get("families")):
        if isinstance(item, dict) and item.get("family_id"):
            result[item["family_id"]] = item
    return result


def missing_reference_index(quality):
    references = as_dict(as_dict(quality).get("entity_references"))
    result = {}
    for item in as_list(references.get("missing_candidates")):
        if isinstance(item, dict) and item.get("entity_id"):
            result[item["entity_id"]] = item
    return result


def build_system_context(audit):
    audit = as_dict(audit)
    system = as_dict(audit.get("system"))
    check = as_dict(audit.get("configuration_check"))
    check_data = as_dict(check.get("data"))
    return {
        "core_version": system.get("core_version"),
        "supervisor_version": system.get("supervisor_version"),
        "os_version": system.get("os_version"),
        "timezone": system.get("timezone"),
        "configuration_check": check_data.get("result") or check.get("status"),
    }


def build_configuration_findings(quality):
    quality = as_dict(quality)
    tree = as_dict(quality.get("configuration_tree"))
    inactive = as_dict(tree.get("inactive_classification"))
    automations = as_dict(quality.get("automations"))
    scripts = as_dict(quality.get("scripts"))
    references = as_dict(quality.get("entity_references"))

    return {
        "missing_active_includes": as_list(tree.get("missing_includes")),
        "missing_entity_references": as_list(references.get("missing_candidates")),
        "duplicate_automation_ids": as_dict(automations.get("duplicate_id_details")),
        "active_duplicate_automation_aliases": as_dict(
            automations.get("active_duplicate_aliases")
        ),
        "unresolved_duplicate_automation_aliases": as_dict(
            automations.get("unresolved_duplicate_aliases")
        ),
        "duplicate_script_aliases": as_dict(scripts.get("duplicate_aliases")),
        "orphan_yaml_candidates": as_list(inactive.get("orphan_candidate")),
    }


def power_expectation(correlation):
    availability = as_dict(as_dict(correlation).get("availability"))
    classes = {
        str(item.get("classification", "")).strip().lower()
        for item in as_list(availability.get("matches"))
        if isinstance(item, dict)
    }
    if "maintenance" in classes:
        return "MAINTENANCE", "EXPLICIT_AVAILABILITY_LABEL"
    if "expected_offline" in classes:
        return "EXPECTED_OFFLINE", "EXPLICIT_AVAILABILITY_LABEL"
    return "UNKNOWN", "NO_EXPLICIT_POWER_EXPECTATION"


def compact_availability(correlation):
    correlation = as_dict(correlation)
    availability = as_dict(correlation.get("availability"))
    expectation, source = power_expectation(correlation)
    matches = []

    for item in as_list(availability.get("matches")):
        if not isinstance(item, dict):
            continue
        matches.append(
            {
                "entity_id": item.get("entity_id"),
                "platform": item.get("platform"),
                "device": item.get("device"),
                "classification": item.get("classification"),
                "labels": as_list(item.get("labels")),
                "history_status": item.get("history_status"),
                "last_usable_state_started_at": item.get("last_usable_state_started_at"),
                "last_usable_state_ended_at": item.get("last_usable_state_ended_at"),
            }
        )

    return {
        "correlation_class": correlation.get("correlation_class"),
        "classification": availability.get("classification"),
        "matches": matches,
        "power_expectation": expectation,
        "power_expectation_source": source,
    }


def compact_repairs(correlation):
    repairs = as_dict(as_dict(correlation).get("repairs"))
    matches = []
    for item in as_list(repairs.get("matches")):
        if not isinstance(item, dict):
            continue
        matches.append(
            {
                "domain": item.get("domain"),
                "severity": item.get("severity"),
                "ignored": item.get("ignored"),
                "is_fixable": item.get("is_fixable"),
                "translation_key": item.get("translation_key"),
                "upgrade_relevance": item.get("upgrade_relevance"),
            }
        )
    return {
        "classification": repairs.get("classification"),
        "unignored_match_count": repairs.get("unignored_match_count", 0),
        "ignored_match_count": repairs.get("ignored_match_count", 0),
        "matches": matches,
    }


def build_issue(final_item, family, correlation, missing_references):
    final_item = as_dict(final_item)
    family = as_dict(family)
    correlation = as_dict(correlation)

    raw_messages = as_list(family.get("message_samples"))
    representative_messages = [
        redact_message(item) for item in raw_messages[:MAX_REPRESENTATIVE_MESSAGES]
    ]
    logger_names = unique_strings(as_list(family.get("logger_names")))
    entity_ids = extract_entity_ids(raw_messages)

    automations = unique_strings(
        [item for item in entity_ids if item.startswith("automation.")]
        + logger_entity_ids(logger_names, "automation")
    )
    scripts = unique_strings(
        [item for item in entity_ids if item.startswith("script.")]
        + logger_entity_ids(logger_names, "script")
    )
    entities = [
        item
        for item in entity_ids
        if not item.startswith(("automation.", "script."))
    ]

    availability = compact_availability(correlation)
    devices = []
    device_keys = set()

    for match in availability["matches"]:
        name = match.get("device")
        if name and name not in device_keys:
            device_keys.add(name)
            devices.append({"name": name, "source": "availability_correlation"})

    for device_id in extract_device_ids(raw_messages):
        key = f"id:{device_id}"
        if key not in device_keys:
            device_keys.add(key)
            devices.append(
                {"device_id": device_id, "name": None, "source": "system_log_message"}
            )

    configuration_links = [
        missing_references[item] for item in entities if item in missing_references
    ]

    gaps = []
    if not representative_messages:
        gaps.append("NO_REPRESENTATIVE_LOG_MESSAGE")
    if family.get("grouping_method") == "single_entry_fallback":
        gaps.append("ISSUE_NOT_CLASSIFIED")
    if (
        str(final_item.get("local_action_path", "")).upper() == "LOCAL INVESTIGATION"
        and not (entities or devices or automations or scripts)
    ):
        gaps.append("NO_AFFECTED_TARGET_IDENTIFIED")
    if (
        availability["power_expectation"] == "UNKNOWN"
        and str(final_item.get("ownership", "")).upper() == "DEVICE / LOCAL NETWORK"
    ):
        gaps.append("POWER_EXPECTATION_UNKNOWN")

    recurrence = as_dict(final_item.get("recurrence"))

    return {
        "stable_issue_id": final_item.get("stable_fingerprint"),
        "family_id": final_item.get("family_id"),
        "title": final_item.get("title") or family.get("title"),
        "grouping_method": family.get("grouping_method"),
        "priority": final_item.get("final_priority"),
        "snapshot_priority": final_item.get("snapshot_priority"),
        "ownership": final_item.get("ownership"),
        "ownership_confidence": final_item.get("ownership_confidence"),
        "local_action_path": final_item.get("local_action_path"),
        "occurrence_count": final_item.get(
            "occurrence_count", family.get("occurrence_count", 0)
        ),
        "first_seen": family.get("first_seen"),
        "last_seen": family.get("last_seen"),
        "recurrence": {
            "class": recurrence.get("class"),
            "observation_span_hours": recurrence.get("observation_span_hours"),
        },
        "direct_failure_evidence": final_item.get("direct_failure_evidence"),
        "recovery_evidence": final_item.get("recovery_evidence"),
        "fallback_evidence": final_item.get("fallback_evidence"),
        "loggers": logger_names,
        "source_locations": unique_strings(as_list(family.get("sources"))),
        "representative_messages": representative_messages,
        "affected_entities": entities,
        "affected_devices": devices,
        "affected_automations": automations,
        "affected_scripts": scripts,
        "availability_context": availability,
        "repairs_context": compact_repairs(correlation),
        "configuration_links": configuration_links,
        "evidence_gaps": gaps,
    }


def issue_sort_key(item):
    priority = str(item.get("priority", "")).upper()
    return (
        PRIORITY_ORDER.get(priority, 99),
        -int(item.get("occurrence_count", 0) or 0),
        str(item.get("title", "")),
    )


def build_ai_evidence(
    *,
    audit,
    quality,
    log_families,
    log_priority_final,
    log_correlation,
    version=VERSION,
    generated_at=None,
):
    generated_at = generated_at or utc_now()
    family_by_id = family_index(log_families)
    correlation_by_id = family_index(log_correlation)
    missing_references = missing_reference_index(quality)
    issues = []

    for item in as_list(as_dict(log_priority_final).get("families")):
        if not isinstance(item, dict):
            continue
        family_id = item.get("family_id")
        issues.append(
            build_issue(
                item,
                family_by_id.get(family_id, {}),
                correlation_by_id.get(family_id, {}),
                missing_references,
            )
        )

    issues.sort(key=issue_sort_key)
    configuration_findings = build_configuration_findings(quality)

    return {
        "schema_version": SCHEMA_VERSION,
        "audit_version": version,
        "generated_at": generated_at,
        "purpose": (
            "Structured local evidence for AI-assisted Home Assistant health "
            "investigation. HA Audit supplies facts and bounded classifications; "
            "the receiving AI decides what advice, if any, is appropriate."
        ),
        "interpretation_rules": [
            "Treat priority as HA Audit's evidence-based ordering, not as severity or proof of a fault.",
            "Do not treat raw occurrence count as recurrence. Use the recurrence field.",
            "LOW or VERY LOW issues can still contain useful, user-fixable configuration evidence.",
            (
                "If power_expectation is UNKNOWN, do not assume an unavailable or "
                "unreachable device should be powered. Recommend checking it only "
                "while the user expects it to be on."
            ),
            (
                "Do not recommend destructive cleanup solely from unavailable, unknown, "
                "not-currently-provided, or missing-history evidence."
            ),
            "If evidence is insufficient, identify what is missing rather than inventing a root cause.",
        ],
        "privacy": {
            "network_addresses_redacted_in_messages": True,
            "installation_specific_names_and_entity_ids_may_be_present": True,
            "external_transmission_performed": False,
        },
        "source_status": {
            "audit_snapshot": bool(audit),
            "quality_audit": bool(quality),
            "log_issue_families": bool(log_families),
            "log_priority_final": bool(log_priority_final),
            "log_correlation": bool(log_correlation),
        },
        "system": build_system_context(audit),
        "configuration_findings": configuration_findings,
        "system_issues": issues,
        "summary": {
            "system_issue_count": len(issues),
            "configuration_missing_entity_reference_count": len(
                configuration_findings["missing_entity_references"]
            ),
            "issues_with_representative_messages": sum(
                1 for item in issues if item["representative_messages"]
            ),
            "device_local_issues_with_unknown_power_expectation": sum(
                1
                for item in issues
                if item["availability_context"]["power_expectation"] == "UNKNOWN"
                and str(item.get("ownership", "")).upper() == "DEVICE / LOCAL NETWORK"
            ),
        },
    }


def main():
    report = build_ai_evidence(
        audit=load_json_optional(AUDIT_FILE),
        quality=load_json_optional(QUALITY_FILE),
        log_families=load_json_optional(LOG_FAMILY_FILE),
        log_priority_final=load_json_optional(LOG_PRIORITY_FINAL_FILE),
        log_correlation=load_json_optional(LOG_CORRELATION_FILE),
    )
    write_json(OUTPUT_FILE, report)


if __name__ == "__main__":
    main()
