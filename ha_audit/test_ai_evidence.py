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


def link_by_type(issue, link_type):
    for item in issue.get(
        "configuration_links",
        [],
    ):
        if item.get(
            "link_type"
        ) == link_type:
            return item

    raise AssertionError(
        f"Missing configuration link: {link_type}"
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
            "source_index": [
                {
                    "id": "123",
                    "alias": "Hue Switch - Bedroom",
                    "source": "automations.yaml",
                    "line": 120,
                    "entity_id": "automation.hue_switch_bedroom",
                    "live_state": "on",
                    "currently_on": True,
                }
            ],
        },
        "scripts": {
            "duplicate_aliases": {},
            "source_index": [
                {
                    "key": "dim_to_off_kitchen",
                    "entity_id": "script.dim_to_off_kitchen",
                    "alias": "Dim to Off - Kitchen",
                    "source": "scripts.yaml",
                    "line": 900,
                }
            ],
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
            "locations_by_entity": {
                "light.kitchen_1": [
                    {
                        "file": "scripts.yaml",
                        "lines": [914],
                    }
                ],
                "sensor.old_watch_battery": [
                    {
                        "file": "entities/template/watch.yaml",
                        "lines": [42, 43],
                    },
                    {
                        "file": "automations.yaml",
                        "lines": [578],
                    },
                ],
            },
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
                    "homeassistant.components.script.dim_to_off_kitchen",
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
                "ownership": "USER / LOCAL CONFIGURATION",
                "ownership_confidence": "MEDIUM",
                "local_action_path": "LOCAL INVESTIGATION",
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
        report["schema_version"] == 2,
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
        "script.dim_to_off_kitchen"
        in zigbee["affected_scripts"],
        "Script logger context was not extracted.",
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

    automation_link = link_by_type(
        zigbee,
        "AUTOMATION_SOURCE",
    )

    require(
        automation_link["source"] == "automations.yaml"
        and automation_link["line"] == 120,
        "Automation source was not linked from quality evidence.",
    )

    script_link = link_by_type(
        zigbee,
        "SCRIPT_SOURCE",
    )

    require(
        script_link["source"] == "scripts.yaml"
        and script_link["line"] == 900,
        "Script source was not linked from quality evidence.",
    )

    entity_link = next(
        item
        for item in zigbee["configuration_links"]
        if item.get("entity_id") == "light.kitchen_1"
    )

    require(
        entity_link["locations"][0]["file"] == "scripts.yaml"
        and entity_link["locations"][0]["lines"] == [914],
        "Active YAML entity reference was not linked.",
    )

    require(
        entity_link["causal_link_established"] is False,
        "Entity-reference link incorrectly claims causality.",
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

    template_link = next(
        item
        for item in template["configuration_links"]
        if item.get("entity_id") == "sensor.old_watch_battery"
    )

    require(
        len(template_link["locations"]) == 2,
        "Full active-YAML source index was not used for template evidence.",
    )

    require(
        template_link["missing_entity_reference"] is True,
        "Missing-reference context was not preserved on the source link.",
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
        report["summary"]["issues_with_configuration_links"] == 2,
        "Configuration-link summary count is wrong.",
    )

    require(
        "action_recommendation"
        not in powered_off,
        "Evidence layer emitted an action recommendation.",
    )

    # v0.8.2: receiving AIs should get facts in ordinary language,
    # without invented root causes, generic clean-up, or power assumptions.
    briefing = report["assistant_briefing"]
    require(
        briefing["detail_levels"]["user"].startswith("Plain English"),
        "User-facing guidance is missing.",
    )
    require(
        len(briefing["response_sequence"]) >= 4,
        "The receiving AI lacks a concrete response plan.",
    )
    require(
        "at least 24 hours" in zigbee["reader_summary"]["recurrence"],
        "Durable recurrence was not explained plainly.",
    )
    require(
        "not proven causes" in zigbee["reader_summary"]["configuration_context"],
        "YAML links were mistaken for proven causes.",
    )
    require(
        "switch.spare_room_plug" in powered_off["reader_summary"]["referenced_objects"],
        "Availability target was lost from reader summary.",
    )
    require(
        "expected offline" in powered_off["reader_summary"]["uncertainty"],
        "Expected-offline safeguard was not explained.",
    )
    require(
        "(and -" not in template["reader_summary"]["referenced_objects"],
        "Reader summary contains a negative number of additional objects.",
    )
    require(
        "not established" in template["reader_summary"]["observed"],
        "An unclassified template warning was incorrectly called a proven failure.",
    )
    require(
        "Recurrence across 24 hours was not established" in template["reader_summary"]["recurrence"],
        "Unproven recurrence was promoted based on raw count.",
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
