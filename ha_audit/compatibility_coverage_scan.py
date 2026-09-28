import json
import os
import re
from datetime import datetime, timezone


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

RELEASE_EVIDENCE_FILE = (
    "/config/release_evidence_audit.json"
)

UPGRADE_COMPATIBILITY_FILE = (
    "/config/upgrade_compatibility_audit.json"
)

OUTPUT_FILE = (
    "/config/compatibility_coverage_audit.json"
)


# ------------------------------------------------------------
# Deterministic rule-to-official-group registry
# ------------------------------------------------------------
#
# This registry does NOT decide whether a change affects the
# installation.
#
# It records which deterministic compatibility rules are
# intended to cover each official backward-incompatible-change
# group.
#
# One official group can map to multiple deterministic rules
# when the release note contains separately testable changes.
# ------------------------------------------------------------

RULE_GROUP_REGISTRY = {
    "2026.9": {
        "Flexit Nordic (BACnet)": [
            "core_2026_9_flexit_bacnet",
        ],

        "KNX": [
            "core_2026_9_knx",
        ],

        "LLM APIs": [
            "core_2026_9_llm_tool_names",
        ],

        "Persistent Notification": [
            "core_2026_9_persistent_notification_updated",
        ],

        "UniFi Protect": [
            "core_2026_9_unifiprotect_switches",
            "core_2026_9_unifiprotect_minimum_version",
        ],

        "Update": [
            "core_2026_9_update_admin_context",
        ],

        "Vacuum": [
            "core_2026_9_vacuum_battery_level",
        ],

        "Z-Wave JS": [
            "core_2026_9_zwave_js_admin_actions",
        ],
    },
}


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


def clean(value):
    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def normalise_heading(value):
    value = clean(
        value
    ).casefold()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return clean(
        value
    )


def unique(values):
    seen = set()
    output = []

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


def rule_pack_family(value):
    value = clean(
        value
    )

    prefix = (
        "home_assistant_core_"
    )

    if value.startswith(
        prefix
    ):
        value = value[
            len(prefix):
        ]

    value = value.replace(
        "_",
        ".",
    )

    match = re.match(
        r"^(\d{4})\.(\d{1,2})$",
        value,
    )

    if not match:
        return None

    return (
        f"{int(match.group(1))}."
        f"{int(match.group(2))}"
    )


def discover_rule_ids(value):
    """
    Find deterministic compatibility rule IDs without depending
    on the exact nesting of upgrade_compatibility_audit.json.

    This deliberately accepts rule_id, id, or rule fields, but
    only values beginning with core_.
    """

    found = []

    def walk(node):

        if isinstance(
            node,
            dict,
        ):

            for key, child in node.items():

                if (
                    key
                    in (
                        "rule_id",
                        "id",
                        "rule",
                    )
                    and isinstance(
                        child,
                        str,
                    )
                    and child.startswith(
                        "core_"
                    )
                ):
                    found.append(
                        child
                    )

                walk(
                    child
                )

        elif isinstance(
            node,
            list,
        ):

            for child in node:

                walk(
                    child
                )

    walk(
        value
    )

    return unique(
        found
    )


def build_registry_index():
    index = {}

    for (
        release_family,
        groups,
    ) in RULE_GROUP_REGISTRY.items():

        family_index = {}

        for (
            heading,
            rule_ids,
        ) in groups.items():

            family_index[
                normalise_heading(
                    heading
                )
            ] = {
                "registered_heading":
                    heading,

                "rule_ids":
                    list(
                        rule_ids
                    ),
            }

        index[
            release_family
        ] = family_index

    return index


REGISTRY_INDEX = (
    build_registry_index()
)


# ------------------------------------------------------------
# Load input reports
# ------------------------------------------------------------

release_evidence = (
    load_json_optional(
        RELEASE_EVIDENCE_FILE
    )
)

upgrade_compatibility = (
    load_json_optional(
        UPGRADE_COMPATIBILITY_FILE
    )
)


release_scope = (
    release_evidence.get(
        "scope",
        {},
    )
)

release_range = (
    release_evidence.get(
        "release_range",
        {},
    )
)

