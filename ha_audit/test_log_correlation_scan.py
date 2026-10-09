from log_correlation_scan import (
    CORRELATION_AVAILABILITY,
    CORRELATION_NONE,
    CORRELATION_REPAIR,
    DIRECT_PARTIAL,
    DIRECT_WHOLE_DEVICE,
    HISTORY_NO_USABLE,
    HISTORY_SOURCE_UNAVAILABLE,
    HISTORY_USABLE,
    IGNORED_REPAIR_MATCH,
    NO_DIRECT_MATCH,
    NO_REPAIR_MATCH,
    UNIGNORED_REPAIR_MATCH,
    build_report,
)


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def family(
    family_id,
    identifiers,
):
    return {
        "family_id": family_id,
        "title": family_id,
        "occurrence_count": 10,
        "observed_identifiers": identifiers,
        "ownership": (
            "DEVICE / LOCAL NETWORK"
        ),
        "local_action_path": (
            "LOCAL INVESTIGATION"
        ),
    }


def unavailable_entity(
    entity_id,
    classification,
    device,
):
    return {
        "entity_id": entity_id,
        "name": entity_id,
        "platform": "test",
        "device_id": (
            f"device_{device}"
        ),
        "device": device,
        "area_id": None,
        "labels": [],
        "classification": (
            classification
        ),
        "device_state_summary": {
            "healthy_entity_ids": [],
            "unavailable_entity_ids": [
                entity_id
            ],
            "unknown_entity_ids": [],
            "healthy_count": 0,
            "unavailable_count": 1,
            "unknown_count": 0,
        },
    }


def history_entity(
    entity_id,
    status,
):
    return {
        "entity_id": entity_id,
        "history_status": status,
        "last_usable_state_started_at": (
            (
                "2026-10-08T08:00:00+00:00"
            )
            if status
            == "usable_history_found"
            else None
        ),
        "last_usable_state_ended_at": (
            (
                "2026-10-08T09:00:00+00:00"
            )
            if status
            == "usable_history_found"
            else None
        ),
    }


def repair(
    domain,
    ignored,
    severity="warning",
    translation_key="test_issue",
):
    return {
        "domain": domain,
        "issue_domain": None,
        "issue_id": (
            "private_issue_id_"
            "192.168.1.20"
        ),
        "severity": severity,
        "is_fixable": False,
        "ignored": ignored,
        "translation_key": (
            translation_key
        ),
        "translation_placeholders": {
            "ip_address": (
                "192.168.1.20"
            ),
            "account_id": (
                "PRIVATE"
            ),
        },
        "learn_more_url": (
            "https://example.invalid/"
        ),
        "upgrade_relevance": (
            "no_break_version"
        ),
    }


def by_family(
    report,
    family_id,
):
    matches = [
        item
        for item in report[
            "families"
        ]
        if item[
            "family_id"
        ]
        == family_id
    ]

    require(
        len(
            matches
        ) == 1,
        (
            f"Expected one family "
            f"record for {family_id}."
        ),
    )

    return matches[
        0
    ]


