from ai_evidence import build_ai_evidence


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def by_family(report, family_id):
    for item in report.get(
        "system_issues",
        [],
    ):
        if item.get(
            "family_id"
        ) == family_id:
            return item

    raise AssertionError(
        f"Missing family: {family_id}"
    )


def main():
    audit = {
        "system": {
            "core_version": "2026.8.3",
            "supervisor_version": "2026.10.2",
            "os_version": "18.2",
            "timezone": "Europe/London",
        },
        "configuration_check": {
            "status": "ok",
            "data": {
                "result": "valid",
            },
        },
    }

    quality = {
        "configuration_tree": {
            "missing_includes": [],
            "inactive_classification": {
                "orphan_candidate": [],
            },
        },
        "automations": {
            "duplicate_id_details": {},
            "active_duplicate_aliases": {},
            "unresolved_duplicate_aliases": {},
        },
        "scripts": {
            "duplicate_aliases": {},
        },
        "entity_references": {
            "missing_candidates": [
                {
                    "entity_id": "sensor.old_watch_battery",
                    "locations": [
                        {
                            "file": "automations.yaml",
                            "lines": [578],
                        }
                    ],
                }
            ],
        },
    }

    log_families = {
        "families": [
            {
                "family_id": "zigbee_delivery",
                "title": "Zigbee / ZHA delivery failures",
                "grouping_method": "deterministic_rule",
                "occurrence_count": 20,
                "first_seen": "2026-10-17T10:00:00+00:00",
                "last_seen": "2026-10-19T10:00:00+00:00",
                "logger_names": [
                    "homeassistant.components.automation.hue_switch_bedroom",
                ],
                "sources": [
                    "components/automation/__init__.py:806",
                ],
                "message_samples": [
                    (
                        "Error executing service: entity_id=['light.kitchen_1'] "
                        "at 192.168.0.20"
                    ),
                ],
            },
            {
                "family_id": "unclassified_template",
                "title": "Unclassified System Log entry",
                "grouping_method": "single_entry_fallback",
                "occurrence_count": 470,
                "first_seen": "2026-10-17T10:00:00+00:00",
                "last_seen": "2026-10-18T10:00:00+00:00",
                "logger_names": [
                    "homeassistant.helpers.template",
                ],
                "sources": [
                    "helpers/template/__init__.py:685",
                ],
                "message_samples": [
                    (
                        "Template variable warning for "
                        "states['sensor.old_watch_battery']['last_changed']"
                    ),
                ],
            },
            {
                "family_id": "powered_off",
                "title": "Expected-offline device connectivity",
                "grouping_method": "single_entry_fallback",
                "occurrence_count": 2,
                "logger_names": [
                    "example.logger",
                ],
                "sources": [],
                "message_samples": [
                    "Cannot reach switch.spare_room_plug",
                ],
            },
        ],
    }

    log_priority_final = {
        "families": [
            {
                "stable_fingerprint": "lfp_zigbee",
                "family_id": "zigbee_delivery",
                "title": "Zigbee / ZHA delivery failures",
                "occurrence_count": 20,
                "ownership": "DEVICE / LOCAL NETWORK",
                "ownership_confidence": "HIGH",
                "local_action_path": "LOCAL INVESTIGATION",
                "direct_failure_evidence": "OBSERVED",
                "recovery_evidence": "NOT OBSERVED",
                "fallback_evidence": "NOT OBSERVED",
                "snapshot_priority": "HIGH",
                "final_priority": "HIGH",
                "recurrence": {
                    "class": "RECURRING 24H+",
                    "observation_span_hours": 48.0,
                },
            },
            {
                "stable_fingerprint": "lfp_template",
                "family_id": "unclassified_template",
                "title": "Unclassified System Log entry",
                "occurrence_count": 470,
                "ownership": "MIXED / UNKNOWN",
                "ownership_confidence": "LOW",
                "local_action_path": "UNKNOWN",
                "direct_failure_evidence": "NOT OBSERVED",
                "recovery_evidence": "NOT OBSERVED",
                "fallback_evidence": "NOT OBSERVED",
                "snapshot_priority": "LOW",
                "final_priority": "LOW",
                "recurrence": {
                    "class": "NOT ESTABLISHED",
                    "observation_span_hours": None,
                },
            },
            {
                "stable_fingerprint": "lfp_powered_off",
                "family_id": "powered_off",
                "title": "Expected-offline device connectivity",
                "occurrence_count": 2,
                "ownership": "DEVICE / LOCAL NETWORK",
                "ownership_confidence": "MEDIUM",
                "local_action_path": "LOCAL INVESTIGATION",
                "direct_failure_evidence": "OBSERVED",
                "recovery_evidence": "NOT OBSERVED",
                "fallback_evidence": "NOT OBSERVED",
                "snapshot_priority": "LOW",
                "final_priority": "LOW",
                "recurrence": {
                    "class": "NOT ESTABLISHED",
                    "observation_span_hours": None,
                },
            },
        ],
    }

    log_correlation = {
        "families": [
            {
                "family_id": "zigbee_delivery",
                "correlation_class": "NO DIRECT CORRELATION",
                "availability": {
                    "classification": "NO DIRECT MATCH",
                    "matches": [],
                },
                "repairs": {
                    "classification": "NO DOMAIN MATCH",
                    "unignored_match_count": 0,
                    "ignored_match_count": 0,
                    "matches": [],
                },
            },
            {
                "family_id": "unclassified_template",
                "correlation_class": "NO DIRECT CORRELATION",
                "availability": {
                    "classification": "NO DIRECT MATCH",
                    "matches": [],
                },
                "repairs": {
                    "classification": "NO DOMAIN MATCH",
                    "unignored_match_count": 0,
                    "ignored_match_count": 0,
                    "matches": [],
                },
            },
            {
                "family_id": "powered_off",
                "correlation_class": "DIRECT AVAILABILITY CORRELATION",
                "availability": {
                    "classification": "DIRECT AVAILABILITY MATCH",
                    "matches": [
                        {
                            "entity_id": "switch.spare_room_plug",
                            "platform": "switch",
                            "device": "Spare Room Plug",
                            "classification": "expected_offline",
                            "labels": [
                                "HA Audit - Expected Offline",
                            ],
                            "history_status": "usable_history_found",
                        }
                    ],
                },
                "repairs": {
                    "classification": "NO DOMAIN MATCH",
                    "unignored_match_count": 0,
                    "ignored_match_count": 0,
                    "matches": [],
                },
            },
        ],
    }

    report = build_ai_evidence(
        audit=audit,
        quality=quality,
        log_families=log_families,
        log_priority_final=log_priority_final,
        log_correlation=log_correlation,
        version="test",
        generated_at="2026-10-19T12:24:00+00:00",
    )

    require(
        report["schema_version"] == 1,
        "Unexpected evidence schema version.",
    )

    require(
        report["system"]["configuration_check"] == "valid",
        "Configuration check was not preserved.",
    )

    require(
        len(report["system_issues"]) == 3,
        "Not all priority levels were included.",
    )

    require(
        report["system_issues"][0]["family_id"]
        == "zigbee_delivery",
        "HIGH issue was not sorted first.",
    )

    zigbee = by_family(
        report,
        "zigbee_delivery",
    )

    require(
        "light.kitchen_1"
        in zigbee["affected_entities"],
        "Exact service target was not extracted.",
    )

    require(
        "automation.hue_switch_bedroom"
        in zigbee["affected_automations"],
        "Automation logger context was not extracted.",
    )

    require(
        "192.168.0.20"
        not in zigbee["representative_messages"][0],
        "Local IP address leaked into AI evidence.",
    )

    require(
        "<IP_ADDRESS>"
        in zigbee["representative_messages"][0],
        "Local IP redaction marker is missing.",
    )

    require(
        zigbee["availability_context"]["power_expectation"]
        == "UNKNOWN",
        "Unlabelled connectivity issue inferred a power expectation.",
    )

    template = by_family(
        report,
        "unclassified_template",
    )

    require(
        template["priority"] == "LOW",
        "LOW issue priority changed unexpectedly.",
    )

    require(
        template["representative_messages"],
        "LOW issue lost its representative message.",
    )

    require(
        "ISSUE_NOT_CLASSIFIED"
        in template["evidence_gaps"],
        "Unclassified issue gap was not preserved.",
    )

    require(
        template["configuration_links"][0]["entity_id"]
        == "sensor.old_watch_battery",
        "System Log evidence was not linked to matching quality evidence.",
    )

    powered_off = by_family(
        report,
        "powered_off",
    )

    require(
        powered_off["availability_context"]["power_expectation"]
        == "EXPECTED_OFFLINE",
        "Explicit expected-offline context was not preserved.",
    )

    require(
        report["configuration_findings"]
        ["missing_entity_references"][0]
        ["locations"][0]["lines"]
        == [578],
        "Configuration source location was not preserved.",
    )

    require(
        "action_recommendation"
        not in powered_off,
        "Evidence layer emitted an action recommendation.",
    )

    require(
        report["privacy"]
        ["external_transmission_performed"]
        is False,
        "Evidence layer incorrectly claims external transmission.",
    )

    print(
        "AI evidence contract tests passed."
    )


if __name__ == "__main__":
    main()
