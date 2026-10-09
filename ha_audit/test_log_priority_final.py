from log_priority_final import (
    DIRECT_WHOLE_DEVICE,
    NO_DIRECT_MATCH,
    NO_REPAIR_MATCH,
    NO_USABLE_HISTORY,
    RECURRING_24H,
    SHORT_WINDOW_REPEAT,
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


def priority_family(
    family_id,
    priority,
    *,
    direct="OBSERVED",
    recovery="NOT OBSERVED",
    fallback="NOT OBSERVED",
    ownership="DEVICE / LOCAL NETWORK",
    action="LOCAL INVESTIGATION",
):
    return {
        "family_id": family_id,
        "title": family_id,
        "occurrence_count": 10,
        "error_occurrences": 10,
        "warning_occurrences": 0,
        "observed_span_class": "MULTI-DAY",
        "direct_failure_evidence": direct,
        "recovery_evidence": recovery,
        "fallback_evidence": fallback,
        "breadth_evidence": "UNKNOWN",
        "ownership": ownership,
        "ownership_confidence": "HIGH",
        "local_action_path": action,
        "priority": priority,
        "priority_method": (
            "deterministic_rule_hierarchy"
        ),
        "priority_basis": "test",
        "priority_modifiers": [],
    }


def fingerprint_family(
    family_id,
):
    return {
        "family_id": family_id,
        "stable_fingerprint": (
            f"lfp_{family_id}"
        ),
    }


def recurrence_family(
    family_id,
    recurrence_class,
):
    return {
        "stable_fingerprint": (
            f"lfp_{family_id}"
        ),
        "family_id": family_id,
        "seen_in_latest_audit": True,
        "recurrence_class": (
            recurrence_class
        ),
        "recurrence_observation_span_hours": (
            30.0
            if recurrence_class
            == RECURRING_24H
            else 2.0
        ),
    }


def correlation_family(
    family_id,
    *,
    availability=NO_DIRECT_MATCH,
    history="NOT APPLICABLE",
    repair=NO_REPAIR_MATCH,
    ignored=0,
    unignored=0,
):
    return {
        "family_id": family_id,
        "availability": {
            "classification": availability,
        },
        "unavailable_history": {
            "classification": history,
        },
        "repairs": {
            "classification": repair,
            "ignored_match_count": ignored,
            "unignored_match_count": (
                unignored
            ),
        },
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
            f"Expected one record for "
            f"{family_id}."
        ),
    )

    return matches[
        0
    ]


