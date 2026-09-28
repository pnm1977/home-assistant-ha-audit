import json
import os
import re
from collections import Counter
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

COVERAGE_FILE = (
    "/config/compatibility_coverage_audit.json"
)

COMPATIBILITY_FILE = (
    "/config/upgrade_compatibility_audit.json"
)

CORRELATION_FILE = (
    "/config/upgrade_correlation_audit.json"
)

OUTPUT_FILE = (
    "/config/correlation_validation_audit.json"
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_json_optional(path):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:
            return json.load(
                handle
            )

    except Exception:
        return {}


def as_dict(value):
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def as_list(value):
    if isinstance(
        value,
        list,
    ):
        return value

    return []


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def unique(values):
    output = []
    seen = set()

    for value in values:
        value = clean(
            value
        )

        if (
            value
            and value not in seen
        ):
            seen.add(
                value
            )

            output.append(
                value
            )

    return output


def comparison_key(
    release_family,
    heading,
):
    return (
        clean(
            release_family
        ).casefold(),

        clean(
            heading
        ).casefold(),
    )


def dynamic_relevance_state(status):
    if status in {
        "strong_local_evidence",
        "local_surface_evidence",
        "partial_local_evidence",
    }:
        return (
            "local_evidence"
        )

    if status == "no_local_evidence":
        return (
            "no_local_evidence"
        )

    return (
        "unresolved"
    )


def deterministic_relevance_state(
    reference_status,
    rows,
):
    if (
        reference_status != "available"
        or not rows
    ):
        return (
            "unresolved"
        )

    local_values = [
        row.get(
            "local_match"
        )

        for row in rows
    ]

    if any(
        value is True

        for value
        in local_values
    ):
        return (
            "local_evidence"
        )

    if all(
        value is False

        for value
        in local_values
    ):
        return (
            "no_local_evidence"
        )

    return (
        "unresolved"
    )


def relevance_relationship(
    reference_status,
    deterministic_state,
    dynamic_state,
):
    if reference_status == "not_available":
        return (
            "no_deterministic_reference"
        )

    if reference_status == "incomplete":
        return (
            "deterministic_reference_incomplete"
        )

    if (
        deterministic_state
        == "local_evidence"
        and dynamic_state
        == "local_evidence"
    ):
        return (
            "aligned_local"
        )

    if (
        deterministic_state
        == "no_local_evidence"
        and dynamic_state
        == "no_local_evidence"
    ):
        return (
            "aligned_no_local"
        )

    if (
        deterministic_state
        == "local_evidence"
        and dynamic_state
        == "no_local_evidence"
    ):
        return (
            "dynamic_gap"
        )

    if (
        deterministic_state
        == "no_local_evidence"
        and dynamic_state
        == "local_evidence"
    ):
        return (
            "deterministic_gap"
        )

    return (
        "unresolved"
    )


# ------------------------------------------------------------
# Load reports
# ------------------------------------------------------------

coverage = load_json_optional(
    COVERAGE_FILE
)

compatibility = load_json_optional(
    COMPATIBILITY_FILE
)

correlation = load_json_optional(
    CORRELATION_FILE
)


coverage_groups = as_list(
    coverage.get(
        "group_coverage"
    )
)

coverage_summary = as_dict(
    coverage.get(
        "summary"
    )
)

coverage_collector = as_dict(
    coverage.get(
        "collector_status"
    )
)

compatibility_results = as_list(
    compatibility.get(
        "results"
    )
)

compatibility_summary = as_dict(
    compatibility.get(
        "summary"
    )
)

compatibility_scope = as_dict(
    compatibility.get(
        "scope"
    )
)

correlation_rows = as_list(
    correlation.get(
        "correlations"
    )
)

correlation_summary = as_dict(
    correlation.get(
        "summary"
    )
)

correlation_scope = as_dict(
    correlation.get(
        "scope"
    )
)

correlation_collector = as_dict(
    correlation.get(
        "collector_status"
    )
)


# ------------------------------------------------------------
# Build deterministic rule index
# ------------------------------------------------------------

deterministic_by_id = {}

for row in compatibility_results:
    if not isinstance(
        row,
        dict,
    ):
        continue

    rule_id = clean(
        row.get(
            "id"
        )
    )

    if rule_id:
        deterministic_by_id[
            rule_id
        ] = row


# ------------------------------------------------------------
# Build deterministic coverage index
# ------------------------------------------------------------

coverage_by_group = {}

for row in coverage_groups:
    if not isinstance(
        row,
        dict,
    ):
        continue

    release_family = clean(
        row.get(
            "release_family"
        )
    )

    heading = clean(
        row.get(
            "official_heading"
        )
        or row.get(
            "registered_heading"
        )
    )

    key = comparison_key(
        release_family,
        heading,
    )

    if (
        key[0]
        and key[1]
    ):
        coverage_by_group[
            key
        ] = row


# ------------------------------------------------------------
# Build dynamic group index
#
# Dynamic correlation is the generic path and therefore becomes
# the canonical group universe when deterministic coverage is
# unavailable for a future release family.
# ------------------------------------------------------------

dynamic_by_group = {}

for row in correlation_rows:
    if not isinstance(
        row,
        dict,
    ):
        continue

    key = comparison_key(
        row.get(
            "release_family"
        ),
        row.get(
            "heading"
        ),
    )

    if (
        key[0]
        and key[1]
    ):
        dynamic_by_group[
            key
        ] = row


# ------------------------------------------------------------
# Build union of official groups
#
# Usually both paths contain the same groups.
#
# For a future release with no deterministic rule pack:
#
#   dynamic correlation still contains the official groups
#   deterministic coverage may contain none
#
# That is now treated as a normal no-reference state.
# ------------------------------------------------------------

all_group_keys = sorted(
    set(
        dynamic_by_group
    )
    | set(
        coverage_by_group
    )
)


# ------------------------------------------------------------
# Determine overall deterministic-reference mode
# ------------------------------------------------------------

reported_rule_count = (
    compatibility_summary.get(
        "rule_count",
        0,
    )
)

rule_pack = compatibility_scope.get(
    "rule_pack"
)

has_deterministic_rules = bool(
    reported_rule_count
    or compatibility_results
)


if not has_deterministic_rules:
    deterministic_reference_mode = (
        "not_available"
    )

elif coverage_groups:
    deterministic_reference_mode = (
        "available"
    )

else:
    deterministic_reference_mode = (
        "incomplete"
    )


# ------------------------------------------------------------
# Compare groups
# ------------------------------------------------------------

comparisons = []

precision_reviews = []

relationship_counts = Counter()

alignment_detail_counts = Counter()


groups_with_reference = 0

groups_without_reference = 0

groups_with_incomplete_reference = 0


for key in all_group_keys:

    dynamic_row = dynamic_by_group.get(
        key
    )

    coverage_row = coverage_by_group.get(
        key
    )


    release_family = (
        clean(
            dynamic_row.get(
                "release_family"
            )
        )
        if dynamic_row
        else clean(
            coverage_row.get(
                "release_family"
            )
        )
    )


    heading = (
        clean(
            dynamic_row.get(
                "heading"
            )
        )
        if dynamic_row
        else clean(
            coverage_row.get(
                "official_heading"
            )
            or coverage_row.get(
                "registered_heading"
            )
        )
    )


    release_notes_url = (
        dynamic_row.get(
            "release_notes_url"
        )
        if dynamic_row
        else coverage_row.get(
            "release_notes_url"
        )
    )


    # --------------------------------------------------------
    # Deterministic coverage/reference
    # --------------------------------------------------------

    if coverage_row:

        coverage_status = clean(
            coverage_row.get(
                "coverage_status"
            )
        ).casefold()

        mapped_rule_ids = unique(
            coverage_row.get(
                "mapped_rule_ids",
                [],
            )
        )

        present_rule_ids = unique(
            coverage_row.get(
                "present_rule_ids",
                [],
            )
        )

        coverage_missing_rule_ids = unique(
            coverage_row.get(
                "missing_rule_ids",
                [],
            )
        )

    else:

        coverage_status = (
            "not_available"
        )

        mapped_rule_ids = []

        present_rule_ids = []

        coverage_missing_rule_ids = []


    deterministic_rows = [
        deterministic_by_id[
            rule_id
        ]

        for rule_id
        in present_rule_ids

        if rule_id
        in deterministic_by_id
    ]


    result_rule_ids = {
        clean(
            row.get(
                "id"
            )
        )

        for row
        in deterministic_rows

        if clean(
            row.get(
                "id"
            )
        )
    }


    missing_result_rule_ids = [
        rule_id

        for rule_id
        in present_rule_ids

        if rule_id
        not in result_rule_ids
    ]


    # --------------------------------------------------------
    # Reference classification
    #
    # not_available:
    #   No deterministic rule exists for this group/release.
    #   This is normal for a new dynamically supported release.
    #
    # incomplete:
    #   A deterministic mapping exists but expected rule output
    #   is absent. This is materially different and merits review.
    # --------------------------------------------------------

    if (
        not coverage_row
        and not has_deterministic_rules
    ):
        reference_status = (
            "not_available"
        )

    elif (
        not mapped_rule_ids
        or coverage_status
        not in {
            "covered",
            "partial",
        }
    ):
        reference_status = (
            "not_available"
        )

    elif (
        coverage_missing_rule_ids
        or missing_result_rule_ids
        or len(
            deterministic_rows
        )
        != len(
            present_rule_ids
        )
    ):
        reference_status = (
            "incomplete"
        )

    else:
        reference_status = (
            "available"
        )


    if reference_status == "available":
        groups_with_reference += 1

    elif reference_status == "not_available":
        groups_without_reference += 1

    else:
        groups_with_incomplete_reference += 1


    deterministic_statuses = unique(
        row.get(
            "status"
        )

        for row
        in deterministic_rows
    )


    deterministic_state = (
        deterministic_relevance_state(
            reference_status,
            deterministic_rows,
        )
    )


    # --------------------------------------------------------
    # Dynamic result
    # --------------------------------------------------------

    dynamic_status = (
        clean(
            dynamic_row.get(
                "correlation_status"
            )
        )

        if dynamic_row

        else "missing_dynamic_result"
    )


    dynamic_state = (
        dynamic_relevance_state(
            dynamic_status
        )
    )


    # --------------------------------------------------------
    # Compare local relevance
    # --------------------------------------------------------

    relationship = relevance_relationship(
        reference_status,
        deterministic_state,
        dynamic_state,
    )


    relationship_counts[
        relationship
    ] += 1


    # --------------------------------------------------------
    # Alignment detail
    # --------------------------------------------------------

    precision_review = False
    precision_note = None


    if relationship == "aligned_local":

        if (
            dynamic_status
            == "partial_local_evidence"
        ):

            alignment_detail = (
                "aligned_with_dynamic_scope_limitation"
            )


        elif (
            dynamic_status
            == "local_surface_evidence"
        ):

            alignment_detail = (
                "aligned_at_local_surface_level"
            )


        elif (
            dynamic_status
            == "strong_local_evidence"
        ):

            deterministic_no_affected_status = any(
                status.startswith(
                    "local_match_no_affected"
                )

                for status
                in deterministic_statuses
            )


            if deterministic_no_affected_status:

                alignment_detail = (
                    "aligned_local_with_precision_difference"
                )

                precision_review = True

                precision_note = (
                    "Dynamic correlation found a scoped "
                    "custom-source code-term match, while the "
                    "deterministic rule reported local presence "
                    "but no affected usage. This is not a "
                    "local-relevance disagreement; the two "
                    "scanners are using different evidence "
                    "precision and should be reviewed side by side."
                )

            else:

                alignment_detail = (
                    "aligned_with_specific_dynamic_evidence"
                )


        else:

            alignment_detail = (
                "aligned_local"
            )


    elif relationship == "aligned_no_local":

        alignment_detail = (
            "aligned_no_local"
        )


    elif relationship == "dynamic_gap":

        alignment_detail = (
            "review_dynamic_gap"
        )


    elif relationship == "deterministic_gap":

        alignment_detail = (
            "review_deterministic_gap"
        )


    elif relationship == "no_deterministic_reference":

        alignment_detail = (
            "dynamic_only_no_deterministic_reference"
        )


    elif relationship == "deterministic_reference_incomplete":

        alignment_detail = (
            "deterministic_reference_incomplete"
        )


    elif dynamic_status == "missing_dynamic_result":

        alignment_detail = (
            "dynamic_result_missing"
        )


    else:

        alignment_detail = (
            "comparison_unresolved"
        )


    alignment_detail_counts[
        alignment_detail
    ] += 1


    # --------------------------------------------------------
    # Store comparison
    # --------------------------------------------------------

    comparison = {
        "release_family":
            release_family,

        "official_heading":
            heading,

        "release_notes_url":
            release_notes_url,

        "coverage": {
            "coverage_status":
                coverage_status,

            "mapped_rule_ids":
                mapped_rule_ids,

            "present_rule_ids":
                present_rule_ids,

            "coverage_missing_rule_ids":
                coverage_missing_rule_ids,
        },

        "deterministic_reference": {
            "reference_status":
                reference_status,

            "result_rule_ids":
                sorted(
                    result_rule_ids
                ),

            "missing_result_rule_ids":
                missing_result_rule_ids,

            "local_relevance_state":
                deterministic_state,

            "statuses":
                deterministic_statuses,

            "results": [
                {
                    "id":
                        row.get(
                            "id"
                        ),

                    "area":
                        row.get(
                            "area"
                        ),

                    "local_match":
                        row.get(
                            "local_match"
                        ),

                    "status":
                        row.get(
                            "status"
                        ),

                    "note":
                        row.get(
                            "note"
                        ),
                }

                for row
                in deterministic_rows
            ],
        },

        "dynamic_reference": {
            "result_available":
                bool(
                    dynamic_row
                ),

            "correlation_status":
                dynamic_status,

            "local_relevance_state":
                dynamic_state,

            "interpretation":
                (
                    dynamic_row.get(
                        "interpretation"
                    )

                    if dynamic_row

                    else None
                ),
        },

        "validation": {
            "local_relevance_relationship":
                relationship,

            "alignment_detail":
                alignment_detail,

            "precision_review":
                precision_review,

            "precision_note":
                precision_note,
        },
    }


    comparisons.append(
        comparison
    )


    if precision_review:

        precision_reviews.append(
            {
                "release_family":
                    release_family,

                "official_heading":
                    heading,

                "dynamic_status":
                    dynamic_status,

                "deterministic_statuses":
                    deterministic_statuses,

                "note":
                    precision_note,
            }
        )


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

official_group_count = len(
    all_group_keys
)


aligned_local_count = (
    relationship_counts.get(
        "aligned_local",
        0,
    )
)


aligned_no_local_count = (
    relationship_counts.get(
        "aligned_no_local",
        0,
    )
)


aligned_count = (
    aligned_local_count
    + aligned_no_local_count
)


dynamic_gap_count = (
    relationship_counts.get(
        "dynamic_gap",
        0,
    )
)


deterministic_gap_count = (
    relationship_counts.get(
        "deterministic_gap",
        0,
    )
)


unresolved_count = (
    relationship_counts.get(
        "unresolved",
        0,
    )
    + relationship_counts.get(
        "deterministic_reference_incomplete",
        0,
    )
)


no_reference_count = (
    relationship_counts.get(
        "no_deterministic_reference",
        0,
    )
)


# ------------------------------------------------------------
# Validation/reference state
#
# COMPLETE:
#   every official group has a complete deterministic reference
#
# PARTIAL_REFERENCE:
#   some groups have reference, some do not
#
# NO_REFERENCE:
#   dynamic analysis exists but no deterministic rules exist yet
#
# INCOMPLETE:
#   deterministic mappings are expected but outputs are missing
# ------------------------------------------------------------

if (
    official_group_count
    and groups_with_reference
    == official_group_count
    and groups_with_incomplete_reference
    == 0
):
    validation_reference_status = (
        "complete"
    )

elif (
    official_group_count
    and groups_with_reference == 0
    and groups_without_reference
    == official_group_count
    and groups_with_incomplete_reference
    == 0
):
    validation_reference_status = (
        "no_reference"
    )

elif groups_with_incomplete_reference:
    validation_reference_status = (
        "incomplete"
    )

elif groups_with_reference:
    validation_reference_status = (
        "partial_reference"
    )

elif official_group_count:
    validation_reference_status = (
        "no_reference"
    )

else:
    validation_reference_status = (
        "not_applicable"
    )


# ------------------------------------------------------------
# Collector status
#
# Lack of deterministic rules is no longer an execution error.
#
# Dynamic correlation is the critical input because this
# validator's future-release purpose is to validate it when a
# deterministic reference exists.
# ------------------------------------------------------------

input_status = {
    "compatibility_coverage":
        (
            "ok"
            if coverage
            else "unavailable"
        ),

    "upgrade_compatibility":
        (
            "ok"
            if compatibility
            else "unavailable"
        ),

    "upgrade_correlation":
        (
            "ok"
            if correlation
            else "unavailable"
        ),
}


if not correlation:

    overall_status = (
        "error"
    )

elif correlation_collector.get(
    "overall"
) != "ok":

    overall_status = (
        "partial"
    )

elif groups_with_incomplete_reference:

    overall_status = (
        "partial"
    )

else:

    # COMPLETE reference, PARTIAL reference and NO reference are
    # all valid executions. Reference availability is reported
    # separately from collector health.
    overall_status = (
        "ok"
    )


# ------------------------------------------------------------
# Final report
# ------------------------------------------------------------

report = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "phase":
            "dynamic_correlation_reference_validation",

        "comparison_dimension":
            "local_relevance_alignment",

        "reference_semantics_version":
            2,

        "external_fetch_performed":
            False,

        "compatibility_assessed":
            False,

        "readiness_verdict_produced":
            False,

        "accuracy_score_produced":
            False,

        "mutates_source_results":
            False,

        "supports_dynamic_only_release":
            True,

        "note": (
            "This report compares dynamic correlation against "
            "available deterministic rule results at official "
            "change-group level. Deterministic reference "
            "availability is optional. A future release with no "
            "deterministic rule pack is a normal dynamic-only "
            "state, not a scanner failure. The report does not "
            "treat either path as ground truth, score accuracy, "
            "or produce a compatibility or update-safety verdict."
        ),
    },

    "inputs": {
        "status":
            input_status,

        "coverage_status":
            coverage_summary.get(
                "coverage_status"
            ),

        "coverage_official_group_count":
            coverage_summary.get(
                "official_crossed_group_count",
                0,
            ),

        "deterministic_rule_pack":
            rule_pack,

        "deterministic_rule_count":
            reported_rule_count,

        "deterministic_reference_mode":
            deterministic_reference_mode,

        "dynamic_evidence_model_version":
            correlation_scope.get(
                "evidence_model_version"
            ),

        "dynamic_official_group_count":
            correlation_summary.get(
                "official_crossed_group_count",
                0,
            ),
    },

    "summary": {
        "official_groups_observed":
            official_group_count,

        "official_groups_compared":
            groups_with_reference,

        "validation_reference_status":
            validation_reference_status,

        "groups_with_deterministic_reference":
            groups_with_reference,

        "groups_without_deterministic_reference":
            groups_without_reference,

        "groups_with_incomplete_deterministic_reference":
            groups_with_incomplete_reference,

        "aligned_count":
            aligned_count,

        "aligned_local_count":
            aligned_local_count,

        "aligned_no_local_count":
            aligned_no_local_count,

        "dynamic_gap_count":
            dynamic_gap_count,

        "deterministic_gap_count":
            deterministic_gap_count,

        "no_reference_count":
            no_reference_count,

        "unresolved_count":
            unresolved_count,

        "precision_review_count":
            len(
                precision_reviews
            ),

        "relationship_counts":
            dict(
                sorted(
                    relationship_counts.items()
                )
            ),

        "alignment_detail_counts":
            dict(
                sorted(
                    alignment_detail_counts.items()
                )
            ),
    },

    "comparisons":
        comparisons,

    "precision_reviews":
        precision_reviews,

    "limitations": [
        (
            "This validator compares local relevance only. "
            "It does not compare safe/unsafe outcomes because "
            "neither source produces such a verdict."
        ),

        (
            "An aligned result means both paths found local "
            "relevance or both found no local relevance. It "
            "does not prove that either result is correct."
        ),

        (
            "A dynamic-only future release with no deterministic "
            "rule pack is reported as NO_REFERENCE rather than "
            "an error or failed validation."
        ),

        (
            "Dynamic strong evidence can still be broader than "
            "a deterministic affected-usage test. A scoped "
            "literal source-code term match is not necessarily "
            "the same as an executable Python name reference."
        ),

        (
            "A deterministic rule pack may inspect narrower or "
            "deeper evidence than the generic dynamic scanner. "
            "Precision differences are recorded separately from "
            "local-relevance gaps."
        ),

        (
            "If a deterministic mapping exists but its expected "
            "rule result is missing, that is an incomplete "
            "reference and remains distinct from the normal "
            "no-reference state."
        ),
    ],

    "collector_status": {
        **input_status,

        "coverage_collector_status":
            coverage_collector.get(
                "overall",
                "unknown",
            ),

        "correlation_collector_status":
            correlation_collector.get(
                "overall",
                "unknown",
            ),

        "deterministic_reference_availability":
            validation_reference_status,

        "overall":
            overall_status,
    },
}


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8",
) as handle:

    json.dump(
        report,
        handle,
        indent=2,
    )


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")

