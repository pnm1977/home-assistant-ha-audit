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
        "across audit runs spanning 24h+" in zigbee["reader_summary"]["recurrence"],
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




def test_specific_reader_guidance():
    from ai_evidence import build_reader_summary, issue_specific_guidance, recurrence_context

    base = {
        "direct_failure_evidence": "OBSERVED",
        "availability_context": {"power_expectation": "UNKNOWN"},
        "ownership": "DEVICE / LOCAL NETWORK",
        "recurrence": {"class": "RECURRING 24H+", "observation_span_hours": 262.77},
        "first_seen": "2026-10-19T08:00:00+00:00",
        "last_seen": "2026-10-19T09:00:00+00:00",
        "configuration_links": [],
    }

    def check(family, messages, expected, expected_check):
        item = dict(base, family_id=family, representative_messages=messages)
        observed, first_check = issue_specific_guidance(item)
        require(expected in observed, f"{family}: concrete observation missing: {observed}")
        require(expected_check in first_check, f"{family}: actionable first check missing: {first_check}")
        require("<IP_ADDRESS>" not in observed, f"{family}: address leaked into user summary")
        return item

    check("shelly", ["Error fetching Shelly EM data: a retrieval error"], "Shelly EM", "current readings")
    check("sonos", ["No recent activity and cannot reach Backroom, marking unavailable"], "Backroom", "should have been online")
    check("apple_tv", ['Connection lost to Apple TV "Kitchen"', 'Connection lost to Apple TV "Living Room (2)"'], "Kitchen and Living Room (2)", "currently available in Home Assistant")
    check("esphome", ["Can't connect to ESPHome API for everything-presence-one-d4e0cc @ <IP_ADDRESS>"], "everything-presence-one-d4e0cc", "before investigating the network")
    check("hue_sync", ["Timeout fetching Philips Hue Play HDMI Sync Box (Hue Sync - BR at <IP_ADDRESS>) data"], "Hue Sync - BR", "current status")
    check("zigbee_delivery", ["Failed to deliver packet: <TXStatus.NWK_ROUTE_DISCOVERY_FAILED: 208>"], "Zigbee commands", "callers, not the faulty devices")
    check("unclassified_sensor", ["Received invalid sensor state: unknown for entity sensor.ashp_flow_temp, expected a number"], "sensor.ashp_flow_temp", "temporary unknown")
    check("unclassified_music", ["Failed to connect to ws://d5369777-music-assistant:8094/ws: Connection timeout"], "Music Assistant's WebSocket service", "add-on and integration")
    check("unclassified_hue", ["Living Room Colour 3: Error executing script: Connection timeout to host https://<IP_ADDRESS>/clip/v2/resource/light/uuid"], "Living Room Colour 3", "changing its YAML")
    check("invalid_auth", ["Login attempt or request with invalid authentication from MacBookAir.lan (<IP_ADDRESS>)."], "MacBookAir.lan", "recognise that client")
    check("ping_issue", ["Timeout error while pinging peer"], "timed out while checking", "identify the peer")
    lg = dict(base, family_id="lg_tv_off", representative_messages=["Device is off and cannot be controlled"],
              configuration_links=[{"link_type":"AUTOMATION_SOURCE","alias":"TV & Events"}])
    lg_observed, lg_check = issue_specific_guidance(lg)
    require("TV & Events tried to change the LG TV input" in lg_observed, "LG TV summary not specific")
    require("before considering a condition" in lg_check, "LG advice suggests unverified changes")

    verified = recurrence_context(base)
    require(verified["historical_verification_needed"], "Cross-run history caveat missing")
    require(verified["reported_log_timestamp_span_hours"] == 1.0, "Log timestamps were misread")
    require(verified["cross_audit_observation_span_hours"] == 262.77, "Upstream span lost")
    require("log_recurrence.json" in verified["interpretation"], "Historical verification source not named")
    longer = recurrence_context(dict(base, first_seen="2026-10-17T08:00:00+00:00"))
    require(not longer["historical_verification_needed"], "Over-24h log span incorrectly flagged")
    unknown = recurrence_context(dict(base, first_seen=None))
    require(unknown["historical_verification_needed"], "Missing timestamp silently treated as verified")
    no_cause = build_reader_summary(dict(base, family_id="unrecognised", representative_messages=[]))
    require("not established" not in no_cause["observed"], "Observed failure was incorrectly negated")
    not_failure = build_reader_summary(dict(base, family_id="unrecognised", representative_messages=[], direct_failure_evidence="NOT OBSERVED"))
    require("not established" in not_failure["observed"], "Unconfirmed failure was claimed")
    print("Issue-specific explanations and cross-audit timing tests passed.")

