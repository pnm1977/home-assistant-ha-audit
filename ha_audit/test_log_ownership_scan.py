from log_ownership_scan import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    OWNER_DEVICE,
    OWNER_EXTERNAL,
    OWNER_HA,
    OWNER_UNKNOWN,
    OWNER_USER,
    build_report,
)


def family(
    family_id,
    title,
    count,
    *,
    logger_names=None,
    sources=None,
    message_samples=None,
):
    return {
        "family_id": family_id,
        "title": title,
        "grouping_method": (
            "deterministic_rule"
            if not family_id.startswith(
                "unclassified_"
            )
            else "single_entry_fallback"
        ),
        "source_entry_count": 1,
        "occurrence_count": count,
        "first_seen": (
            "2026-10-01T10:00:00+00:00"
        ),
        "last_seen": (
            "2026-10-07T10:00:00+00:00"
        ),
        "logger_names": (
            logger_names or []
        ),
        "sources": (
            sources or []
        ),
        "message_samples": (
            message_samples or []
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
        ),
        family(
            "octopus_energy",
            (
                "Octopus Energy API / "
                "data retrieval"
            ),
            185,
        ),
        family(
            "music_queue_info",
            (
                "Music automation queue_info "
                "template failures"
            ),
            6,
        ),
        family(
            "lg_tv_off",
            (
                "LG TV automation calls "
                "while the device is off"
            ),
            48,
        ),
        family(
            "missing_targets",
            (
                "Referenced entities or "
                "devices not currently "
                "available"
            ),
            136,
        ),
        family(
            "supervisor_store_reload",
            (
                "Supervisor App Store "
                "reload timeouts"
            ),
            10,
        ),
        family(
            "unclassified_ws",
            (
                "Unclassified System "
                "Log entry"
            ),
            11,
            logger_names=[
                (
                    "homeassistant.components."
                    "websocket_api.http.connection"
                )
            ],
            sources=[
                (
                    "components/websocket_api/"
                    "http.py:569"
                )
            ],
            message_samples=[
                (
                    "Disconnected: No PONG "
                    "received after 27.5 seconds"
                )
            ],
        ),
        family(
            "unclassified_template",
            (
                "Unclassified System "
                "Log entry"
            ),
            1,
            logger_names=[
                (
                    "homeassistant.components."
                    "template.validators"
                )
            ],
            sources=[
                (
                    "components/template/"
                    "validators.py:39"
                )
            ],
            message_samples=[
                (
                    "Received invalid sensor "
                    "state: unknown, expected "
                    "a number"
                )
            ],
        ),
        family(
            "unclassified_running",
            (
                "Unclassified System "
                "Log entry"
            ),
            1,
            logger_names=[
                (
                    "homeassistant.components."
                    "automation.tv_lr_volume"
                )
            ],
            message_samples=[
                (
                    "automation.tv_lr_volume: "
                    "Already running"
                )
            ],
        ),
        family(
            "unclassified_hassio",
            (
                "Unclassified System "
                "Log entry"
            ),
            2,
            logger_names=[
                (
                    "homeassistant.components."
                    "hassio.coordinator"
                )
            ],
            sources=[
                (
                    "components/hassio/"
                    "coordinator.py:1422"
                )
            ],
            message_samples=[
                (
                    "Error on Supervisor API: "
                    "Timeout connecting to "
                    "Supervisor"
                )
            ],
        ),
        family(
            "unclassified_unknown",
            (
                "Unclassified System "
                "Log entry"
            ),
            1,
            logger_names=[
                "unknown.logger"
            ],
            message_samples=[
                (
                    "Unknown unexpected "
                    "condition"
                )
            ],
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


def record_by_id(
    report,
    family_id,
):
    matches = [
        record
        for record in report[
            "families"
        ]
        if record.get(
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
            f"{family_id}, got "
            f"{len(matches)}."
        ),
    )

    return matches[
        0
    ]


def main():
    report = build_report(
        FAMILY_REPORT
    )

    zigbee = record_by_id(
        report,
        "zigbee_delivery",
    )

    require(
        zigbee[
            "ownership"
        ] == OWNER_DEVICE,
        (
            "Zigbee ownership "
            "incorrect."
        ),
    )

    require(
        zigbee[
            "ownership_confidence"
        ] == CONFIDENCE_HIGH,
        (
            "Zigbee confidence "
            "incorrect."
        ),
    )

    octopus = record_by_id(
        report,
        "octopus_energy",
    )

    require(
        octopus[
            "ownership"
        ] == OWNER_EXTERNAL,
        (
            "Octopus ownership "
            "incorrect."
        ),
    )

    music = record_by_id(
        report,
        "music_queue_info",
    )

    require(
        music[
            "ownership"
        ] == OWNER_USER,
        (
            "Music template ownership "
            "incorrect."
        ),
    )

    lg_tv = record_by_id(
        report,
        "lg_tv_off",
    )

    require(
        lg_tv[
            "ownership"
        ] == OWNER_USER,
        (
            "LG TV automation ownership "
            "incorrect."
        ),
    )

    missing = record_by_id(
        report,
        "missing_targets",
    )

    require(
        missing[
            "ownership"
        ] == OWNER_UNKNOWN,
        (
            "Missing targets should remain "
            "mixed/unknown."
        ),
    )

    require(
        missing[
            "ownership_confidence"
        ] == CONFIDENCE_LOW,
        (
            "Missing-target confidence "
            "should be LOW."
        ),
    )

    supervisor = record_by_id(
        report,
        "supervisor_store_reload",
    )

    require(
        supervisor[
            "ownership"
        ] == OWNER_HA,
        (
            "Supervisor ownership "
            "incorrect."
        ),
    )

    websocket = record_by_id(
        report,
        "unclassified_ws",
    )

    require(
        websocket[
            "ownership"
        ] == OWNER_DEVICE,
        (
            "WebSocket fallback ownership "
            "incorrect."
        ),
    )

    require(
        websocket[
            "ownership_confidence"
        ] == CONFIDENCE_LOW,
        (
            "WebSocket fallback should "
            "remain LOW confidence."
        ),
    )

    template = record_by_id(
        report,
        "unclassified_template",
    )

    require(
        template[
            "ownership"
        ] == OWNER_USER,
        (
            "Template fallback ownership "
            "incorrect."
        ),
    )

    require(
        template[
            "ownership_confidence"
        ] == CONFIDENCE_MEDIUM,
        (
            "Template fallback confidence "
            "incorrect."
        ),
    )

    running = record_by_id(
        report,
        "unclassified_running",
    )

    require(
        running[
            "ownership"
        ] == OWNER_USER,
        (
            "Already-running automation "
            "ownership incorrect."
        ),
    )

    hassio = record_by_id(
        report,
        "unclassified_hassio",
    )

    require(
        hassio[
            "ownership"
        ] == OWNER_HA,
        (
            "Hassio fallback ownership "
            "incorrect."
        ),
    )

    unknown = record_by_id(
        report,
        "unclassified_unknown",
    )

    require(
        unknown[
            "ownership"
        ] == OWNER_UNKNOWN,
        (
            "Unknown evidence should "
            "remain unresolved."
        ),
    )

    require(
        unknown[
            "ownership_confidence"
        ] == CONFIDENCE_LOW,
        (
            "Unknown evidence should have "
            "LOW confidence."
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
            "Ownership scan produced "
            "priority."
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
            "Ownership scan produced "
            "severity."
        ),
    )

    for record in report[
        "families"
    ]:
        require(
            "priority"
            not in record,
            (
                "Ownership record contains "
                "priority."
            ),
        )

        require(
            "severity"
            not in record,
            (
                "Ownership record contains "
                "severity."
            ),
        )

        require(
            "suggested_action"
            not in record,
            (
                "Ownership record contains "
                "action advice."
            ),
        )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG OWNERSHIP TEST"
    )
    print("=" * 62)
    print(
        "Zigbee device/network:        PASS"
    )
    print(
        "External service ownership:  PASS"
    )
    print(
        "Local config ownership:      PASS"
    )
    print(
        "HA platform ownership:       PASS"
    )
    print(
        "Mixed/unknown conservatism:  PASS"
    )
    print(
        "WebSocket fallback:          PASS"
    )
    print(
        "Template fallback:           PASS"
    )
    print(
        "Automation fallback:         PASS"
    )
    print(
        "Unknown fallback:            PASS"
    )
    print(
        "No priority judgement:       PASS"
    )
    print(
        "No severity judgement:       PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