print(
    "Correlation validation"
)

print(
    "------------------------------------------"
)

print(
    f"Official groups observed:      "
    f"{official_group_count}"
)

print(
    f"Groups with reference:         "
    f"{groups_with_reference}"
)

print(
    f"Groups without reference:      "
    f"{groups_without_reference}"
)

print(
    f"Incomplete references:         "
    f"{groups_with_incomplete_reference}"
)

print(
    f"Reference status:              "
    f"{validation_reference_status.upper()}"
)

print("")

if groups_with_reference:

    print(
        f"Aligned:                       "
        f"{aligned_count}"
    )

    print(
        f"  Aligned local:               "
        f"{aligned_local_count}"
    )

    print(
        f"  Aligned no local:            "
        f"{aligned_no_local_count}"
    )

    print(
        f"Dynamic gaps:                  "
        f"{dynamic_gap_count}"
    )

    print(
        f"Deterministic gaps:            "
        f"{deterministic_gap_count}"
    )

    print(
        f"Unresolved:                    "
        f"{unresolved_count}"
    )

    print(
        f"Precision reviews:             "
        f"{len(precision_reviews)}"
    )

else:

    print(
        "Comparison result:            "
        "NO DETERMINISTIC REFERENCE"
    )

print("")

print(
    "Important: deterministic reference availability "
    "is separate from collector health."
)

print(
    "A dynamic-only release is valid and does not "
    "produce an accuracy or compatibility verdict."
)

print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