def main():
    families = [
        priority_family(
            "short_high",
            "HIGH",
        ),
        priority_family(
            "durable_local",
            "MEDIUM",
        ),
        priority_family(
            "durable_external_low",
            "LOW",
            ownership="EXTERNAL SERVICE",
            action="LIMITED LOCAL CONTROL",
        ),
        priority_family(
            "durable_external_medium",
            "MEDIUM",
            ownership="EXTERNAL SERVICE",
            action="LIMITED LOCAL CONTROL",
        ),
        priority_family(
            "correlated_low",
            "LOW",
            ownership="MIXED / UNKNOWN",
            action="UNKNOWN",
        ),
        priority_family(
            "correlated_medium_unknown",
            "MEDIUM",
            ownership="MIXED / UNKNOWN",
            action="UNKNOWN",
        ),
        priority_family(
            "ignored_repair",
            "LOW",
        ),
        priority_family(
            "no_correlation",
            "MEDIUM",
        ),
        priority_family(
            "both_evidence",
            "LOW",
        ),
        priority_family(
            "fallback_protected",
            "LOW",
            fallback="OBSERVED",
        ),
        priority_family(
            "recovery_protected",
            "MEDIUM",
            recovery="OBSERVED",
        ),
    ]

    recurrence_classes = {
        "short_high": SHORT_WINDOW_REPEAT,
        "durable_local": RECURRING_24H,
        "durable_external_low": RECURRING_24H,
        "durable_external_medium": RECURRING_24H,
        "correlated_low": SHORT_WINDOW_REPEAT,
        "correlated_medium_unknown": (
            SHORT_WINDOW_REPEAT
        ),
        "ignored_repair": SHORT_WINDOW_REPEAT,
        "no_correlation": SHORT_WINDOW_REPEAT,
        "both_evidence": RECURRING_24H,
        "fallback_protected": RECURRING_24H,
        "recovery_protected": RECURRING_24H,
    }

    correlations = {
        "short_high": correlation_family(
            "short_high"
        ),
        "durable_local": correlation_family(
            "durable_local"
        ),
        "durable_external_low": (
            correlation_family(
                "durable_external_low"
            )
        ),
        "durable_external_medium": (
            correlation_family(
                "durable_external_medium"
            )
        ),
        "correlated_low": correlation_family(
            "correlated_low",
            availability=DIRECT_WHOLE_DEVICE,
            history=NO_USABLE_HISTORY,
        ),
        "correlated_medium_unknown": (
            correlation_family(
                "correlated_medium_unknown",
                availability=(
                    DIRECT_WHOLE_DEVICE
                ),
                history=NO_USABLE_HISTORY,
            )
        ),
        "ignored_repair": correlation_family(
            "ignored_repair",
            repair="IGNORED DOMAIN MATCH",
            ignored=1,
        ),
        "no_correlation": correlation_family(
            "no_correlation"
        ),
        "both_evidence": correlation_family(
            "both_evidence",
            availability=DIRECT_WHOLE_DEVICE,
            history=NO_USABLE_HISTORY,
        ),
        "fallback_protected": (
            correlation_family(
                "fallback_protected"
            )
        ),
        "recovery_protected": (
            correlation_family(
                "recovery_protected"
            )
        ),
    }

    priority_report = {
        "audit_version": "test",
        "scope": {
            "priority_produced": True,
        },
        "source_status": {
            "family_status": "ok",
            "ownership_status": "ok",
        },
        "families": families,
    }

    fingerprint_report = {
        "audit_version": "test",
        "scope": {
            "stable_fingerprints_produced": (
                True
            ),
        },
        "source_collection": {
            "status": "ok",
        },
        "families": [
            fingerprint_family(
                item[
                    "family_id"
                ]
            )
            for item in families
        ],
        "duplicate_fingerprint_groups": [],
    }

    recurrence_report = {
        "audit_version": "test",
        "status": "ok",
        "scope": {
            "recurrence_evidence_produced": (
                True
            ),
        },
        "families": [
            recurrence_family(
                family_id,
                recurrence_classes[
                    family_id
                ],
            )
            for family_id
            in recurrence_classes
        ],
    }

    correlation_report = {
        "audit_version": "test",
        "status": "ok",
        "scope": {
            "correlation_produced": True,
        },
        "families": list(
            correlations.values()
        ),
    }

    report = build_report(
        priority_report,
        fingerprint_report,
        recurrence_report,
        correlation_report,
    )

    require(
        report[
            "status"
        ] == "ok",
        (
            "Valid aligned sources were "
            "rejected."
        ),
    )

    require(
        by_family(
            report,
            "short_high",
        )[
            "final_priority"
        ] == "HIGH",
        (
            "Short-window recurrence changed "
            "priority."
        ),
    )

    require(
        by_family(
            report,
            "durable_local",
        )[
            "final_priority"
        ] == "HIGH",
        (
            "Durable local recurrence did not "
            "promote priority."
        ),
    )

    require(
        by_family(
            report,
            "durable_external_low",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Durable external recurrence did "
            "not receive the bounded promotion."
        ),
    )

    require(
        by_family(
            report,
            "durable_external_medium",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Limited local control incorrectly "
            "promoted an external issue to HIGH."
        ),
    )

    require(
        by_family(
            report,
            "correlated_low",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Direct whole-device unavailability "
            "with no usable history did not "
            "promote LOW to MEDIUM."
        ),
    )

    require(
        by_family(
            report,
            "correlated_medium_unknown",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Unknown action domain incorrectly "
            "promoted a correlated issue to HIGH."
        ),
    )

    require(
        by_family(
            report,
            "ignored_repair",
        )[
            "final_priority"
        ] == "LOW",
        (
            "Ignored Repair context changed "
            "priority."
        ),
    )

    require(
        by_family(
            report,
            "ignored_repair",
        )[
            "repairs"
        ][
            "effect"
        ] == "CONTEXT ONLY",
        (
            "Ignored Repair context was not "
            "preserved as context only."
        ),
    )

    require(
        by_family(
            report,
            "no_correlation",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Absence of direct correlation "
            "demoted priority."
        ),
    )

    require(
        by_family(
            report,
            "both_evidence",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Multiple enrichment signals raised "
            "priority by more than one level."
        ),
    )

    require(
        by_family(
            report,
            "fallback_protected",
        )[
            "final_priority"
        ] == "LOW",
        (
            "Durable recurrence ignored observed "
            "fallback protection."
        ),
    )

    require(
        by_family(
            report,
            "recovery_protected",
        )[
            "final_priority"
        ] == "MEDIUM",
        (
            "Durable recurrence ignored observed "
            "recovery evidence."
        ),
    )

    require(
        report[
            "summary"
        ][
            "very_high_emitted"
        ]
        is False,
        (
            "VERY HIGH was emitted without "
            "critical-impact evidence."
        ),
    )

    broken_recurrence = dict(
        recurrence_report
    )

    broken_recurrence[
        "families"
    ] = recurrence_report[
        "families"
    ][
        :-1
    ]

    misaligned = build_report(
        priority_report,
        fingerprint_report,
        broken_recurrence,
        correlation_report,
    )

    require(
        misaligned[
            "status"
        ] == "source_misaligned",
        (
            "Missing current recurrence evidence "
            "did not fail closed."
        ),
    )

    require(
        misaligned[
            "scope"
        ][
            "priority_produced"
        ]
        is False,
        (
            "Misaligned sources still produced "
            "a final priority."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT FINAL LOG PRIORITY TEST"
    )
    print("=" * 62)
    print(
        "Short-window repeat no raise:  PASS"
    )
    print(
        "Durable local repeat raises:   PASS"
    )
    print(
        "External issue capped MEDIUM:  PASS"
    )
    print(
        "Whole-device evidence raises:  PASS"
    )
    print(
        "Unknown action capped MEDIUM:  PASS"
    )
    print(
        "Ignored Repair context only:   PASS"
    )
    print(
        "No correlation no demotion:    PASS"
    )
    print(
        "Combined promotion max +1:     PASS"
    )
    print(
        "Fallback blocks repeat raise:  PASS"
    )
    print(
        "Recovery blocks repeat raise:  PASS"
    )
    print(
        "VERY HIGH remains reserved:    PASS"
    )
    print(
        "Source mismatch fails closed:  PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
