from log_priority_evidence import (
    ACTION_CLEAR_LOCAL,
    ACTION_INVESTIGATE_LOCAL,
    ACTION_LIMITED_LOCAL,
    BREADTH_MULTIPLE,
    BREADTH_SINGLE,
    BREADTH_UNKNOWN,
    NOT_OBSERVED,
    OBSERVED,
    SPAN_MULTI_DAY,
    SPAN_SAME_DAY,
    build_report,
)


def family(
    family_id,
    title,
    count,
    first_seen,
    last_seen,
    *,
    messages=None,
    logger_names=None,
    sources=None,
    level_occurrences=None,
    source_entry_count=1,
):
    return {
        "family_id": family_id,
        "title": title,
        "grouping_method": (
            "deterministic_rule"
        ),
        "source_entry_count": (
            source_entry_count
        ),
        "occurrence_count": count,
        "level_occurrences": (
            level_occurrences
            or {
                "ERROR": count
            }
        ),
        "first_seen": first_seen,
        "last_seen": last_seen,
        "logger_names": (
            logger_names or []
        ),
        "sources": (
            sources or []
        ),
        "message_samples": (
            messages or []
        ),
    }


def ownership(
    family_id,
    domain,
    confidence,
):
    return {
        "family_id": family_id,
        "ownership": domain,
        "ownership_confidence": (
            confidence
        ),
    }


FAMILY_REPORT = {
    "source_collection": {
        "status": "ok",
        "error": None,
    },
    "families": [
        family(
            "zigbee_delivery",
            (
                "Zigbee / ZHA "
                "delivery failures"
            ),
            724,
            (
                "2026-10-02T20:00:00+00:00"
            ),
            (
                "2026-10-07T19:00:00+00:00"
            ),
            messages=[
                (
                    "Failed to send request: "
                    "device did not respond"
                ),
                (
                    "Error executing service "
                    "light.turn_on for "
                    "light.kitchen_4"
                ),
            ],
            logger_names=[
                (
                    "homeassistant.components."
                    "automation.hue_switch_pb"
                ),
                (
                    "homeassistant.components."
                    "script.dim_to_off_kitchen"
                ),
            ],
            sources=[
                "helpers/script.py:2291",
            ],
            source_entry_count=16,
        ),
        family(
            "apple_tv",
            "Apple TV connectivity",
            268,
            (
                "2026-10-02T20:00:00+00:00"
            ),
            (
                "2026-10-07T05:00:00+00:00"
            ),
            messages=[
                (
                    "Connection lost to Apple TV "
                    "\"Backroom\""
                ),
                (
                    "Connection lost to Apple TV "
                    "\"Kitchen\""
                ),
                (
                    "Connection was re-established "
                    "to device \"Backroom\""
                ),
            ],
            level_occurrences={
                "ERROR": 212,
                "WARNING": 56,
            },
            source_entry_count=3,
        ),
        family(
            "octopus_energy",
            (
                "Octopus Energy API / "
                "data retrieval"
            ),
            191,
            (
                "2026-10-02T20:00:00+00:00"
            ),
            (
                "2026-10-07T20:00:00+00:00"
            ),
            messages=[
                (
                    "Failed to retrieve new "
                    "dispatches - using cached "
                    "dispatches."
                )
            ],
            level_occurrences={
                "ERROR": 70,
                "WARNING": 121,
            },
            source_entry_count=4,
        ),
        family(
            "slow_entity_update",
            (
                "Entity updates taking "
                "over 10 seconds"
            ),
            128,
            (
                "2026-10-03T07:00:00+00:00"
            ),
            (
                "2026-10-07T19:00:00+00:00"
            ),
            messages=[
                (
                    "Update of light.kitchen_1 "
                    "is taking over 10 seconds"
                ),
                (
                    "Update of light.bathroom_1 "
                    "is taking over 10 seconds"
                ),
            ],
            level_occurrences={
                "WARNING": 128
            },
        ),
        family(
            "robovac",
            "RoboVac connectivity",
            8,
            (
                "2026-10-07T15:16:00+00:00"
            ),
            (
                "2026-10-07T15:27:00+00:00"
            ),
            messages=[
                (
                    "Update for "
                    "vacuum.robovac_upstairs "
                    "fails"
                )
            ],
            sources=[
                (
                    "custom_components/robovac/"
                    "vacuum.py:758"
                )
            ],
            source_entry_count=3,
        ),
        family(
            "music_queue_info",
            (
                "Music automation queue_info "
                "template failures"
            ),
            6,
            (
                "2026-10-07T19:19:09+00:00"
            ),
            (
                "2026-10-07T19:19:39+00:00"
            ),
            messages=[
                (
                    "Error executing script. "
                    "UndefinedError: queue_info "
                    "is undefined"
                )
            ],
            logger_names=[
                (
                    "homeassistant.components."
                    "automation.music_2_0_playlists_2"
                ),
                (
                    "homeassistant.components."
                    "script.music_2_0_playlist_action"
                ),
                (
                    "homeassistant.components."
                    "script.music_2_0_playlist_count_2"
                ),
            ],
            sources=[
                "helpers/script.py:2291",
            ],
            source_entry_count=4,
        ),
        family(
            "unclassified_ws",
            (
                "Unclassified System "
                "Log entry"
            ),
            11,
            (
                "2026-10-04T02:00:00+00:00"
            ),
            (
                "2026-10-07T02:00:00+00:00"
            ),
            messages=[
                (
                    "Client from 127.0.0.1 "
                    "disconnected: No PONG "
                    "received after 27.5 seconds"
                )
            ],
            level_occurrences={
                "WARNING": 11
            },
        ),
        family(
            "unclassified_running",
            (
                "Unclassified System "
                "Log entry"
            ),
            1,
            (
                "2026-10-07T15:23:00+00:00"
            ),
            (
                "2026-10-07T15:23:00+00:00"
            ),
            messages=[
                (
                    "TV - LR - Volume/Source: "
                    "Already running"
                )
            ],
            logger_names=[
                (
                    "homeassistant.components."
                    "automation.tv_lr_volume"
                )
            ],
            sources=[
                "helpers/script.py:2291",
            ],
            level_occurrences={
                "WARNING": 1
            },
        ),
    ],
}


