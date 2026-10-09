from log_recurrence_scan import (
    NOT_ESTABLISHED,
    RECURRING_24H,
    REPEAT_SPAN_UNKNOWN,
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


def record(
    fingerprint,
    title,
    repeat_count,
    first_audit,
    last_repeat,
    priority="MEDIUM",
    seen=True,
    activity="RETAINED EVIDENCE",
):
    return {
        "stable_fingerprint": fingerprint,
        "fingerprint_method": (
            "deterministic_rule_v1"
        ),
        "latest_family_id": title.lower(),
        "title": title,
        "first_audit_seen": first_audit,
        "last_audit_seen": (
            "2026-10-12T12:00:00+00:00"
        ),
        "last_seen_run_sequence": 4,
        "audit_appearances": 4,
        "consecutive_audit_appearances": 4,
        "missed_audits_since_seen": 0,
        "repeat_activity_audits": (
            repeat_count
        ),
        "consecutive_new_activity_audits": (
            repeat_count
        ),
        "first_repeat_activity_at": (
            last_repeat
            if repeat_count > 0
            else None
        ),
        "last_repeat_activity_at": (
            last_repeat
        ),
        "last_activity_status": activity,
        "first_log_seen": (
            "2026-10-01T00:00:00+00:00"
        ),
        "last_log_seen": (
            "2026-10-12T11:00:00+00:00"
        ),
        "latest_occurrence_count": 10,
        "latest_priority": priority,
        "seen_in_latest_audit": seen,
    }


def persistence(
    *,
    generated_at,
    run_sequence,
    current_family_count,
    status="ok",
    history_written=True,
):
    return {
        "generated_at": generated_at,
        "scope": {
            "history_written": (
                history_written
            ),
        },
        "status": status,
        "summary": {
            "run_sequence": (
                run_sequence
            ),
            "current_family_count": (
                current_family_count
            ),
        },
    }


def by_title(
    report,
    title,
):
    matches = [
        item
        for item in report[
            "families"
        ]
        if item[
            "title"
        ]
        == title
    ]

    require(
        len(
            matches
        ) == 1,
        (
            f"Expected one record "
            f"for {title}."
        ),
    )

    return matches[
        0
    ]


def main():
    updated_at = (
        "2026-10-12T12:00:00+00:00"
    )

    history = {
        "history_schema_version": 1,
        "fingerprint_schema_version": 1,
        "created_at": (
            "2026-10-09T09:00:00+00:00"
        ),
        "updated_at": updated_at,
        "run_sequence": 4,
        "last_audit_version": "test",
        "records": {
            "lfp_none": record(
                "lfp_none",
                "No Repeat",
                0,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                None,
            ),
            "lfp_short_one": record(
                "lfp_short_one",
                "One Short Repeat",
                1,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-09T09:15:00+00:00"
                ),
                activity="NEW ACTIVITY",
            ),
            "lfp_short_many": record(
                "lfp_short_many",
                "Many Short Repeats",
                5,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-09T09:45:00+00:00"
                ),
                priority="HIGH",
                activity="NEW ACTIVITY",
            ),
            "lfp_day_one": record(
                "lfp_day_one",
                "One Later Repeat",
                1,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-10T15:00:00+00:00"
                ),
                activity="NEW ACTIVITY",
            ),
            "lfp_days_many": record(
                "lfp_days_many",
                "Repeated Across Days",
                3,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-12T09:00:00+00:00"
                ),
                priority="HIGH",
                activity="NEW ACTIVITY",
            ),
            "lfp_retained_after": record(
                "lfp_retained_after",
                "Retained After Repeat",
                1,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-09T10:00:00+00:00"
                ),
                activity="RETAINED EVIDENCE",
            ),
            "lfp_historical": record(
                "lfp_historical",
                "Historical Repeat",
                2,
                (
                    "2026-10-09T09:00:00+00:00"
                ),
                (
                    "2026-10-11T09:00:00+00:00"
                ),
                seen=False,
                activity="NOT PRESENT",
            ),
            "lfp_unknown": record(
                "lfp_unknown",
                "Unknown Span",
                2,
                None,
                None,
                activity="NEW ACTIVITY",
            ),
        },
    }

    current_persistence = persistence(
        generated_at=updated_at,
        run_sequence=4,
        current_family_count=7,
    )

    report = build_report(
        history,
        current_persistence,
    )

    require(
        report[
            "status"
        ] == "ok",
        (
            "Valid current persistence/history "
            "pair was rejected."
        ),
    )

    require(
        report[
            "scope"
        ][
            "recurrence_evidence_produced"
        ]
        is True,
        (
            "Recurrence evidence not "
            "produced."
        ),
    )

    require(
        by_title(
            report,
            "No Repeat",
        )[
            "recurrence_class"
        ]
        == NOT_ESTABLISHED,
        (
            "Retained evidence incorrectly "
            "established recurrence."
        ),
    )

    require(
        by_title(
            report,
            "One Short Repeat",
        )[
            "recurrence_class"
        ]
        == SHORT_WINDOW_REPEAT,
        (
            "Short repeat incorrectly "
            "classified."
        ),
    )

    require(
        by_title(
            report,
            "Many Short Repeats",
        )[
            "recurrence_class"
        ]
        == SHORT_WINDOW_REPEAT,
        (
            "Rapid repeated audit runs "
            "incorrectly established "
            "24-hour recurrence."
        ),
    )

    require(
        by_title(
            report,
            "One Later Repeat",
        )[
            "recurrence_class"
        ]
        == RECURRING_24H,
        (
            "A genuinely later independent "
            "repeat was not recognised."
        ),
    )

    require(
        by_title(
            report,
            "Repeated Across Days",
        )[
            "recurrence_class"
        ]
        == RECURRING_24H,
        (
            "Cross-day recurrence was not "
            "recognised."
        ),
    )

    require(
        by_title(
            report,
            "Retained After Repeat",
        )[
            "recurrence_class"
        ]
        == SHORT_WINDOW_REPEAT,
        (
            "Later retained evidence "
            "incorrectly changed the "
            "recurrence class."
        ),
    )

    historical = by_title(
        report,
        "Historical Repeat",
    )

    require(
        historical[
            "recurrence_class"
        ]
        == RECURRING_24H,
        (
            "Historical recurrence evidence "
            "was lost."
        ),
    )

    require(
        historical[
            "seen_in_latest_audit"
        ]
        is False,
        (
            "Historical issue incorrectly "
            "marked current."
        ),
    )

    require(
        by_title(
            report,
            "Unknown Span",
        )[
            "recurrence_class"
        ]
        == REPEAT_SPAN_UNKNOWN,
        (
            "Unknown timestamp span was "
            "treated as proven recurrence."
        ),
    )

    require(
        by_title(
            report,
            "Many Short Repeats",
        )[
            "recurrence_observation_span_hours"
        ]
        == 0.75,
        (
            "Short observation span "
            "calculation is incorrect."
        ),
    )

    require(
        by_title(
            report,
            "Repeated Across Days",
        )[
            "recurrence_observation_span_hours"
        ]
        == 72.0,
        (
            "Multi-day observation span "
            "calculation is incorrect."
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
            "Recurrence evidence layer "
            "altered priority."
        ),
    )

    require(
        report[
            "scope"
        ][
            "action_recommendation_produced"
        ]
        is False,
        (
            "Recurrence evidence layer "
            "produced an action "
            "recommendation."
        ),
    )

    require(
        report[
            "summary"
        ][
            "current_recurrence_counts"
        ][
            SHORT_WINDOW_REPEAT
        ] == 3,
        (
            "Current short-window count "
            "incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "current_recurrence_counts"
        ][
            RECURRING_24H
        ] == 2,
        (
            "Current 24-hour recurrence "
            "count incorrect."
        ),
    )

    blocked = build_report(
        history,
        persistence(
            generated_at=updated_at,
            run_sequence=4,
            current_family_count=7,
            status="duplicate_fingerprints",
            history_written=False,
        ),
    )

    require(
        blocked[
            "status"
        ]
        == "persistence_not_current",
        (
            "Failed persistence did not "
            "block recurrence output."
        ),
    )

    require(
        blocked[
            "scope"
        ][
            "recurrence_evidence_produced"
        ]
        is False,
        (
            "Stale recurrence evidence was "
            "presented after persistence "
            "failure."
        ),
    )

    require(
        blocked[
            "families"
        ] == [],
        (
            "Blocked recurrence report "
            "still exposed stale families."
        ),
    )

    stale_time = build_report(
        history,
        persistence(
            generated_at=(
                "2026-10-12T11:59:00+00:00"
            ),
            run_sequence=4,
            current_family_count=7,
        ),
    )

    require(
        stale_time[
            "status"
        ]
        == "persistence_not_current",
        (
            "Stale persistence timestamp "
            "was accepted."
        ),
    )

    stale_sequence = build_report(
        history,
        persistence(
            generated_at=updated_at,
            run_sequence=3,
            current_family_count=7,
        ),
    )

    require(
        stale_sequence[
            "status"
        ]
        == "persistence_not_current",
        (
            "Mismatched persistence sequence "
            "was accepted."
        ),
    )

    stale_count = build_report(
        history,
        persistence(
            generated_at=updated_at,
            run_sequence=4,
            current_family_count=8,
        ),
    )

    require(
        stale_count[
            "status"
        ]
        == "persistence_not_current",
        (
            "Mismatched current-family count "
            "was accepted."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG RECURRENCE TEST"
    )
    print("=" * 62)
    print(
        "Current persistence aligned:   PASS"
    )
    print(
        "Retained evidence protected:  PASS"
    )
    print(
        "Single short repeat:          PASS"
    )
    print(
        "Rapid-run inflation blocked:  PASS"
    )
    print(
        "Later independent repeat:     PASS"
    )
    print(
        "24-hour recurrence detected:  PASS"
    )
    print(
        "Retained class preserved:     PASS"
    )
    print(
        "Historical state preserved:   PASS"
    )
    print(
        "Unknown span conservative:    PASS"
    )
    print(
        "Observation span calculated:  PASS"
    )
    print(
        "Persistence failure blocked:  PASS"
    )
    print(
        "Stale timestamp blocked:      PASS"
    )
    print(
        "Stale sequence blocked:       PASS"
    )
    print(
        "Family-count mismatch blocked: PASS"
    )
    print(
        "No priority change:           PASS"
    )
    print(
        "No action recommendation:     PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
