from copy import deepcopy

from log_fingerprint_scan import (
    build_report,
    fingerprint_family,
)


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def fallback_family(
    family_id,
    logger,
    source,
    messages,
):
    return {
        "family_id": family_id,
        "title": (
            "Unclassified System Log entry"
        ),
        "grouping_method": (
            "single_entry_fallback"
        ),
        "rule_id": None,
        "source_entry_count": 1,
        "occurrence_count": 1,
        "level_occurrences": {
            "WARNING": 1,
        },
        "first_seen": (
            "2026-10-07T10:00:00+00:00"
        ),
        "last_seen": (
            "2026-10-07T10:00:00+00:00"
        ),
        "logger_names": [
            logger
        ],
        "sources": [
            source
        ],
        "message_samples": messages,
        "members": [
            {
                "source_entry_index": 10,
                "level": "WARNING",
                "count": 1,
            }
        ],
    }


def deterministic_family(
    family_id,
):
    return {
        "family_id": family_id,
        "title": family_id,
        "grouping_method": (
            "deterministic_rule"
        ),
        "rule_id": family_id,
        "source_entry_count": 1,
        "occurrence_count": 10,
        "logger_names": [
            "example.logger"
        ],
        "sources": [
            "example.py:10"
        ],
        "message_samples": [
            "Example message"
        ],
    }


def fingerprint(
    family,
):
    return fingerprint_family(
        family
    )[
        "stable_fingerprint"
    ]