OWNERSHIP_REPORT = {
    "source_collection": {
        "status": "ok",
        "error": None,
    },
    "families": [
        ownership(
            "zigbee_delivery",
            (
                "DEVICE / LOCAL NETWORK"
            ),
            "HIGH",
        ),
        ownership(
            "apple_tv",
            (
                "DEVICE / LOCAL NETWORK"
            ),
            "MEDIUM",
        ),
        ownership(
            "octopus_energy",
            "EXTERNAL SERVICE",
            "HIGH",
        ),
        ownership(
            "slow_entity_update",
            "MIXED / UNKNOWN",
            "LOW",
        ),
        ownership(
            "robovac",
            (
                "DEVICE / LOCAL NETWORK"
            ),
            "HIGH",
        ),
        ownership(
            "music_queue_info",
            (
                "USER / LOCAL CONFIGURATION"
            ),
            "HIGH",
        ),
        ownership(
            "unclassified_ws",
            (
                "DEVICE / LOCAL NETWORK"
            ),
            "LOW",
        ),
        ownership(
            "unclassified_running",
            (
                "USER / LOCAL CONFIGURATION"
            ),
            "HIGH",
        ),
    ],
}


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def by_id(
    report,
    family_id,
):
    matches = [
        item
        for item in report[
            "families"
        ]
        if item.get(
            "family_id"
        )
        == family_id
    ]

    require(
        len(
            matches
        ) == 1,
        (
            f"Expected one record for "
            f"{family_id}."
        ),
    )

    return matches[
        0
    ]


