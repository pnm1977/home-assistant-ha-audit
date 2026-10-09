from copy import deepcopy

from log_persistence_scan import (
    ACTIVITY_BASELINE,
    ACTIVITY_NEW,
    ACTIVITY_NOT_PRESENT,
    ACTIVITY_RETAINED,
    build_update,
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
    count,
    first_seen,
    last_seen,
):
    return {
        "family_id": family_id,
        "title": family_id,
        "occurrence_count": count,
        "first_seen": first_seen,
        "last_seen": last_seen,
    }


def fingerprint(
    family_id,
    value,
):
    return {
        "family_id": family_id,
        "stable_fingerprint": value,
        "fingerprint_method": (
            "deterministic_rule_v1"
        ),
    }


def priority(
    family_id,
    value,
):
    return {
        "family_id": family_id,
        "priority": value,
    }


def reports(
    families,
    fingerprints,
    priorities,
):
    return (
        {
            "source_collection": {
                "status": "ok",
                "error": None,
            },
            "families": families,
        },
        {
            "scope": {
                "fingerprint_schema_version": 1,
            },
            "source_collection": {
                "status": "ok",
                "error": None,
            },
            "summary": {
                (
                    "duplicate_fingerprint_"
                    "group_count"
                ): 0,
            },
            "families": fingerprints,
        },
        {
            "source_status": {
                "family_status": "ok",
                "ownership_status": "ok",
            },
            "families": priorities,
        },
    )


def by_fingerprint(
    history,
    value,
):
    return history[
        "records"
    ][
        value
    ]


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
            f"Expected one report record "
            f"for {family_id}."
        ),
    )

    return matches[
        0
    ]


