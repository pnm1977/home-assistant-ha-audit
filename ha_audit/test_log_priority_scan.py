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
            count=266,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
        ),
        item(
            "shelly_like",
            count=777,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth="UNKNOWN",
            confidence="MEDIUM",
        ),
        item(
            "apple_tv_like",
            count=335,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
            recovery="OBSERVED",
            confidence="MEDIUM",
        ),
        item(
            "hue_sparse_like",
            count=4,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
        ),
        item(
            "invalid_auth",
            count=12,
            direct="OBSERVED",
            span="MULTI-DAY",
            breadth=(
                "MULTIPLE TARGETS / PATHS"
            ),
            ownership=(
                "USER / LOCAL CONFIGURATION"
            ),
            confidence="MEDIUM",
        ),
        item(
            "octopus_like",
            count=213,
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
            count=87,
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
            count=57,
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
            count=166,
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

    require(
        by_id(
            report,
            "zigbee_like",
        )[
            "priority"
        ]
        == PRIORITY_HIGH,
        (
            "Broad repeated Zigbee-like "
            "failure should be HIGH."
        ),
    )

    require(
        by_id(
            report,
            "shelly_like",
        )[
            "priority"
        ]
        == PRIORITY_HIGH,
        (
            "Very strong repeated local "
            "failure should raise MEDIUM "
            "to HIGH."
        ),
    )

    require(
        by_id(
            report,
            "apple_tv_like",
        )[
            "priority"
        ]
        == PRIORITY_MEDIUM,
        (
            "Observed recovery should "
            "reduce HIGH to MEDIUM."
        ),
    )

    require(
        by_id(
            report,
            "hue_sparse_like",
        )[
            "priority"
        ]
        == PRIORITY_MEDIUM,
        (
            "Sparse log-only evidence "
            "must not reach HIGH."
        ),
    )

    require(
        by_id(
            report,
            "invalid_auth",
        )[
            "priority"
        ]
        == PRIORITY_MEDIUM,
        (
            "Authentication failures "
            "must remain MEDIUM until "
            "security evidence supports "
            "higher urgency."
        ),
    )

    require(
        by_id(
            report,
            "octopus_like",
        )[
            "priority"
        ]
        == PRIORITY_LOW,
        (
            "External service with "
            "observed fallback should "
            "be LOW."
        ),
    )

    require(
        by_id(
            report,
            "music_like",
        )[
            "priority"
        ]
        == PRIORITY_MEDIUM,
        (
            "Direct local failure across "
            "multiple execution paths "
            "should be MEDIUM."
        ),
    )

    require(
        by_id(
            report,
            "lg_tv_like",
        )[
            "priority"
        ]
        == PRIORITY_HIGH,
        (
            "Multi-day direct failure "
            "with clear local action "
            "should be HIGH."
        ),
    )

    require(
        by_id(
            report,
            "slow_update_like",
        )[
            "priority"
        ]
        == PRIORITY_LOW,
        (
            "Broad multi-day warning "
            "without direct failure "
            "should remain LOW."
        ),
    )

    require(
        by_id(
            report,
            "platform_sparse_like",
        )[
            "priority"
        ]
        == PRIORITY_LOW,
        (
            "Sparse platform evidence "
            "should be capped at LOW."
        ),
    )

    require(
        by_id(
            report,
            "one_off_noise",
        )[
            "priority"
        ]
        == PRIORITY_VERY_LOW,
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
        "Strong recurrence modifier:   PASS"
    )
    print(
        "Sparse evidence restraint:    PASS"
    )
    print(
        "Authentication restraint:     PASS"
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