release_aggregate = (
    release_evidence.get(
        "aggregate",
        {},
    )
)

release_collector = (
    release_evidence.get(
        "collector_status",
        {},
    )
)

compatibility_scope = (
    upgrade_compatibility.get(
        "scope",
        {},
    )
)

compatibility_summary = (
    upgrade_compatibility.get(
        "summary",
        {},
    )
)


if not isinstance(
    release_scope,
    dict,
):
    release_scope = {}


if not isinstance(
    release_range,
    dict,
):
    release_range = {}


if not isinstance(
    release_aggregate,
    dict,
):
    release_aggregate = {}


if not isinstance(
    release_collector,
    dict,
):
    release_collector = {}


if not isinstance(
    compatibility_scope,
    dict,
):
    compatibility_scope = {}


if not isinstance(
    compatibility_summary,
    dict,
):
    compatibility_summary = {}


# ------------------------------------------------------------
# Official crossed breaking-change groups
# ------------------------------------------------------------

official_groups = (
    release_aggregate.get(
        "breaking_change_groups",
        [],
    )
)

if not isinstance(
    official_groups,
    list,
):
    official_groups = []


crossed_groups = [
    item
    for item
    in official_groups
    if (
        isinstance(
            item,
            dict,
        )
        and item.get(
            "crossed_from_installed"
        )
    )
]


crossed_release_families = (
    release_aggregate.get(
        "crossed_release_families",
        [],
    )
)

if not isinstance(
    crossed_release_families,
    list,
):
    crossed_release_families = []


# ------------------------------------------------------------
# Deterministic compatibility rule evidence
# ------------------------------------------------------------

compatibility_rule_ids = (
    discover_rule_ids(
        upgrade_compatibility
    )
)


compatibility_rule_pack = (
    compatibility_scope.get(
        "rule_pack"
    )
)


compatibility_rule_pack_family = (
    rule_pack_family(
        compatibility_rule_pack
    )
)


compatibility_rule_count = (
    compatibility_summary.get(
        "rule_count",
        0,
    )
)

try:
    compatibility_rule_count = int(
        compatibility_rule_count
    )

except (
    TypeError,
    ValueError,
):
    compatibility_rule_count = 0


# ------------------------------------------------------------
# Group-to-rule coverage
# ------------------------------------------------------------

group_results = []

mapped_rule_ids = []

present_linked_rule_ids = []

missing_mapped_rule_ids = []


covered_group_count = 0

partial_group_count = 0

unmapped_group_count = 0


for group in crossed_groups:

    release_family = clean(
        group.get(
            "release_family"
        )
    )

    heading = clean(
        group.get(
            "heading"
        )
    )


    family_registry = (
        REGISTRY_INDEX.get(
            release_family,
            {},
        )
    )


    registry_entry = (
        family_registry.get(
            normalise_heading(
                heading
            )
        )
    )


    expected_rule_ids = []

    registered_heading = None


    if registry_entry:

        registered_heading = (
            registry_entry.get(
                "registered_heading"
            )
        )

        expected_rule_ids = unique(
            registry_entry.get(
                "rule_ids",
                [],
            )
        )


    present_rule_ids = [
        rule_id
        for rule_id
        in expected_rule_ids
        if rule_id
        in compatibility_rule_ids
    ]


    missing_rule_ids = [
        rule_id
        for rule_id
        in expected_rule_ids
        if rule_id
        not in compatibility_rule_ids
    ]


    mapped_rule_ids.extend(
        expected_rule_ids
    )

    present_linked_rule_ids.extend(
        present_rule_ids
    )

    missing_mapped_rule_ids.extend(
        missing_rule_ids
    )


    if not expected_rule_ids:

        coverage_status = (
            "unmapped"
        )

        unmapped_group_count += 1


    elif missing_rule_ids:

        coverage_status = (
            "partial"
        )

        partial_group_count += 1


    else:

        coverage_status = (
            "covered"
        )

        covered_group_count += 1


    group_results.append(
        {
            "release_family":
                release_family,

            "official_heading":
                heading,

            "registered_heading":
                registered_heading,

            "release_notes_url":
                group.get(
                    "release_notes_url"
                ),

            "coverage_status":
                coverage_status,

            "mapped_rule_count":
                len(
                    expected_rule_ids
                ),

            "mapped_rule_ids":
                expected_rule_ids,

            "present_rule_ids":
                present_rule_ids,

            "missing_rule_ids":
                missing_rule_ids,
        }
    )


