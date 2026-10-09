from log_priority_scan import (
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_VERY_HIGH,
    PRIORITY_VERY_LOW,
    build_report,
)


def item(
    family_id,
    *,
    count,
    direct,
    span,
    breadth,
    recovery="NOT OBSERVED",
    fallback="NOT OBSERVED",
    ownership=(
        "DEVICE / LOCAL NETWORK"
    ),
    confidence="HIGH",
    action=(
        "LOCAL INVESTIGATION"
    ),
):
    return {
        "family_id": family_id,
        "title": family_id,
        "occurrence_count": count,
        "error_occurrences": count,
        "warning_occurrences": 0,
        "observed_span_class": span,
        "direct_failure_evidence": direct,
        "recovery_evidence": recovery,
        "fallback_evidence": fallback,
        "breadth_evidence": breadth,
        "ownership": ownership,
        "ownership_confidence": (
            confidence
        ),
        "local_action_path": action,
    }


EVIDENCE_REPORT = {
    "source_status": {
        "family_status": "ok",
        "ownership_status": "ok",
    },
    "families": [
        item(
            "zigbee_like",
            count=724,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
        ),
        item(
            "apple_tv_like",
            count=268,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
            recovery="OBSERVED",
        ),
        item(
            "octopus_like",
            count=191,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth="UNKNOWN",
            fallback="OBSERVED",
            ownership="EXTERNAL SERVICE",
            action=(
                "LIMITED LOCAL CONTROL"
            ),
        ),
        item(
            "music_like",
            count=6,
            direct="OBSERVED",
            span="SAME-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
            ownership=(
                "USER / LOCAL CONFIGURATION"
            ),
            action=(
                "CLEAR LOCAL ACTION PATH"
            ),
        ),
        item(
            "lg_tv_like",
            count=48,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "SINGLE TARGET / PATH"
            ),
            ownership=(
                "USER / LOCAL CONFIGURATION"
            ),
            action=(
                "CLEAR LOCAL ACTION PATH"
            ),
        ),
        item(
            "slow_update_like",
            count=131,
            direct="NOT OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
            ownership=(
                "MIXED / UNKNOWN"
            ),
            confidence="LOW",
            action="UNKNOWN",
        ),
        item(
            "platform_sparse_like",
            count=4,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth="UNKNOWN",
            ownership=(
                "HOME ASSISTANT PLATFORM"
            ),
            confidence="MEDIUM",
            action=(
                "PLATFORM / UPSTREAM"
            ),
        ),
        item(
            "one_off_noise",
            count=1,
            direct="NOT OBSERVED",
            span="SAME-DAY",
            breadth=(
                "SINGLE TARGET / PATH"
            ),
            ownership=(
                "USER / LOCAL CONFIGURATION"
            ),
            action=(
                "CLEAR LOCAL ACTION PATH"
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


def by_id(
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
            f"{family_id}."
        ),
    )

    return matches[
        0
    ]


def main():
    report = build_report(
        EVIDENCE_REPORT
    )

    zigbee = by_id(
        report,
        "zigbee_like",
    )

    require(
        zigbee[
            "priority"
        ] == PRIORITY_HIGH,
        (
            "Broad multi-day direct "
            "failure should be HIGH."
        ),
    )

    apple_tv = by_id(
        report,
        "apple_tv_like",
    )

    require(
        apple_tv[
            "priority"
        ] == PRIORITY_MEDIUM,
        (
            "Observed recovery should "
            "reduce HIGH to MEDIUM."
        ),
    )

    octopus = by_id(
        report,
        "octopus_like",
    )

    require(
        octopus[
            "priority"
        ] == PRIORITY_LOW,
        (
            "External service with "
            "observed fallback should "
            "be LOW."
        ),
    )

    music = by_id(
        report,
        "music_like",
    )

    require(
        music[
            "priority"
        ] == PRIORITY_MEDIUM,
        (
            "Direct local failure across "
            "multiple execution paths "
            "should be MEDIUM."
        ),
    )

    lg_tv = by_id(
        report,
        "lg_tv_like",
    )

    require(
        lg_tv[
            "priority"
        ] == PRIORITY_HIGH,
        (
            "Multi-day direct failure "
            "with clear local action "
            "should be HIGH."
        ),
    )

    slow = by_id(
        report,
        "slow_update_like",
    )

    require(
        slow[
            "priority"
        ] == PRIORITY_LOW,
        (
            "Broad multi-day warning "
            "without direct failure "
            "should remain LOW."
        ),
    )

    platform_sparse = by_id(
        report,
        "platform_sparse_like",
    )

    require(
        platform_sparse[
            "priority"
        ] == PRIORITY_LOW,
        (
            "Sparse platform evidence "
            "should be capped at LOW."
        ),
    )

    noise = by_id(
        report,
        "one_off_noise",
    )

    require(
        noise[
            "priority"
        ] == PRIORITY_VERY_LOW,
        (
            "One-off condition without "
            "direct failure should be "
            "VERY LOW."
        ),
    )

    require(
        report[
            "summary"
        ][
            "priority_counts"
        ][
            PRIORITY_VERY_HIGH
        ] == 0,
        (
            "Current log-only model "
            "must not emit VERY HIGH."
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
            "Priority scan produced "
            "severity."
        ),
    )

    for record in report[
        "families"
    ]:
        require(
            "priority_score"
            not in record,
            (
                "Numeric priority score "
                "must not be produced."
            ),
        )

        require(
            "severity"
            not in record,
            (
                "Priority record contains "
                "severity."
            ),
        )

        require(
            "suggested_action"
            not in record,
            (
                "Priority record contains "
                "action advice."
            ),
        )

    priorities = [
        record[
            "priority"
        ]
        for record in report[
            "families"
        ]
    ]

    require(
        priorities.index(
            PRIORITY_HIGH
        )
        < priorities.index(
            PRIORITY_MEDIUM
        ),
        (
            "Priority sorting is "
            "incorrect."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG PRIORITY TEST"
    )
    print("=" * 62)
    print(
        "Broad direct failure:         PASS"
    )
    print(
        "Recovery modifier:            PASS"
    )
    print(
        "Fallback modifier:            PASS"
    )
    print(
        "Clear local action path:      PASS"
    )
    print(
        "Warning-only restraint:       PASS"
    )
    print(
        "Sparse upstream restraint:    PASS"
    )
    print(
        "One-off noise restraint:      PASS"
    )
    print(
        "VERY HIGH reserved:           PASS"
    )
    print(
        "No numeric score:             PASS"
    )
    print(
        "No severity judgement:        PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
