from log_family_scan import build_family_report


def require(
    condition,
    message,
):
    if not condition:
        raise AssertionError(
            message
        )


def fallback_entry(
    *,
    first_seen,
    last_seen,
    message,
    name="homeassistant.components.tado.coordinator",
    level="ERROR",
    file_name="helpers/update_coordinator.py",
    line=435,
    exception=None,
):
    return {
        "level": level,
        "name": name,
        "count": 1,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "source": {
            "file": file_name,
            "line": line,
        },
        "messages": [
            message
        ],
        "exception": exception,
    }


def main():
    identical_one = fallback_entry(
        first_seen=(
            "2026-10-09T10:20:32+00:00"
        ),
        last_seen=(
            "2026-10-09T10:20:32+00:00"
        ),
        message=(
            "Unexpected error fetching tado data"
        ),
        exception=(
            "First traceback payload"
        ),
    )

    identical_two = fallback_entry(
        first_seen=(
            "2026-10-09T10:25:42+00:00"
        ),
        last_seen=(
            "2026-10-09T10:25:42+00:00"
        ),
        message=(
            "Unexpected error fetching tado data"
        ),
        exception=(
            "Different traceback payload"
        ),
    )

    distinct_message = fallback_entry(
        first_seen=(
            "2026-10-09T10:30:00+00:00"
        ),
        last_seen=(
            "2026-10-09T10:30:00+00:00"
        ),
        message=(
            "Different tado coordinator failure"
        ),
    )

    distinct_level = fallback_entry(
        first_seen=(
            "2026-10-09T10:31:00+00:00"
        ),
        last_seen=(
            "2026-10-09T10:31:00+00:00"
        ),
        message=(
            "Unexpected error fetching tado data"
        ),
        level="WARNING",
    )

    distinct_source_line = fallback_entry(
        first_seen=(
            "2026-10-09T10:32:00+00:00"
        ),
        last_seen=(
            "2026-10-09T10:32:00+00:00"
        ),
        message=(
            "Unexpected error fetching tado data"
        ),
        line=436,
    )

    report = build_family_report(
        {
            "collection": {
                "status": "ok",
                "error": None,
            },
            "entries": [
                identical_one,
                identical_two,
                distinct_message,
                distinct_level,
                distinct_source_line,
            ],
        }
    )

    families = report[
        "families"
    ]

    require(
        report[
            "summary"
        ][
            "source_entry_count"
        ] == 5,
        (
            "Source entry count changed."
        ),
    )

    require(
        len(
            families
        ) == 4,
        (
            "Equivalent fallback rows were "
            "not consolidated, or distinct "
            "evidence was over-grouped."
        ),
    )

    merged = [
        family
        for family in families
        if family.get(
            "source_entry_count"
        ) == 2
    ]

    require(
        len(
            merged
        ) == 1,
        (
            "Expected exactly one merged "
            "fallback family."
        ),
    )

    merged = merged[
        0
    ]

    require(
        merged[
            "occurrence_count"
        ] == 2,
        (
            "Merged fallback occurrence "
            "count is incorrect."
        ),
    )

    require(
        merged[
            "first_seen"
        ]
        == (
            "2026-10-09T10:20:32+00:00"
        ),
        (
            "Merged fallback first_seen "
            "is incorrect."
        ),
    )

    require(
        merged[
            "last_seen"
        ]
        == (
            "2026-10-09T10:25:42+00:00"
        ),
        (
            "Merged fallback last_seen "
            "is incorrect."
        ),
    )

    require(
        merged[
            "message_samples"
        ]
        == [
            (
                "Unexpected error fetching "
                "tado data"
            )
        ],
        (
            "Merged fallback message samples "
            "are incorrect."
        ),
    )

    require(
        report[
            "summary"
        ][
            "family_occurrence_count"
        ]
        == report[
            "summary"
        ][
            "source_occurrence_count"
        ],
        (
            "Fallback consolidation changed "
            "the total occurrence count."
        ),
    )

    print("")
    print("=" * 62)
    print(
        "HA AUDIT FALLBACK GROUPING TEST"
    )
    print("=" * 62)
    print(
        "Exception variation ignored:   PASS"
    )
    print(
        "Exact fallback rows grouped:   PASS"
    )
    print(
        "Different message separated:   PASS"
    )
    print(
        "Different level separated:     PASS"
    )
    print(
        "Different source separated:    PASS"
    )
    print(
        "Occurrence total preserved:    PASS"
    )
    print("")
    print("RESULT: PASS")
    print("=" * 62)


if __name__ == "__main__":
    main()