def main():
    report = build_report(
        FAMILY_REPORT,
        OWNERSHIP_REPORT,
    )

    zigbee = by_id(
        report,
        "zigbee_delivery",
    )

    require(
        zigbee[
            "observed_span_class"
        ]
        == SPAN_MULTI_DAY,
        (
            "Zigbee observed span "
            "incorrect."
        ),
    )

    require(
        "persistence_evidence"
        not in zigbee,
        (
            "Observed span must not be "
            "described as persistence."
        ),
    )

    require(
        zigbee[
            "direct_failure_evidence"
        ]
        == OBSERVED,
        (
            "Zigbee direct failure "
            "was not detected."
        ),
    )

    require(
        zigbee[
            "breadth_evidence"
        ]
        == BREADTH_MULTIPLE,
        (
            "Zigbee breadth "
            "incorrect."
        ),
    )

    require(
        "light.turn_on"
        not in zigbee[
            "observed_identifiers"
        ],
        (
            "Service name was incorrectly "
            "counted as a target."
        ),
    )

    require(
        "script.py"
        not in zigbee[
            "observed_identifiers"
        ],
        (
            "Python filename was incorrectly "
            "counted as a target."
        ),
    )

    require(
        "light.kitchen_4"
        in zigbee[
            "observed_identifiers"
        ],
        (
            "Real Zigbee target was lost."
        ),
    )

    require(
        zigbee[
            "local_action_path"
        ]
        == ACTION_INVESTIGATE_LOCAL,
        (
            "Zigbee action path "
            "incorrect."
        ),
    )

    apple_tv = by_id(
        report,
        "apple_tv",
    )

    require(
        apple_tv[
            "recovery_evidence"
        ]
        == OBSERVED,
        (
            "Apple TV recovery "
            "was not detected."
        ),
    )

    require(
        apple_tv[
            "breadth_evidence"
        ]
        == BREADTH_MULTIPLE,
        (
            "Apple TV family should retain "
            "multiple-device breadth."
        ),
    )

    octopus = by_id(
        report,
        "octopus_energy",
    )

    require(
        octopus[
            "fallback_evidence"
        ]
        == OBSERVED,
        (
            "Octopus cached fallback "
            "was not detected."
        ),
    )

    require(
        octopus[
            "local_action_path"
        ]
        == ACTION_LIMITED_LOCAL,
        (
            "Octopus action path "
            "incorrect."
        ),
    )

    slow = by_id(
        report,
        "slow_entity_update",
    )

    require(
        slow[
            "direct_failure_evidence"
        ]
        == NOT_OBSERVED,
        (
            "Slow update warning should "
            "not be promoted to a direct "
            "failure."
        ),
    )

    require(
        slow[
            "breadth_evidence"
        ]
        == BREADTH_MULTIPLE,
        (
            "Slow-update breadth "
            "incorrect."
        ),
    )

    robovac = by_id(
        report,
        "robovac",
    )

    require(
        robovac[
            "breadth_evidence"
        ]
        == BREADTH_SINGLE,
        (
            "Single RoboVac should not be "
            "promoted to multiple breadth."
        ),
    )

    require(
        "vacuum.py"
        not in robovac[
            "observed_identifiers"
        ],
        (
            "RoboVac source filename was "
            "counted as a target."
        ),
    )

    music = by_id(
        report,
        "music_queue_info",
    )

    require(
        music[
            "observed_span_class"
        ]
        == SPAN_SAME_DAY,
        (
            "Music observed span "
            "incorrect."
        ),
    )

    require(
        music[
            "direct_failure_evidence"
        ]
        == OBSERVED,
        (
            "Music failure evidence "
            "missing."
        ),
    )

    require(
        music[
            "breadth_evidence"
        ]
        == BREADTH_MULTIPLE,
        (
            "Music execution paths were "
            "not recognised."
        ),
    )

    require(
        "script.py"
        not in music[
            "observed_identifiers"
        ],
        (
            "Music source filename was "
            "counted as a target."
        ),
    )

    require(
        music[
            "local_action_path"
        ]
        == ACTION_CLEAR_LOCAL,
        (
            "Music local action path "
            "incorrect."
        ),
    )

    websocket = by_id(
        report,
        "unclassified_ws",
    )

    require(
        websocket[
            "breadth_evidence"
        ]
        == BREADTH_UNKNOWN,
        (
            "Loopback WebSocket address "
            "should not create target "
            "breadth."
        ),
    )

    require(
        "127.0.0.1"
        not in websocket[
            "observed_identifiers"
        ],
        (
            "Loopback address was counted "
            "as a target."
        ),
    )

    running = by_id(
        report,
        "unclassified_running",
    )

    require(
        running[
            "breadth_evidence"
        ]
        == BREADTH_SINGLE,
        (
            "One already-running automation "
            "should have single breadth."
        ),
    )

    require(
        running[
            "observed_identifiers"
        ]
        == [
            "automation.tv_lr_volume"
        ],
        (
            "Already-running automation "
            "contains false target IDs."
        ),
    )

    require(
        report[
            "summary"
        ][
            "missing_ownership_count"
        ] == 0,
        (
            "Unexpected missing "
            "ownership record."
        ),
    )

    require(
        report[
            "summary"
        ][
            "extra_ownership_count"
        ] == 0,
        (
            "Unexpected extra "
            "ownership record."
        ),
    )

    require(
        report[
            "scope"
        ][
            "priority_produced"
        ]
        is False,
        (
            "Priority was produced."
        ),
    )

    require(
        report[
            "scope"
        ][
            "severity_produced"
        ]
        is False,
        (
            "Severity was produced."
        ),
    )

    for item in report[
        "families"
    ]:
        require(
            "priority"
            not in item,
            (
                "Evidence record contains "
                "priority."
            ),
        )

        require(
            "priority_score"
            not in item,
            (
                "Evidence record contains "
                "priority score."
            ),
        )

        require(
            "severity"
            not in item,
            (
                "Evidence record contains "
                "severity."
            ),
        )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG PRIORITY EVIDENCE TEST"
    )
    print("=" * 62)
    print(
        "Observed time span:           PASS"
    )
    print(
        "No persistence overclaim:     PASS"
    )
    print(
        "Direct failure evidence:      PASS"
    )
    print(
        "Recovery evidence:            PASS"
    )
    print(
        "Fallback evidence:            PASS"
    )
    print(
        "Breadth evidence:             PASS"
    )
    print(
        "Service IDs excluded:         PASS"
    )
    print(
        "Source filenames excluded:    PASS"
    )
    print(
        "Loopback targets excluded:    PASS"
    )
    print(
        "Ownership carried forward:   PASS"
    )
    print(
        "Local action path:            PASS"
    )
    print(
        "Input alignment checks:       PASS"
    )
    print(
        "No priority judgement:        PASS"
    )
    print(
        "No severity judgement:        PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