mapped_rule_ids = unique(
    mapped_rule_ids
)


present_linked_rule_ids = unique(
    present_linked_rule_ids
)


missing_mapped_rule_ids = unique(
    missing_mapped_rule_ids
)


unlinked_compatibility_rule_ids = [
    rule_id
    for rule_id
    in compatibility_rule_ids
    if rule_id
    not in mapped_rule_ids
]


# ------------------------------------------------------------
# Per-release coverage
# ------------------------------------------------------------

release_results = []


for release_family in crossed_release_families:

    family_groups = [
        item
        for item
        in group_results
        if item.get(
            "release_family"
        )
        == release_family
    ]


    family_covered = sum(
        1
        for item
        in family_groups
        if item.get(
            "coverage_status"
        )
        == "covered"
    )


    family_partial = sum(
        1
        for item
        in family_groups
        if item.get(
            "coverage_status"
        )
        == "partial"
    )


    family_unmapped = sum(
        1
        for item
        in family_groups
        if item.get(
            "coverage_status"
        )
        == "unmapped"
    )


    if not family_groups:

        family_status = (
            "no_official_groups"
        )


    elif (
        family_covered
        == len(
            family_groups
        )
    ):

        family_status = (
            "covered"
        )


    elif (
        family_covered
        or family_partial
    ):

        family_status = (
            "partial"
        )


    else:

        family_status = (
            "uncovered"
        )


    release_results.append(
        {
            "release_family":
                release_family,

            "official_group_count":
                len(
                    family_groups
                ),

            "covered_group_count":
                family_covered,

            "partial_group_count":
                family_partial,

            "unmapped_group_count":
                family_unmapped,

            "coverage_status":
                family_status,

            "registry_available":
                release_family
                in RULE_GROUP_REGISTRY,

            "is_compatibility_rule_pack_family":
                release_family
                == compatibility_rule_pack_family,
        }
    )


# ------------------------------------------------------------
# Overall coverage classification
# ------------------------------------------------------------

release_report_available = bool(
    release_evidence
)


compatibility_report_available = bool(
    upgrade_compatibility
)


release_evidence_ok = (
    release_collector.get(
        "overall"
    )
    == "ok"
)


crossed_group_count = len(
    crossed_groups
)


if not release_report_available:

    coverage_status = (
        "unavailable_release_evidence"
    )


elif not compatibility_report_available:

    coverage_status = (
        "unavailable_compatibility_report"
    )


elif not release_evidence_ok:

    coverage_status = (
        "release_evidence_incomplete"
    )


elif crossed_group_count == 0:

    coverage_status = (
        "not_applicable"
    )


elif (
    covered_group_count
    == crossed_group_count
    and not partial_group_count
    and not unmapped_group_count
    and not missing_mapped_rule_ids
    and not unlinked_compatibility_rule_ids
):

    coverage_status = (
        "complete"
    )


elif (
    covered_group_count
    or partial_group_count
):

    coverage_status = (
        "partial"
    )


else:

    coverage_status = (
        "none"
    )


