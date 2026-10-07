from log_family_scan import (
    build_family_report,
)


def entry(
    *,
    name,
    level,
    count,
    message,
    first_seen,
    last_seen,
    file="helpers/test.py",
    line=1,
    exception="",
):
    return {
        "level": level,
        "name": name,
        "source": {
            "file": file,
            "line": line,
        },
        "count": count,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "messages": [
            message
        ],
        "exception": exception,
    }


LOG_AUDIT = {
    "collection": {
        "status": "ok",
        "error": None,
    },
    "entries": [
        entry(
            name=(
                "homeassistant.components."
                "script.dim_to_off"
            ),
            level="ERROR",
            count=100,
            message=(
                "Failed to send request: "
                "Failed to deliver packet: "
                "<TXStatus.MAC_NO_ACK: 233>"
            ),
            first_seen=(
                "2026-10-01T10:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T10:00:00+00:00"
            ),
        ),
        entry(
            name="homeassistant",
            level="ERROR",
            count=50,
            message=(
                "Task exception was never "
                "retrieved"
            ),
            exception=(
                "zigpy.exceptions.DeliveryError: "
                "Failed to deliver packet: "
                "<TXStatus.NWK_ROUTE_DISCOVERY_FAILED: 208>"
            ),
            first_seen=(
                "2026-10-02T10:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T09:00:00+00:00"
            ),
            file=(
                "components/zha/helpers.py"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "apple_tv"
            ),
            level="ERROR",
            count=40,
            message="Failed to connect",
            first_seen=(
                "2026-10-01T11:00:00+00:00"
            ),
            last_seen=(
                "2026-10-06T11:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "apple_tv"
            ),
            level="WARNING",
            count=20,
            message=(
                'Connection lost to Apple TV '
                '"Living Room"'
            ),
            first_seen=(
                "2026-10-01T12:00:00+00:00"
            ),
            last_seen=(
                "2026-10-06T12:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "custom_components."
                "octopus_energy.api_client"
            ),
            level="WARNING",
            count=30,
            message=(
                "Unable to fetch planned "
                "dispatches"
            ),
            first_seen=(
                "2026-10-01T13:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T13:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "custom_components."
                "octopus_energy.api_client"
            ),
            level="ERROR",
            count=20,
            message=(
                "Failed to retrieve intelligent "
                "dispatches"
            ),
            first_seen=(
                "2026-10-01T13:01:00+00:00"
            ),
            last_seen=(
                "2026-10-07T13:01:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "automation.music_test"
            ),
            level="ERROR",
            count=2,
            message=(
                "Error rendering data template: "
                "UndefinedError: 'queue_info' "
                "is undefined"
            ),
            first_seen=(
                "2026-10-07T14:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T14:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "script.music_test"
            ),
            level="ERROR",
            count=1,
            message=(
                "Error rendering data template: "
                "UndefinedError: 'queue_info' "
                "is undefined"
            ),
            first_seen=(
                "2026-10-07T14:01:00+00:00"
            ),
            last_seen=(
                "2026-10-07T14:01:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "automation.tv_events"
            ),
            level="ERROR",
            count=16,
            message=(
                "Error calling async_select_source "
                "for device LG webOS Smart TV: "
                "Device is off and cannot be "
                "controlled"
            ),
            first_seen=(
                "2026-10-03T15:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T15:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "http.ban"
            ),
            level="WARNING",
            count=3,
            message=(
                "Login attempt or request with "
                "invalid authentication from "
                "192.168.0.10"
            ),
            first_seen=(
                "2026-10-07T16:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T17:00:00+00:00"
            ),
        ),
        entry(
            name=(
                "homeassistant.components."
                "hassio.handler"
            ),
            level="ERROR",
            count=2,
            message=(
                "Timeout on /store/reload "
                "request"
            ),
            first_seen=(
                "2026-10-07T18:00:00+00:00"
            ),
            last_seen=(
                "2026-10-07T18:05:00+00:00"
            ),
        ),
        entry(
            name="unknown.logger",
            level="ERROR",
            count=1,
            message=(
                "Completely unrelated first "
                "unknown problem"
            ),
            first_seen=(
                "2026-10-07T18:10:00+00:00"
            ),
            last_seen=(
                "2026-10-07T18:10:00+00:00"
            ),
        ),
        entry(
            name="unknown.logger",
            level="ERROR",
            count=1,
            message=(
                "Completely unrelated second "
                "unknown problem"
            ),
            first_seen=(
                "2026-10-07T18:11:00+00:00"
            ),
            last_seen=(
                "2026-10-07T18:11:00+00:00"
            ),
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


def family_by_id(
    report,
    family_id,
):
    matches = [
        family
        for family in report[
            "families"
        ]
        if family.get(
            "family_id"
        )
        == family_id
    ]

    require(
        len(
            matches
        ) == 1,
        (
            f"Expected one family "
            f"{family_id}, got "
            f"{len(matches)}."
        ),
    )

    return matches[
        0
    ]


def main():
    report = build_family_report(
        LOG_AUDIT
    )

    require(
        report[
            "source_collection"
        ][
            "status"
        ] == "ok",
        "Source collection status lost.",
    )

    zigbee = family_by_id(
        report,
        "zigbee_delivery",
    )

    require(
        zigbee[
            "source_entry_count"
        ] == 2,
        (
            "Zigbee entries were not "
            "clustered."
        ),
    )

    require(
        zigbee[
            "occurrence_count"
        ] == 150,
        (
            "Zigbee occurrence count "
            "incorrect."
        ),
    )

    apple_tv = family_by_id(
        report,
        "apple_tv",
    )

    require(
        apple_tv[
            "source_entry_count"
        ] == 2,
        (
            "Apple TV error and warning "
            "were not clustered."
        ),
    )

    require(
        apple_tv[
            "level_occurrences"
        ][
            "ERROR"
        ] == 40,
        (
            "Apple TV ERROR occurrence "
            "count incorrect."
        ),
    )

    require(
        apple_tv[
            "level_occurrences"
        ][
            "WARNING"
        ] == 20,
        (
            "Apple TV WARNING occurrence "
            "count incorrect."
        ),
    )

    octopus = family_by_id(
        report,
        "octopus_energy",
    )

    require(
        octopus[
            "source_entry_count"
        ] == 2,
        "Octopus entries not clustered.",
    )

    music = family_by_id(
        report,
        "music_queue_info",
    )

    require(
        music[
            "source_entry_count"
        ] == 2,
        (
            "Music queue_info failures "
            "were not clustered."
        ),
    )

    lg_tv = family_by_id(
        report,
        "lg_tv_off",
    )

    require(
        lg_tv[
            "occurrence_count"
        ] == 16,
        "LG TV family count incorrect.",
    )

    invalid_auth = family_by_id(
        report,
        "invalid_auth",
    )

    require(
        invalid_auth[
            "occurrence_count"
        ] == 3,
        (
            "Invalid-auth family count "
            "incorrect."
        ),
    )

    store_reload = family_by_id(
        report,
        "supervisor_store_reload",
    )

    require(
        store_reload[
            "occurrence_count"
        ] == 2,
        (
            "Store reload family count "
            "incorrect."
        ),
    )

    unclassified = [
        family
        for family in report[
            "families"
        ]
        if family.get(
            "grouping_method"
        )
        == "single_entry_fallback"
    ]

    require(
        len(
            unclassified
        ) == 2,
        (
            "Unrelated unknown entries "
            "should remain separate."
        ),
    )

    require(
        report[
            "summary"
        ][
            "source_occurrence_count"
        ]
        == report[
            "summary"
        ][
            "family_occurrence_count"
        ],
        (
            "Clustering lost or duplicated "
            "occurrences."
        ),
    )

    require(
        report[
            "scope"
        ][
            "priority_produced"
        ]
        is False,
        "Family scan produced priority.",
    )

    require(
        report[
            "scope"
        ][
            "severity_produced"
        ]
        is False,
        "Family scan produced severity.",
    )

    require(
        report[
            "scope"
        ][
            "action_recommendation_produced"
        ]
        is False,
        (
            "Family scan produced action "
            "advice."
        ),
    )

    for family in report[
        "families"
    ]:
        require(
            "priority"
            not in family,
            (
                "Family unexpectedly contains "
                "priority."
            ),
        )

        require(
            "severity"
            not in family,
            (
                "Family unexpectedly contains "
                "severity."
            ),
        )

        require(
            "suggested_action"
            not in family,
            (
                "Family unexpectedly contains "
                "action advice."
            ),
        )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG ISSUE FAMILY TEST"
    )
    print("=" * 62)
    print(
        "Zigbee family clustering:     PASS"
    )
    print(
        "Apple TV family clustering:   PASS"
    )
    print(
        "Octopus family clustering:    PASS"
    )
    print(
        "Music template clustering:    PASS"
    )
    print(
        "LG TV family clustering:      PASS"
    )
    print(
        "Security-context grouping:    PASS"
    )
    print(
        "Transient HA grouping:        PASS"
    )
    print(
        "Unknown entries kept apart:   PASS"
    )
    print(
        "Occurrence preservation:      PASS"
    )
    print(
        "No priority judgement:        PASS"
    )
    print(
        "No severity judgement:        PASS"
    )
    print(
        "No action recommendation:     PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
