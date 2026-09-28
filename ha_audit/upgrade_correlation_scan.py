import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

RELEASE_EVIDENCE_FILE = (
    "/config/release_evidence_audit.json"
)

UPGRADE_IMPACT_FILE = (
    "/config/upgrade_impact_audit.json"
)

QUALITY_FILE = (
    "/config/quality_audit.json"
)

UPGRADE_COMPATIBILITY_FILE = (
    "/config/upgrade_compatibility_audit.json"
)

OUTPUT_FILE = (
    "/config/upgrade_correlation_audit.json"
)

MAX_TEXT_FILE_BYTES = (
    2 * 1024 * 1024
)

MAX_CUSTOM_SOURCE_FILES_PER_DOMAIN = (
    1000
)

MAX_MATCH_FILES_PER_TERM = (
    25
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


def as_list(value):
    if isinstance(
        value,
        list,
    ):
        return value

    return []


def as_dict(value):
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def normalise_identifier(value):
    value = (
        clean(
            value
        )
        .casefold()
        .replace(
            "&",
            " and ",
        )
    )

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        value,
    ).strip(
        "_"
    )


def compact_identifier(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        clean(
            value
        ).casefold(),
    )


def heading_candidates(heading):
    normalised = normalise_identifier(
        heading
    )

    if not normalised:
        return []

    candidates = [
        normalised,
    ]

    words = [
        word
        for word
        in normalised.split(
            "_"
        )
        if word
    ]

    removable_suffixes = {
        "api",
        "apis",
        "integration",
        "integrations",
        "platform",
        "platforms",
    }

    while (
        words
        and words[-1]
        in removable_suffixes
    ):
        words = words[:-1]

        if words:
            candidates.append(
                "_".join(
                    words
                )
            )

    return unique(
        candidates
    )