def main():
    (
        family_report,
        fingerprint_report,
        priority_report,
    ) = reports(
        [
            family(
                "alpha",
                10,
                (
                    "2026-10-09T08:00:00+00:00"
                ),
                (
                    "2026-10-09T08:10:00+00:00"
                ),
            ),
            family(
                "beta",
                5,
                (
                    "2026-10-09T08:05:00+00:00"
                ),
                (
                    "2026-10-09T08:15:00+00:00"
                ),
            ),
        ],
        [
            fingerprint(
                "alpha",
                "lfp_alpha",
            ),
            fingerprint(
                "beta",
                "lfp_beta",
            ),
        ],
        [
            priority(
                "alpha",
                "HIGH",
            ),
            priority(
                "beta",
                "LOW",
            ),
        ],
    )

    (
        history_1,
        report_1,
        ready_1,
    ) = build_update(
        family_report,
        fingerprint_report,
        priority_report,
        None,
        (
            "2026-10-09T08:30:00+00:00"
        ),
    )

    require(
        ready_1,
        "First history write not ready.",
    )

    require(
        history_1[
            "run_sequence"
        ] == 1,
        (
            "First run sequence "
            "incorrect."
        ),
    )

    require(
        by_family(
            report_1,
            "alpha",
        )[
            "activity_since_previous_audit"
        ]
        == ACTIVITY_BASELINE,
        (
            "First observation must "
            "be BASELINE."
        ),
    )

    alpha_1 = by_fingerprint(
        history_1,
        "lfp_alpha",
    )

    require(
        alpha_1[
            "repeat_activity_audits"
        ] == 0,
        (
            "Baseline must not count "
            "as repeat activity."
        ),
    )

    (
        history_2,
        report_2,
        ready_2,
    ) = build_update(
        family_report,
        fingerprint_report,
        priority_report,
        history_1,
        (
            "2026-10-09T09:00:00+00:00"
        ),
    )

    require(
        ready_2,
        "Second history write not ready.",
    )

    alpha_2 = by_fingerprint(
        history_2,
        "lfp_alpha",
    )

    require(
        alpha_2[
            "audit_appearances"
        ] == 2,
        (
            "Audit appearance count "
            "incorrect."
        ),
    )

    require(
        alpha_2[
            "consecutive_audit_appearances"
        ] == 2,
        (
            "Consecutive appearance count "
            "incorrect."
        ),
    )

    require(
        alpha_2[
            "last_activity_status"
        ]
        == ACTIVITY_RETAINED,
        (
            "Unchanged System Log evidence "
            "must be RETAINED EVIDENCE."
        ),
    )

    require(
        alpha_2[
            "repeat_activity_audits"
        ] == 0,
        (
            "Repeated audit of unchanged "
            "evidence falsely counted as "
            "recurrence."
        ),
    )

    family_report_3 = deepcopy(
        family_report
    )

    for item in family_report_3[
        "families"
    ]:
        if item[
            "family_id"
        ] == "beta":
            item[
                "occurrence_count"
            ] = 9

            item[
                "last_seen"
            ] = (
                "2026-10-09T09:15:00+00:00"
            )

    (
        history_3,
        report_3,
        ready_3,
    ) = build_update(
        family_report_3,
        fingerprint_report,
        priority_report,
        history_2,
        (
            "2026-10-09T09:30:00+00:00"
        ),
    )

    require(
        ready_3,
        "Third history write not ready.",
    )

    beta_3 = by_fingerprint(
        history_3,
        "lfp_beta",
    )

    require(
        beta_3[
            "last_activity_status"
        ]
        == ACTIVITY_NEW,
        (
            "Advanced log evidence was "
            "not detected as NEW ACTIVITY."
        ),
    )

    require(
        beta_3[
            "repeat_activity_audits"
        ] == 1,
        (
            "Repeat activity counter "
            "incorrect."
        ),
    )

    require(
        beta_3[
            "consecutive_new_activity_audits"
        ] == 1,
        (
            "First new-activity streak "
            "should be 1."
        ),
    )

    family_report_4 = deepcopy(
        family_report_3
    )

    for item in family_report_4[
        "families"
    ]:
        if item[
            "family_id"
        ] == "beta":
            item[
                "occurrence_count"
            ] = 14

            item[
                "last_seen"
            ] = (
                "2026-10-09T09:45:00+00:00"
            )

    (
        history_4,
        report_4,
        ready_4,
    ) = build_update(
        family_report_4,
        fingerprint_report,
        priority_report,
        history_3,
        (
            "2026-10-09T10:00:00+00:00"
        ),
    )

    require(
        ready_4,
        "Fourth history write not ready.",
    )

    beta_4 = by_fingerprint(
        history_4,
        "lfp_beta",
    )

    require(
        beta_4[
            "repeat_activity_audits"
        ] == 2,
        (
            "Second repeat activity "
            "was not accumulated."
        ),
    )

    require(
        beta_4[
            "consecutive_new_activity_audits"
        ] == 2,
        (
            "Consecutive new-activity "
            "streak should be 2."
        ),
    )

    family_report_5 = deepcopy(
        family_report_4
    )

    family_report_5[
        "families"
    ] = [
        item
        for item in family_report_5[
            "families"
        ]
        if item[
            "family_id"
        ] != "alpha"
    ]

    fingerprint_report_5 = deepcopy(
        fingerprint_report
    )

    fingerprint_report_5[
        "families"
    ] = [
        item
        for item in fingerprint_report_5[
            "families"
        ]
        if item[
            "family_id"
        ] != "alpha"
    ]

    priority_report_5 = deepcopy(
        priority_report
    )

    priority_report_5[
        "families"
    ] = [
        item
        for item in priority_report_5[
            "families"
        ]
        if item[
            "family_id"
        ] != "alpha"
    ]

    (
        history_5,
        report_5,
        ready_5,
    ) = build_update(
        family_report_5,
        fingerprint_report_5,
        priority_report_5,
        history_4,
        (
            "2026-10-09T10:30:00+00:00"
        ),
    )

    require(
        ready_5,
        "Fifth history write not ready.",
    )

    alpha_5 = by_fingerprint(
        history_5,
        "lfp_alpha",
    )

    require(
        alpha_5[
            "seen_in_latest_audit"
        ]
        is False,
        (
            "Missing historical family "
            "still marked present."
        ),
    )

    require(
        alpha_5[
            "last_activity_status"
        ]
        == ACTIVITY_NOT_PRESENT,
        (
            "Missing historical family "
            "status incorrect."
        ),
    )

    require(
        alpha_5[
            "missed_audits_since_seen"
        ] == 1,
        (
            "Missed-audit counter "
            "incorrect."
        ),
    )

    require(
        alpha_5[
            "consecutive_audit_appearances"
        ] == 0,
        (
            "Missing family retained its "
            "appearance streak."
        ),
    )

    bad_fingerprint_report = deepcopy(
        fingerprint_report
    )

    bad_fingerprint_report[
        "families"
    ] = bad_fingerprint_report[
        "families"
    ][
        :-1
    ]

    (
        bad_history,
        bad_report,
        bad_ready,
    ) = build_update(
        family_report,
        bad_fingerprint_report,
        priority_report,
        history_1,
        (
            "2026-10-09T11:00:00+00:00"
        ),
    )

    require(
        bad_ready
        is False,
        (
            "Misaligned inputs were "
            "allowed to write history."
        ),
    )

    require(
        bad_history is None,
        (
            "Misaligned inputs produced "
            "replacement history."
        ),
    )

    require(
        bad_report[
            "status"
        ] == "alignment_error",
        (
            "Misaligned input status "
            "incorrect."
        ),
    )

    history_text = str(
        history_5
    ).lower()

    require(
        "message_samples"
        not in history_text,
        (
            "Raw message evidence leaked "
            "into history."
        ),
    )

    require(
        "logger_names"
        not in history_text,
        (
            "Raw logger evidence leaked "
            "into history."
        ),
    )

    require(
        "sources"
        not in history_text,
        (
            "Raw source evidence leaked "
            "into history."
        ),
    )

    require(
        report_5[
            "scope"
        ][
            "persistence_judgement_produced"
        ]
        is False,
        (
            "History layer produced a "
            "persistence judgement."
        ),
    )

    require(
        report_5[
            "scope"
        ][
            "priority_changed"
        ]
        is False,
        (
            "History layer altered "
            "priority."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT LOG PERSISTENCE TEST"
    )
    print("=" * 62)
    print(
        "First observation baseline:   PASS"
    )
    print(
        "Retained evidence detected:   PASS"
    )
    print(
        "No false recurrence:          PASS"
    )
    print(
        "New activity detected:        PASS"
    )
    print(
        "Repeat activity counted:      PASS"
    )
    print(
        "Activity streak counted:      PASS"
    )
    print(
        "Missing family tracked:       PASS"
    )
    print(
        "Appearance streak reset:      PASS"
    )
    print(
        "Input alignment protected:    PASS"
    )
    print(
        "No raw evidence persisted:    PASS"
    )
    print(
        "No priority change:           PASS"
    )
    print(
        "No persistence judgement:     PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