def main():
    template_a = fallback_family(
        "unclassified_old_hash",
        (
            "homeassistant.components."
            "template.validators"
        ),
        (
            "components/template/"
            "validators.py:39"
        ),
        [
            (
                "Received invalid sensor state: "
                "unknown for entity "
                "sensor.ashp_flow_temp, "
                "expected a number"
            )
        ],
    )

    template_b = deepcopy(
        template_a
    )

    template_b[
        "family_id"
    ] = "unclassified_new_hash"

    template_b[
        "occurrence_count"
    ] = 27

    template_b[
        "first_seen"
    ] = (
        "2026-10-09T06:00:00+00:00"
    )

    template_b[
        "last_seen"
    ] = (
        "2026-10-09T07:00:00+00:00"
    )

    template_b[
        "sources"
    ] = [
        (
            "components/template/"
            "validators.py:42"
        )
    ]

    template_b[
        "message_samples"
    ] = [
        (
            "Received invalid sensor state: "
            "unavailable for entity "
            "sensor.ashp_flow_temp, "
            "expected a number"
        )
    ]

    template_b[
        "members"
    ][0][
        "source_entry_index"
    ] = 47

    require(
        fingerprint(
            template_a
        )
        == fingerprint(
            template_b
        ),
        (
            "Template fingerprint changed "
            "because of transient family ID, "
            "count, time, source line, state "
            "value or source-entry index."
        ),
    )

    template_other_entity = (
        deepcopy(
            template_a
        )
    )

    template_other_entity[
        "message_samples"
    ] = [
        (
            "Received invalid sensor state: "
            "unknown for entity "
            "sensor.other_temperature, "
            "expected a number"
        )
    ]

    require(
        fingerprint(
            template_a
        )
        != fingerprint(
            template_other_entity
        ),
        (
            "Different template entities "
            "were incorrectly merged."
        ),
    )

    websocket_a = fallback_family(
        "unclassified_ws_a",
        (
            "homeassistant.components."
            "websocket_api.http.connection"
        ),
        (
            "components/websocket_api/"
            "http.py:569"
        ),
        [
            (
                "[2696600861104] jack from "
                "127.0.0.1 "
                "(Home Assistant/2026.9.1 "
                "(io.robbie.HomeAssistant; "
                "build:2026.2985; iOS 27.0.1)): "
                "Disconnected: Received error "
                "message during command phase: "
                "No PONG received after "
                "27.5 seconds"
            )
        ],
    )

    websocket_b = fallback_family(
        "unclassified_ws_b",
        (
            "homeassistant.components."
            "websocket_api.http.connection"
        ),
        (
            "components/websocket_api/"
            "http.py:601"
        ),
        [
            (
                "[9912345678901] luke from "
                "192.168.1.99 "
                "(Home Assistant/2026.10.3 "
                "(io.robbie.HomeAssistant; "
                "build:2026.3100; iOS 27.1)): "
                "Disconnected: Received error "
                "message during command phase: "
                "No PONG received after "
                "31.0 seconds"
            )
        ],
    )

    require(
        fingerprint(
            websocket_a
        )
        == fingerprint(
            websocket_b
        ),
        (
            "WebSocket heartbeat fingerprint "
            "changed because of client, IP, "
            "version, connection ID, duration "
            "or source line."
        ),
    )

    already_running_a = (
        fallback_family(
            "unclassified_running_a",
            (
                "homeassistant.components."
                "automation.tv_lr_volume"
            ),
            "helpers/script.py:2291",
            [
                (
                    "TV - LR - Volume/Source: "
                    "Already running"
                )
            ],
        )
    )

    already_running_b = (
        fallback_family(
            "unclassified_running_b",
            (
                "homeassistant.components."
                "automation.tv_lr_volume"
            ),
            "helpers/script.py:2310",
            [
                (
                    "Renamed display title: "
                    "Already running"
                )
            ],
        )
    )

    require(
        fingerprint(
            already_running_a
        )
        == fingerprint(
            already_running_b
        ),
        (
            "Already-running automation "
            "fingerprint changed because "
            "of display title or source line."
        ),
    )

    other_automation = (
        deepcopy(
            already_running_a
        )
    )

    other_automation[
        "logger_names"
    ] = [
        (
            "homeassistant.components."
            "automation.other_automation"
        )
    ]

    require(
        fingerprint(
            already_running_a
        )
        != fingerprint(
            other_automation
        ),
        (
            "Different automation loggers "
            "were incorrectly merged."
        ),
    )

    reordered_a = fallback_family(
        "unclassified_order_a",
        "example.logger",
        "example/source.py:10",
        [
            "Failed item 123456789012",
            (
                "Cannot connect to "
                "192.168.0.20"
            ),
        ],
    )

    reordered_a[
        "logger_names"
    ] = [
        "example.logger.two",
        "example.logger",
    ]

    reordered_a[
        "sources"
    ] = [
        "example/other.py:22",
        "example/source.py:10",
    ]

    reordered_b = deepcopy(
        reordered_a
    )

    reordered_b[
        "logger_names"
    ].reverse()

    reordered_b[
        "sources"
    ].reverse()

    reordered_b[
        "message_samples"
    ].reverse()

    require(
        fingerprint(
            reordered_a
        )
        == fingerprint(
            reordered_b
        ),
        (
            "Fingerprint changed because "
            "evidence ordering changed."
        ),
    )

    zigbee_a = deterministic_family(
        "zigbee_delivery"
    )

    zigbee_b = deepcopy(
        zigbee_a
    )

    zigbee_b[
        "occurrence_count"
    ] = 999

    zigbee_b[
        "logger_names"
    ] = [
        "completely.different.logger"
    ]

    zigbee_b[
        "message_samples"
    ] = [
        "Completely different sample"
    ]

    require(
        fingerprint(
            zigbee_a
        )
        == fingerprint(
            zigbee_b
        ),
        (
            "Deterministic family "
            "fingerprint should depend "
            "on its rule identity."
        ),
    )

    require(
        fingerprint(
            zigbee_a
        )
        != fingerprint(
            deterministic_family(
                "apple_tv"
            )
        ),
        (
            "Different deterministic "
            "families share a fingerprint."
        ),
    )

    duplicate_template = deepcopy(
        template_a
    )

    duplicate_template[
        "family_id"
    ] = "unclassified_duplicate"

    report = build_report(
        {
            "source_collection": {
                "status": "ok",
                "error": None,
            },
            "families": [
                template_a,
                duplicate_template,
                websocket_a,
                already_running_a,
                zigbee_a,
            ],
        }
    )

    require(
        report[
            "summary"
        ][
            "family_count"
        ] == 5,
        (
            "Unexpected family count."
        ),
    )

    require(
        report[
            "summary"
        ][
            "stable_fingerprint_count"
        ] == 4,
        (
            "Distinct fingerprint count "
            "is incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "duplicate_fingerprint_group_count"
        ] == 1,
        (
            "Duplicate fingerprint group "
            "was not detected."
        ),
    )

    require(
        report[
            "scope"
        ][
            "history_written"
        ]
        is False,
        (
            "Fingerprint probe must not "
            "write history."
        ),
    )

    require(
        report[
            "scope"
        ][
            "persistence_judgement_produced"
        ]
        is False,
        (
            "Fingerprint probe must not "
            "produce persistence judgement."
        ),
    )

    for record in report[
        "families"
    ]:
        require(
            record[
                "stable_fingerprint"
            ].startswith(
                "lfp_"
            ),
            (
                "Stable fingerprint prefix "
                "is missing."
            ),
        )

        require(
            "message_samples"
            not in record,
            (
                "Raw message evidence leaked "
                "into fingerprint output."
            ),
        )

        require(
            "sources"
            not in record,
            (
                "Raw source evidence leaked "
                "into fingerprint output."
            ),
        )

        require(
            "logger_names"
            not in record,
            (
                "Raw logger evidence leaked "
                "into fingerprint output."
            ),
        )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG FINGERPRINT TEST"
    )
    print("=" * 62)
    print(
        "Transient family ID ignored:  PASS"
    )
    print(
        "Counts/timestamps ignored:    PASS"
    )
    print(
        "Source line ignored:          PASS"
    )
    print(
        "Source entry index ignored:   PASS"
    )
    print(
        "WebSocket volatility removed: PASS"
    )
    print(
        "Template state normalized:    PASS"
    )
    print(
        "Entity distinction retained:  PASS"
    )
    print(
        "Automation identity retained: PASS"
    )
    print(
        "Evidence ordering stable:     PASS"
    )
    print(
        "Deterministic rules stable:   PASS"
    )
    print(
        "Duplicate detection:          PASS"
    )
    print(
        "No history written:           PASS"
    )
    print(
        "No raw evidence persisted:    PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