# ------------------------------------------------------------
# Report
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
            "compatibility_coverage_mapping",

        "local_evidence_only":
            False,

        "external_fetch_performed":
            False,

        "official_release_evidence_consumed":
            True,

        "compatibility_assessed":
            False,

        "readiness_verdict_produced":
            False,

        "note": (
            "This report links official Home Assistant Core "
            "backward-incompatible-change groups to deterministic "
            "HA Audit compatibility rules. It measures rule "
            "coverage only. It does not decide whether a change "
            "affects this installation and does not produce a "
            "safe-to-update verdict."
        ),
    },

    "inputs": {
        "release_evidence_report_available":
            release_report_available,

        "release_evidence_status":
            release_collector.get(
                "overall"
            ),

        "upgrade_compatibility_report_available":
            compatibility_report_available,

        "compatibility_rule_pack":
            compatibility_rule_pack,

        "compatibility_rule_pack_family":
            compatibility_rule_pack_family,

        "compatibility_rule_count_reported":
            compatibility_rule_count,

        "compatibility_rule_ids_discovered":
            compatibility_rule_ids,
    },

    "release_range": {
        "status":
            release_range.get(
                "status"
            ),

        "complete":
            release_range.get(
                "complete"
            ),

        "crossed_release_families":
            crossed_release_families,
    },

    "summary": {
        "coverage_status":
            coverage_status,

        "official_crossed_group_count":
            crossed_group_count,

        "covered_group_count":
            covered_group_count,

        "partial_group_count":
            partial_group_count,

        "unmapped_group_count":
            unmapped_group_count,

        "mapped_rule_count":
            len(
                mapped_rule_ids
            ),

        "present_linked_rule_count":
            len(
                present_linked_rule_ids
            ),

        "missing_mapped_rule_count":
            len(
                missing_mapped_rule_ids
            ),

        "unlinked_compatibility_rule_count":
            len(
                unlinked_compatibility_rule_ids
            ),
    },

    "release_coverage":
        release_results,

    "group_coverage":
        group_results,

    "rule_linkage": {
        "mapped_rule_ids":
            mapped_rule_ids,

        "present_linked_rule_ids":
            present_linked_rule_ids,

        "missing_mapped_rule_ids":
            missing_mapped_rule_ids,

        "unlinked_compatibility_rule_ids":
            unlinked_compatibility_rule_ids,
    },

    "limitations": [
        (
            "Coverage mappings are deterministic and must be "
            "defined explicitly for each supported release family."
        ),

        (
            "An official group marked covered means HA Audit has "
            "one or more deterministic rules linked to that group; "
            "it does not mean every possible configuration path or "
            "UI-managed value has been inspected."
        ),

        (
            "A rule being linked does not mean the affected feature "
            "is present or affected on this installation."
        ),
    ],

    "collector_status": {
        "release_evidence_input":
            (
                "ok"
                if release_report_available
                else "unavailable"
            ),

        "upgrade_compatibility_input":
            (
                "ok"
                if compatibility_report_available
                else "unavailable"
            ),

        "rule_id_discovery":
            (
                "ok"
                if (
                    compatibility_rule_ids
                    or compatibility_rule_count
                    == 0
                )
                else "no_rule_ids_found"
            ),

        "overall":
            (
                "ok"
                if coverage_status
                in (
                    "complete",
                    "not_applicable",
                )
                else "partial"
                if coverage_status
                in (
                    "partial",
                    "none",
                )
                else "error"
            ),
    },
}


# ------------------------------------------------------------
# Write report
# ------------------------------------------------------------

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
    "Compatibility coverage mapping"
)

print(
    "------------------------------------------"
)

print(
    f"Coverage status:               "
    f"{coverage_status}"
)

print(
    f"Official crossed groups:       "
    f"{crossed_group_count}"
)

print(
    f"Covered groups:                "
    f"{covered_group_count}"
)

print(
    f"Partial groups:                "
    f"{partial_group_count}"
)

print(
    f"Unmapped groups:               "
    f"{unmapped_group_count}"
)

print(
    f"Compatibility rules reported:  "
    f"{compatibility_rule_count}"
)

print(
    f"Rule IDs discovered:           "
    f"{len(compatibility_rule_ids)}"
)

print(
    f"Linked rules present:          "
    f"{len(present_linked_rule_ids)}"
)

print(
    f"Missing mapped rules:          "
    f"{len(missing_mapped_rule_ids)}"
)

print(
    f"Unlinked compatibility rules:  "
    f"{len(unlinked_compatibility_rule_ids)}"
)


if release_results:

    print("")

    print(
        "Per-release coverage:"
    )

    print(
        "------------------------------------------"
    )

    for release in release_results:

        print(
            f"{release.get('release_family')}: "
            f"{release.get('coverage_status')}; "
            f"{release.get('covered_group_count', 0)}/"
            f"{release.get('official_group_count', 0)} "
            "group(s) covered"
        )


print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