def main():
    observed_at = (
        "2026-10-09T10:00:00+00:00"
    )

    priority_report = {
        "source_status": {
            "family_status": "ok",
            "ownership_status": "ok",
        },
        "families": [
            family(
                "missing_targets",
                [
                    "media_player.one",
                    "media_player.two",
                    "script.not_availability",
                ],
            ),
            family(
                "partial_case",
                [
                    "sensor.partial"
                ],
            ),
            family(
                "shelly",
                [],
            ),
            family(
                "octopus_energy",
                [],
            ),
            family(
                "unclassified_test",
                [
                    "automation.example"
                ],
            ),
        ],
    }

    availability_report = {
        "states_observed_at": (
            observed_at
        ),
        "entities": [
            unavailable_entity(
                "media_player.one",
                (
                    "whole_device_"
                    "unavailable_unlabelled"
                ),
                "One",
            ),
            unavailable_entity(
                "media_player.two",
                (
                    "whole_device_"
                    "unavailable_unlabelled"
                ),
                "Two",
            ),
            unavailable_entity(
                "sensor.partial",
                "partial_availability",
                "Partial Device",
            ),
        ],
    }

    history_report = {
        "source_availability_observed_at": (
            observed_at
        ),
        "history_policy": {
            "recorder_status": "ok",
        },
        "entities": [
            history_entity(
                "media_player.one",
                (
                    "history_found_"
                    "no_usable_state"
                ),
            ),
            history_entity(
                "media_player.two",
                (
                    "history_found_"
                    "no_usable_state"
                ),
            ),
            history_entity(
                "sensor.partial",
                "usable_history_found",
            ),
        ],
    }

    update_report = {
        "repairs": {
            "issues": [
                repair(
                    "shelly",
                    True,
                    severity="error",
                    translation_key=(
                        "push_update_failure"
                    ),
                ),
                repair(
                    "octopus_energy",
                    False,
                    translation_key=(
                        "service_problem"
                    ),
                ),
                repair(
                    "unrelated",
                    False,
                ),
            ],
        },
    }

    report = build_report(
        priority_report,
        availability_report,
        history_report,
        update_report,
    )

    require(
        report[
            "status"
        ] == "ok",
        (
            "Valid correlation inputs "
            "were rejected."
        ),
    )

    missing = by_family(
        report,
        "missing_targets",
    )

    require(
        missing[
            "correlation_class"
        ]
        == CORRELATION_AVAILABILITY,
        (
            "Direct unavailable targets "
            "were not correlated."
        ),
    )

    require(
        missing[
            "availability"
        ][
            "classification"
        ]
        == DIRECT_WHOLE_DEVICE,
        (
            "Whole-device unavailable "
            "match was not recognised."
        ),
    )

    require(
        missing[
            "availability"
        ][
            "exact_entity_match_count"
        ] == 2,
        (
            "Exact entity match count "
            "incorrect."
        ),
    )

    require(
        missing[
            "unavailable_history"
        ][
            "classification"
        ]
        == HISTORY_NO_USABLE,
        (
            "No-usable-history evidence "
            "was not recognised."
        ),
    )

    partial = by_family(
        report,
        "partial_case",
    )

    require(
        partial[
            "availability"
        ][
            "classification"
        ]
        == DIRECT_PARTIAL,
        (
            "Partial availability match "
            "was not recognised."
        ),
    )

    require(
        partial[
            "unavailable_history"
        ][
            "classification"
        ]
        == HISTORY_USABLE,
        (
            "Usable Recorder history "
            "was not preserved."
        ),
    )

    shelly = by_family(
        report,
        "shelly",
    )

    require(
        shelly[
            "correlation_class"
        ]
        == CORRELATION_REPAIR,
        (
            "Repair-only context was "
            "not identified."
        ),
    )

    require(
        shelly[
            "availability"
        ][
            "classification"
        ]
        == NO_DIRECT_MATCH,
        (
            "Shelly received false "
            "availability correlation."
        ),
    )

    require(
        shelly[
            "repairs"
        ][
            "classification"
        ]
        == IGNORED_REPAIR_MATCH,
        (
            "Ignored Repair domain match "
            "was not preserved."
        ),
    )

    octopus = by_family(
        report,
        "octopus_energy",
    )

    require(
        octopus[
            "repairs"
        ][
            "classification"
        ]
        == UNIGNORED_REPAIR_MATCH,
        (
            "Unignored Repair domain match "
            "was not recognised."
        ),
    )

    noise = by_family(
        report,
        "unclassified_test",
    )

    require(
        noise[
            "correlation_class"
        ]
        == CORRELATION_NONE,
        (
            "Unrelated family received "
            "false correlation."
        ),
    )

    require(
        noise[
            "repairs"
        ][
            "classification"
        ]
        == NO_REPAIR_MATCH,
        (
            "Unrelated Repair was "
            "incorrectly matched."
        ),
    )

    output_text = str(
        report
    ).lower()

    require(
        "private_issue_id"
        not in output_text,
        (
            "Repair issue ID leaked "
            "into correlation output."
        ),
    )

    require(
        "192.168.1.20"
        not in output_text,
        (
            "Repair IP address leaked "
            "into correlation output."
        ),
    )

    require(
        "private"
        not in output_text,
        (
            "Repair placeholder content "
            "leaked into correlation "
            "output."
        ),
    )

    require(
        "example.invalid"
        not in output_text,
        (
            "Repair URL leaked into "
            "correlation output."
        ),
    )

    require(
        report[
            "summary"
        ][
            "direct_availability_family_count"
        ] == 2,
        (
            "Availability family count "
            "incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "direct_unavailable_entity_match_count"
        ] == 3,
        (
            "Unavailable entity match "
            "count incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "repair_domain_family_count"
        ] == 2,
        (
            "Repair-domain family count "
            "incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "unignored_repair_match_count"
        ] == 1,
        (
            "Unignored Repair count "
            "incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "ignored_repair_match_count"
        ] == 1,
        (
            "Ignored Repair count "
            "incorrect."
        ),
    )

    require(
        report[
            "scope"
        ][
            "priority_changed"
        ]
        is False,
        (
            "Correlation layer altered "
            "priority."
        ),
    )

    misaligned_history = dict(
        history_report
    )

    misaligned_history[
        "source_availability_observed_at"
    ] = (
        "2026-10-09T09:59:00+00:00"
    )

    partial_report = build_report(
        priority_report,
        availability_report,
        misaligned_history,
        update_report,
    )

    require(
        partial_report[
            "status"
        ] == "partial",
        (
            "Misaligned Recorder evidence "
            "was not surfaced as partial."
        ),
    )

    require(
        by_family(
            partial_report,
            "missing_targets",
        )[
            "availability"
        ][
            "classification"
        ]
        == DIRECT_WHOLE_DEVICE,
        (
            "Current availability evidence "
            "was lost because history was "
            "misaligned."
        ),
    )

    require(
        by_family(
            partial_report,
            "missing_targets",
        )[
            "unavailable_history"
        ][
            "classification"
        ]
        == HISTORY_SOURCE_UNAVAILABLE,
        (
            "Misaligned history was "
            "incorrectly used."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG CORRELATION TEST"
    )
    print("=" * 62)
    print(
        "Exact availability match:     PASS"
    )
    print(
        "Whole-device correlation:     PASS"
    )
    print(
        "Partial availability:         PASS"
    )
    print(
        "No-usable history evidence:   PASS"
    )
    print(
        "Usable history preserved:     PASS"
    )
    print(
        "Ignored Repair context:       PASS"
    )
    print(
        "Unignored Repair context:     PASS"
    )
    print(
        "No fuzzy Repair matching:     PASS"
    )
    print(
        "History alignment protected:  PASS"
    )
    print(
        "Availability survives partial: PASS"
    )
    print(
        "Repair private data omitted:  PASS"
    )
    print(
        "No priority change:           PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