def extract_integration_domains(links):
    domains = []

    for link in as_list(
        links
    ):
        if not isinstance(
            link,
            str,
        ):
            continue

        try:
            parsed = urlparse(
                link
            )

        except Exception:
            continue

        host = (
            parsed.hostname
            or ""
        ).casefold()

        if host not in {
            "home-assistant.io",
            "www.home-assistant.io",
        }:
            continue

        match = re.match(
            r"^/integrations/([^/?#]+)/?",
            parsed.path,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        domain = normalise_identifier(
            match.group(
                1
            )
        )

        if domain:
            domains.append(
                domain
            )

    return unique(
        domains
    )


def scanworthy_code_terms(values):
    output = []

    for value in as_list(
        values
    ):
        term = clean(
            value
        )

        if (
            not term
            or len(
                term
            ) < 4
        ):
            continue

        # Placeholder examples such as:
        #
        # switch.<device>_fireplace_mode
        #
        # are useful official evidence but should not be
        # treated as literal local-search terms.
        if (
            "<" in term
            and ">" in term
        ):
            continue

        has_code_punctuation = any(
            marker in term
            for marker in (
                "_",
                ".",
                ":",
                "/",
            )
        )

        has_internal_capital = any(
            char.isupper()
            for char in term[1:]
        )

        if (
            has_code_punctuation
            or has_internal_capital
        ):
            output.append(
                term
            )

    return unique(
        output
    )


def extract_paths_from_value(value):
    paths = []

    if isinstance(
        value,
        str,
    ):
        if value.lower().endswith(
            (
                ".yaml",
                ".yml",
            )
        ):
            paths.append(
                value
            )

    elif isinstance(
        value,
        list,
    ):
        for item in value:
            paths.extend(
                extract_paths_from_value(
                    item
                )
            )

    elif isinstance(
        value,
        dict,
    ):
        for key in (
            "path",
            "file",
            "filename",
            "relative_path",
        ):
            if key in value:
                paths.extend(
                    extract_paths_from_value(
                        value.get(
                            key
                        )
                    )
                )

    return paths


def extract_active_yaml_paths(
    configuration_tree,
    home_root,
):
    configuration_tree = as_dict(
        configuration_tree
    )

    candidate_keys = (
        "active_yaml_files",
        "active_files",
        "active_yaml",
        "active_paths",
        "active",
    )

    raw_paths = []
    source_key = None

    for key in candidate_keys:
        if key not in configuration_tree:
            continue

        found = extract_paths_from_value(
            configuration_tree.get(
                key
            )
        )

        if found:
            raw_paths = found
            source_key = key
            break

    resolved = []

    for raw_path in unique(
        raw_paths
    ):
        path = Path(
            raw_path
        )

        if path.is_absolute():
            if str(
                path
            ).startswith(
                "/config/"
            ):
                path = (
                    Path(
                        home_root
                    )
                    / str(
                        path
                    )[
                        len(
                            "/config/"
                        ):
                    ]
                )

        else:
            path = (
                Path(
                    home_root
                )
                / path
            )

        resolved.append(
            str(
                path
            )
        )

    return {
        "source_key":
            source_key,

        "paths":
            unique(
                resolved
            ),
    }


def read_text_file(path):
    try:
        if os.stat(
            path
        ).st_size > MAX_TEXT_FILE_BYTES:
            return (
                None,
                "file_too_large",
            )

        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            return (
                handle.read(),
                None,
            )

    except Exception as error:
        return (
            None,
            str(
                error
            ),
        )


def scan_files_for_terms(
    paths,
    terms,
):
    terms = scanworthy_code_terms(
        terms
    )

    matches = {
        term: []
        for term in terms
    }

    failures = []
    files_checked = 0

    if not terms:
        return {
            "files_checked": 0,
            "failures": [],
            "term_matches": {},
            "matched_term_count": 0,
            "matched_file_count": 0,
        }

    for path in unique(
        paths
    ):
        text, error = read_text_file(
            path
        )

        if error:
            failures.append(
                {
                    "path":
                        path,

                    "error":
                        error,
                }
            )

            continue

        files_checked += 1

        lower_text = text.casefold()

        for term in terms:
            if (
                term.casefold()
                not in lower_text
            ):
                continue

            if len(
                matches[
                    term
                ]
            ) < MAX_MATCH_FILES_PER_TERM:
                matches[
                    term
                ].append(
                    path
                )

    term_matches = {
        term:
            found_paths

        for term, found_paths
        in matches.items()

        if found_paths
    }

    matched_files = {
        path

        for found_paths
        in term_matches.values()

        for path
        in found_paths
    }

    return {
        "files_checked":
            files_checked,

        "failures":
            failures,

        "term_matches":
            term_matches,

        "matched_term_count":
            len(
                term_matches
            ),

        "matched_file_count":
            len(
                matched_files
            ),
    }


def collect_custom_source_paths(
    domain,
    custom_components_root,
):
    root = (
        Path(
            custom_components_root
        )
        / domain
    )

    if not root.is_dir():
        return (
            [],
            None,
        )

    output = []

    try:
        for (
            current_root,
            dirs,
            files,
        ) in os.walk(
            root
        ):
            dirs[:] = [
                directory

                for directory
                in dirs

                if directory
                not in {
                    "__pycache__",
                    ".git",
                }
            ]

            for filename in files:
                if not filename.lower().endswith(
                    (
                        ".py",
                        ".yaml",
                        ".yml",
                        ".json",
                    )
                ):
                    continue

                output.append(
                    str(
                        Path(
                            current_root
                        )
                        / filename
                    )
                )

                if len(
                    output
                ) >= MAX_CUSTOM_SOURCE_FILES_PER_DOMAIN:
                    return (
                        output,
                        "file_limit_reached",
                    )

    except Exception as error:
        return (
            output,
            str(
                error
            ),
        )

    return (
        output,
        None,
    )


def match_heading_to_local_identifiers(
    heading,
    local_identifiers,
):
    candidate_compacts = {
        compact_identifier(
            candidate
        )

        for candidate
        in heading_candidates(
            heading
        )

        if compact_identifier(
            candidate
        )
    }

    matches = []

    for identifier in local_identifiers:
        if (
            compact_identifier(
                identifier
            )
            in candidate_compacts
        ):
            matches.append(
                identifier
            )

    return unique(
        matches
    )


# ------------------------------------------------------------
# Load inputs
# ------------------------------------------------------------

release_evidence = load_json_optional(
    RELEASE_EVIDENCE_FILE
)

upgrade_impact = load_json_optional(
    UPGRADE_IMPACT_FILE
)

quality = load_json_optional(
    QUALITY_FILE
)

upgrade_compatibility = load_json_optional(
    UPGRADE_COMPATIBILITY_FILE
)


release_aggregate = as_dict(
    release_evidence.get(
        "aggregate"
    )
)

release_collector_status = as_dict(
    release_evidence.get(
        "collector_status"
    )
)

impact_config_entries = as_dict(
    upgrade_impact.get(
        "config_entries"
    )
)

impact_loaded_components = as_dict(
    upgrade_impact.get(
        "loaded_components"
    )
)

impact_platform_usage = as_dict(
    upgrade_impact.get(
        "platform_usage"
    )
)

impact_custom_integrations = as_dict(
    upgrade_impact.get(
        "custom_integrations"
    )
)

impact_home_config = as_dict(
    upgrade_impact.get(
        "home_assistant_config"
    )
)

configuration_tree = as_dict(
    quality.get(
        "configuration_tree"
    )
)

compatibility_summary = as_dict(
    upgrade_compatibility.get(
        "summary"
    )
)

compatibility_scope = as_dict(
    upgrade_compatibility.get(
        "scope"
    )
)


# ------------------------------------------------------------
# Build local evidence indexes
# ------------------------------------------------------------

configured_domains = unique(
    impact_config_entries.get(
        "domains",
        [],
    )
)

loaded_components = unique(
    as_list(
        impact_loaded_components.get(
            "bare_components"
        )
    )
    + as_list(
        impact_loaded_components.get(
            "component_roots"
        )
    )
)


platform_index = {}

for row in as_list(
    impact_platform_usage.get(
        "platforms"
    )
):
    if not isinstance(
        row,
        dict,
    ):
        continue

    platform = normalise_identifier(
        row.get(
            "platform"
        )
    )

    if platform:
        platform_index[
            platform
        ] = unique(
            row.get(
                "integrations",
                [],
            )
        )


active_custom_rows = [
    item

    for item
    in as_list(
        impact_custom_integrations.get(
            "active"
        )
    )

    if isinstance(
        item,
        dict,
    )
]


active_custom_by_domain = {}

for item in active_custom_rows:
    domain = normalise_identifier(
        item.get(
            "domain"
        )
        or item.get(
            "directory"
        )
    )

    if domain:
        active_custom_by_domain[
            domain
        ] = item


active_custom_domains = sorted(
    active_custom_by_domain
)


all_local_identifiers = unique(
    configured_domains
    + loaded_components
    + list(
        platform_index
    )
    + active_custom_domains
)


home_root = (
    impact_home_config.get(
        "root"
    )
    or "/homeassistant"
)


custom_components_root = (
    impact_home_config.get(
        "custom_components_root"
    )
    or str(
        Path(
            home_root
        )
        / "custom_components"
    )
)


active_yaml_discovery = (
    extract_active_yaml_paths(
        configuration_tree,
        home_root,
    )
)

active_yaml_paths = (
    active_yaml_discovery[
        "paths"
    ]
)


# ------------------------------------------------------------
# Select crossed official backward-incompatible change groups
# ------------------------------------------------------------

official_groups = [
    item

    for item
    in as_list(
        release_aggregate.get(
            "breaking_change_groups"
        )
    )

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


# ------------------------------------------------------------
# Dynamic correlation
# ------------------------------------------------------------

results = []

status_counts = Counter()

all_yaml_failures = []

custom_source_scan_failures = []


for group in official_groups:
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

    official_domains = (
        extract_integration_domains(
            group.get(
                "links"
            )
        )
    )

    code_terms = unique(
        group.get(
            "code_terms",
            [],
        )
    )

    scan_terms = (
        scanworthy_code_terms(
            code_terms
        )
    )


    # --------------------------------------------------------
    # Direct local integration/platform evidence
    # --------------------------------------------------------

    configured_domain_matches = [
        domain

        for domain
        in official_domains

        if domain
        in configured_domains
    ]


    loaded_component_matches = [
        domain

        for domain
        in official_domains

        if domain
        in loaded_components
    ]


    platform_matches = [
        domain

        for domain
        in official_domains

        if domain
        in platform_index
    ]


    active_custom_matches = [
        domain

        for domain
        in official_domains

        if domain
        in active_custom_by_domain
    ]


    # --------------------------------------------------------
    # Weaker heading-based relationship
    # --------------------------------------------------------

    heading_matches = (
        match_heading_to_local_identifiers(
            heading,
            all_local_identifiers,
        )
    )


    platform_integration_evidence = {
        platform:
            platform_index.get(
                platform,
                [],
            )

        for platform
        in platform_matches
    }


    # --------------------------------------------------------
    # Active YAML code-term evidence
    # --------------------------------------------------------

    yaml_scan = scan_files_for_terms(
        active_yaml_paths,
        scan_terms,
    )

    all_yaml_failures.extend(
        yaml_scan.get(
            "failures",
            [],
        )
    )


    # --------------------------------------------------------
    # Determine which active custom integrations are relevant
    # enough to inspect.
    #
    # Example:
    #
    # official Vacuum change
    #   -> local vacuum platform
    #   -> integrations matter / robovac / tuya
    #   -> robovac is active custom integration
    #   -> inspect robovac source for official code terms
    # --------------------------------------------------------

    relevant_custom_domains = set(
        active_custom_matches
    )


    for platform in platform_matches:
        for integration in platform_index.get(
            platform,
            [],
        ):
            integration_domain = (
                normalise_identifier(
                    integration
                )
            )

            if (
                integration_domain
                in active_custom_by_domain
            ):
                relevant_custom_domains.add(
                    integration_domain
                )


    for heading_match in heading_matches:
        match_domain = (
            normalise_identifier(
                heading_match
            )
        )

        if (
            match_domain
            in active_custom_by_domain
        ):
            relevant_custom_domains.add(
                match_domain
            )


    # --------------------------------------------------------
    # Relevant custom-source code-term evidence
    # --------------------------------------------------------

    custom_source_scans = []

    custom_source_matched_terms = set()


    for domain in sorted(
        relevant_custom_domains
    ):
        (
            source_paths,
            discovery_error,
        ) = collect_custom_source_paths(
            domain,
            custom_components_root,
        )

        source_scan = scan_files_for_terms(
            source_paths,
            scan_terms,
        )

        if discovery_error:
            custom_source_scan_failures.append(
                {
                    "domain":
                        domain,

                    "error":
                        discovery_error,
                }
            )

        custom_source_matched_terms.update(
            source_scan.get(
                "term_matches",
                {},
            )
        )

        custom_source_scans.append(
            {
                "domain":
                    domain,

                "source_file_count":
                    len(
                        source_paths
                    ),

                "source_discovery_error":
                    discovery_error,

                "files_checked":
                    source_scan.get(
                        "files_checked",
                        0,
                    ),

                "matched_term_count":
                    source_scan.get(
                        "matched_term_count",
                        0,
                    ),

                "term_matches":
                    source_scan.get(
                        "term_matches",
                        {},
                    ),

                "read_failures":
                    source_scan.get(
                        "failures",
                        [],
                    ),
            }
        )


    # --------------------------------------------------------
    # Evidence classification
    #
    # These are correlation statuses only.
    #
    # They do NOT mean:
    #   affected
    #   unaffected
    #   compatible
    #   incompatible
    #   safe to update
    # --------------------------------------------------------

    direct_evidence_present = bool(
        configured_domain_matches
        or loaded_component_matches
        or platform_matches
        or active_custom_matches
    )


    literal_code_evidence_present = bool(
        yaml_scan.get(
            "matched_term_count"
        )
        or custom_source_matched_terms
    )


    heading_evidence_present = bool(
        heading_matches
    )


    if (
        direct_evidence_present
        or literal_code_evidence_present
    ):
        correlation_status = (
            "strong_local_evidence"
        )

    elif heading_evidence_present:
        correlation_status = (
            "partial_local_evidence"
        )

    elif official_domains:
        correlation_status = (
            "no_local_evidence"
        )

    elif (
        scan_terms
        and not active_yaml_paths
    ):
        correlation_status = (
            "insufficient_evidence"
        )

    elif scan_terms:
        correlation_status = (
            "no_local_evidence"
        )

    else:
        correlation_status = (
            "insufficient_evidence"
        )


    status_counts[
        correlation_status
    ] += 1


    if (
        correlation_status
        == "strong_local_evidence"
    ):
        interpretation = (
            "Local evidence relevant to the official "
            "change was found. This does not mean the "
            "installation is affected."
        )

    elif (
        correlation_status
        == "partial_local_evidence"
    ):
        interpretation = (
            "A weaker local identifier relationship was "
            "found, but no direct official-domain or "
            "literal code-term evidence was confirmed."
        )

    elif (
        correlation_status
        == "no_local_evidence"
    ):
        interpretation = (
            "No local evidence was found for the official "
            "integration or platform identifiers available "
            "for this change."
        )

    else:
        interpretation = (
            "The available official and local evidence is "
            "insufficient for a useful correlation "
            "classification."
        )


    results.append(
        {
            "release_family":
                release_family,

            "heading":
                heading,

            "release_notes_url":
                group.get(
                    "release_notes_url"
                ),

            "official_text":
                group.get(
                    "text"
                ),

            "official_integration_domains":
                official_domains,

            "official_code_terms":
                code_terms,

            "scanworthy_code_terms":
                scan_terms,

            "local_evidence": {
                "configured_domain_matches":
                    configured_domain_matches,

                "loaded_component_matches":
                    loaded_component_matches,

                "platform_matches":
                    platform_matches,

                "platform_integration_evidence":
                    platform_integration_evidence,

                "active_custom_integration_matches":
                    active_custom_matches,

                "heading_identifier_matches":
                    heading_matches,

                "active_yaml": {
                    "scan_available":
                        bool(
                            active_yaml_paths
                        ),

                    "files_checked":
                        yaml_scan.get(
                            "files_checked",
                            0,
                        ),

                    "matched_term_count":
                        yaml_scan.get(
                            "matched_term_count",
                            0,
                        ),

                    "term_matches":
                        yaml_scan.get(
                            "term_matches",
                            {},
                        ),

                    "read_failures":
                        yaml_scan.get(
                            "failures",
                            [],
                        ),
                },

                "custom_source": {
                    "relevant_domains":
                        sorted(
                            relevant_custom_domains
                        ),

                    "matched_terms":
                        sorted(
                            custom_source_matched_terms
                        ),

                    "scans":
                        custom_source_scans,
                },
            },

            "correlation_status":
                correlation_status,

            "interpretation":
                interpretation,
        }
    )


# ------------------------------------------------------------
# Keep deterministic results as reference only
# ------------------------------------------------------------

reference_validation = {
    "deterministic_report_available":
        bool(
            upgrade_compatibility
        ),

    "deterministic_rule_pack":
        compatibility_scope.get(
            "rule_pack"
        ),

    "deterministic_rule_count":
        compatibility_summary.get(
            "rule_count",
            0,
        ),

    "deterministic_status_counts":
        as_dict(
            compatibility_summary.get(
                "status_counts"
            )
        ),

    "influences_dynamic_correlation_status":
        False,

    "note": (
        "The deterministic compatibility report is retained "
        "only as reference context for side-by-side validation. "
        "Its rule outcomes do not influence dynamic correlation "
        "status."
    ),
}


# ------------------------------------------------------------
# Report
# ------------------------------------------------------------

strong_count = status_counts.get(
    "strong_local_evidence",
    0,
)

partial_count = status_counts.get(
    "partial_local_evidence",
    0,
)

no_local_count = status_counts.get(
    "no_local_evidence",
    0,
)

insufficient_count = status_counts.get(
    "insufficient_evidence",
    0,
)


input_status = {
    "release_evidence":
        (
            "ok"
            if release_evidence
            else "unavailable"
        ),

    "upgrade_impact":
        (
            "ok"
            if upgrade_impact
            else "unavailable"
        ),

    "quality_audit":
        (
            "ok"
            if quality
            else "unavailable"
        ),

    "upgrade_compatibility_reference":
        (
            "ok"
            if upgrade_compatibility
            else "unavailable"
        ),
}


critical_input_error = (
    not release_evidence
    or not upgrade_impact
)


if critical_input_error:
    overall_status = (
        "error"
    )

elif (
    release_collector_status.get(
        "overall"
    )
    != "ok"
):
    overall_status = (
        "partial"
    )

else:
    overall_status = (
        "ok"
    )


report = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "phase":
            "dynamic_upgrade_correlation_foundation",

        "external_fetch_performed":
            False,

        "official_release_evidence_consumed":
            True,

        "local_upgrade_impact_evidence_consumed":
            True,

        "dynamic_correlation_performed":
            True,

        "compatibility_assessed":
            False,

        "readiness_verdict_produced":
            False,

        "deterministic_rule_outcomes_used_for_classification":
            False,

        "note": (
            "This report dynamically correlates official "
            "Home Assistant Core backward-incompatible-change "
            "evidence with local integration, platform, YAML, "
            "and custom-source evidence. Correlation is not "
            "proof of impact, compatibility, incompatibility, "
            "or update safety."
        ),
    },

    "inputs": {
        "status":
            input_status,

        "official_release_evidence_status":
            release_collector_status.get(
                "overall"
            ),

        "official_crossed_group_count":
            len(
                official_groups
            ),

        "configured_domain_count":
            len(
                configured_domains
            ),

        "loaded_component_count":
            len(
                loaded_components
            ),

        "platform_count":
            len(
                platform_index
            ),

        "active_custom_integration_count":
            len(
                active_custom_domains
            ),

        "active_yaml_count_reported":
            configuration_tree.get(
                "active_yaml_count"
            ),

        "active_yaml_path_source_key":
            active_yaml_discovery.get(
                "source_key"
            ),

        "active_yaml_paths_discovered":
            len(
                active_yaml_paths
            ),
    },

    "local_indexes": {
        "configured_domains":
            configured_domains,

        "loaded_components":
            loaded_components,

        "platforms": {
            platform:
                integrations

            for platform, integrations
            in sorted(
                platform_index.items()
            )
        },

        "active_custom_domains":
            active_custom_domains,
    },

    "summary": {
        "official_crossed_group_count":
            len(
                official_groups
            ),

        "strong_local_evidence_count":
            strong_count,

        "partial_local_evidence_count":
            partial_count,

        "no_local_evidence_count":
            no_local_count,

        "insufficient_evidence_count":
            insufficient_count,

        "groups_with_any_local_evidence_count":
            (
                strong_count
                + partial_count
            ),

        "groups_without_local_evidence_count":
            no_local_count,
    },

    "correlations":
        results,

    "reference_validation":
        reference_validation,

    "limitations": [
        (
            "Strong local evidence means the official change "
            "has a direct local integration/platform match or "
            "literal code-term evidence. It does not mean the "
            "installation is affected."
        ),

        (
            "Partial local evidence is intentionally weaker "
            "and must not be treated as proof that a feature "
            "is configured or affected."
        ),

        (
            "No local evidence means this scanner found no "
            "relevant evidence in the evidence classes it "
            "inspected; it is not a guarantee that the feature "
            "is absent."
        ),

        (
            "UI-managed content and configuration paths not "
            "represented by the current local evidence sources "
            "may remain uninspected."
        ),
    ],

    "collector_status": {
        **input_status,

        "active_yaml_discovery":
            (
                "ok"
                if active_yaml_paths
                else "unavailable"
            ),

        "active_yaml_read_failures":
            len(
                all_yaml_failures
            ),

        "custom_source_scan_failures":
            len(
                custom_source_scan_failures
            ),

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
    "Dynamic upgrade correlation"
)

print(
    "------------------------------------------"
)

print(
    f"Official crossed groups:      "
    f"{len(official_groups)}"
)

print(
    f"Strong local evidence:        "
    f"{strong_count}"
)

print(
    f"Partial local evidence:       "
    f"{partial_count}"
)

print(
    f"No local evidence:            "
    f"{no_local_count}"
)

print(
    f"Insufficient evidence:        "
    f"{insufficient_count}"
)

print("")

print(
    f"Active YAML paths found:      "
    f"{len(active_yaml_paths)}"
)

print(
    f"Active YAML read failures:    "
    f"{len(all_yaml_failures)}"
)

print(
    f"Custom source scan failures:  "
    f"{len(custom_source_scan_failures)}"
)

print("")

print(
    "Important: correlation evidence is not a "
    "compatibility or safe-to-update verdict."
)

print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