def test_real_world_message_variations():
    """Regression examples from the v0.8.31 live audit, with addresses redacted.

    Assertions describe directly observable faults only; they must not
    invent routing, wireless, integration or configuration root causes.
    """
    from ai_evidence import build_reader_summary, issue_specific_guidance

    base = {
        "direct_failure_evidence": "OBSERVED",
        "ownership": "DEVICE / LOCAL NETWORK",
        "availability_context": {"power_expectation": "UNKNOWN"},
        "configuration_links": [],
        "affected_entities": [],
        "recurrence": {"class": "NOT ESTABLISHED"},
    }

    def observed_for(family, messages, **extra):
        issue = dict(base, family_id=family, representative_messages=messages, **extra)
        observed, first_check = issue_specific_guidance(issue)
        summary = build_reader_summary(issue)
        require(summary["observed"] == observed, f"{family}: observation lost in reader summary")
        require(summary["first_check"] == first_check, f"{family}: check lost in reader summary")
        require("<IP_ADDRESS>" not in observed, f"{family}: address marker leaked to summary")
        return observed, first_check

    # Live messages report a light service-call error. This is not, on its
    # own, evidence of Zigbee route discovery or wireless-channel failure.
    zigbee_message = (
        "Error executing service: <ServiceCall light.turn_on "
        "(c:sample): entity_id=['light.living_room_lamp'], "
        "params=transition=1.0, brightness=255>"
    )
    observed, check = observed_for(
        "zigbee_delivery", [zigbee_message],
        affected_entities=["light.living_room_lamp", "light.kitchen_2"],
    )
    require("errors executing light commands" in observed, "Zigbee: live message not recognised")
    require("light.living_room_lamp" in observed, "Zigbee: affected entity omitted")
    require("do not identify a Zigbee routing failure" in observed, "Zigbee: causal caution missing")
    require("test one named light once" in check, "Zigbee: useful first check missing")
    require("callers, not the cause" in check, "Zigbee: automation causality assumed")

    # Preserve the original delivery-packet path, including distinct error
    # wording when direct packet-delivery evidence really is present.
    observed, check = observed_for(
        "zigbee_delivery", ["Failed to deliver packet: <TXStatus.NWK_ROUTE_DISCOVERY_FAILED: 208>"],
    )
    require("Zigbee commands" in observed and "route discovery" in observed,
            "Zigbee: existing packet-delivery guidance regressed")
    require("fresh delivery error" in check, "Zigbee: packet-delivery first check regressed")

    # A generic service error should not be rewritten as a Zigbee fault.
    observed, check = observed_for(
        "zigbee_delivery", ["Error executing service: domain=switch, service=turn_on"],
    )
    require("Home Assistant reported a failure" in observed,
            "Zigbee: unsupported message should retain the fallback")
    require(check == "", "Zigbee: unsupported message produced speculative advice")

    # v0.8.31 reported 'Error fetching', not 'Timeout fetching'.
    hue_message = (
        "Error fetching Philips Hue Play HDMI Sync Box "
        "(Hue Sync - BR at <IP_ADDRESS>) data: Error requesting data from <IP_ADDRESS>"
    )
    observed, check = observed_for("hue_sync", [hue_message])
    require("error retrieving data from Hue Sync - BR" in observed,
            "Hue Sync: real retrieval error not recognised")
    require("fresh data-retrieval errors" in check, "Hue Sync: first check missing")
    require("timed out" not in observed.lower(), "Hue Sync: generic error falsely called timeout")

    observed, check = observed_for(
        "hue_sync", ["Timeout fetching Philips Hue Play HDMI Sync Box (Hue Sync - BR at <IP_ADDRESS>) data"],
    )
    require("timed out fetching status" in observed, "Hue Sync: timeout-specific guidance regressed")
    require("new timeouts" in check, "Hue Sync: timeout follow-up missing")

    # Actual response-timeout messages identify the vacuum by name.
    robovac_message = (
        "Failed to update vacuum RoboVac Upstairs. Failure count: 2/3. "
        "Error: Timed out waiting for response to sequence number 1052502608"
    )
    observed, check = observed_for("robovac", [robovac_message])
    require("timed out waiting for a response from RoboVac Upstairs" in observed,
            "RoboVac: real timeout message not recognised")
    require("If RoboVac Upstairs should be available" in check,
            "RoboVac: expected-online safeguard missing")
    require("cause is not yet established" in check,
            "RoboVac: timeout incorrectly attributed to a network or device fault")

    observed, check = observed_for(
        "robovac", ["Failed to update vacuum RoboVac Upstairs. Failure count: 1/3. Error: Unknown"],
    )
    require("update failure for RoboVac Upstairs" in observed,
            "RoboVac: non-timeout update failure not recognised")
    require("new update failure" in check, "RoboVac: non-timeout follow-up missing")
    require("timed out" not in observed, "RoboVac: non-timeout message falsely called timeout")

    # Unsupported patterns remain cautious instead of guessing causes.
    for family in ("hue_sync", "robovac"):
        observed, check = observed_for(family, ["Unexpected generic error without a target"])
        require("Home Assistant reported a failure" in observed,
                f"{family}: unsupported message should retain the fallback")
        require(not check, f"{family}: unsupported message produced guessed advice")

    # Guard previous useful guidance from accidental changes.
    observed, check = observed_for("shelly", ["Error fetching Shelly EM data: retrieval error"])
    require("failed to retrieve data from Shelly EM" in observed and "current readings" in check,
            "Shelly: existing guidance regressed")
    observed, check = observed_for(
        "invalid_auth", ["Login attempt with invalid authentication from Mac.lan (<IP_ADDRESS>)."],
    )
    require("Mac.lan" in observed and "don't weaken authentication" in check,
            "Authentication: existing security guidance regressed")
    print("Real-world troubleshooting guidance regression tests passed.")


if __name__ == "__main__":
    main()
    test_specific_reader_guidance()
    test_real_world_message_variations()
