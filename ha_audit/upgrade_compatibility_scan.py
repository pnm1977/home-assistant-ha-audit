import io
import json
import os
import re
import tokenize
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

QUALITY_FILE = (
    "/config/quality_audit.json"
)

UPGRADE_IMPACT_FILE = (
    "/config/upgrade_impact_audit.json"
)

OUTPUT_FILE = (
    "/config/upgrade_compatibility_audit.json"
)

DEFAULT_CONFIG_ROOT = "/homeassistant"

CORE_2026_9 = (
    2026,
    9,
    0,
)

OFFICIAL_RELEASE_URL = (
    "https://www.home-assistant.io/"
    "blog/2026/09/02/release-20269/"
)

VACUUM_DEPRECATION_URL = (
    "https://developers.home-assistant.io/"
    "blog/2025/07/02/"
    "vacuum-battery-properties-deprecated/"
)


UPDATE_ACTIONS = {
    "update.install",
    "update.skip",
    "update.clear_skipped",
}


# Targeted aid only.
#
# The 2026.9 release notes give
# GetLiveContext and HassTurnOn as examples.
#
# The additional names are known Home Assistant
# LLM tool names and make the local search more useful.
#
# This is deliberately NOT treated as an exhaustive
# list of every possible LLM tool.
KNOWN_UNPREFIXED_LLM_TOOL_NAMES = (
    "GetLiveContext",
    "GetDateTime",
    "HassTurnOn",
    "HassTurnOff",
    "HassBroadcast",
)


# Straight integration-domain checks.
#
# These are useful when a breaking change applies to
# an integration that simply is not present locally.
INTEGRATION_RULES = (
    (
        "core_2026_9_flexit_bacnet",
        "Flexit Nordic (BACnet)",
        "flexit_bacnet",
        (
            "Deprecated fireplace mode switch "
            "removed."
        ),
    ),
    (
        "core_2026_9_knx",
        "KNX",
        "knx",
        (
            "Initial KNX expose value is no longer "
            "sent automatically."
        ),
    ),
    (
        "core_2026_9_unifiprotect_switches",
        "UniFi Protect",
        "unifiprotect",
        (
            "Smart detection switch availability "
            "behaviour changed."
        ),
    ),
    (
        "core_2026_9_unifiprotect_minimum_version",
        "UniFi Protect",
        "unifiprotect",
        (
            "UniFi Protect 7.2.105 or newer "
            "is required."
        ),
    ),
    (
        "core_2026_9_zwave_js_admin_actions",
        "Z-Wave JS",
        "zwave_js",
        (
            "Lock-user and credential actions now "
            "require administrator context."
        ),
    ),
)


# ------------------------------------------------------------
# Home Assistant-friendly YAML loader
# ------------------------------------------------------------

class HALoader(
    yaml.SafeLoader
):
    pass


def unknown_tag(
    loader,
    tag_suffix,
    node,
):
    if isinstance(
        node,
        yaml.ScalarNode,
    ):
        return loader.construct_scalar(
            node
        )

    if isinstance(
        node,
        yaml.SequenceNode,
    ):
        return loader.construct_sequence(
            node
        )

    if isinstance(
        node,
        yaml.MappingNode,
    ):
        return loader.construct_mapping(
            node
        )

    return None


HALoader.add_multi_constructor(
    "!",
    unknown_tag,
)


# ------------------------------------------------------------
# Generic helpers
# ------------------------------------------------------------

def load_json_optional(
    path,
):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            payload = json.load(
                handle
            )

        if isinstance(
            payload,
            dict,
        ):
            return payload

    except Exception:
        pass

    return {}


def safe_load_yaml(
    path,
):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as handle:

            return yaml.load(
                handle,
                Loader=HALoader,
            )

    except Exception:
        return None


def safe_read_text(
    path,
):
    try:
        with open(
            path,
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:

            return handle.read()

    except Exception:
        return ""


def parse_version(
    value,
):
    if value is None:
        return None

    match = re.search(
        r"(\d+)\.(\d+)(?:\.(\d+))?",
        str(
            value
        ),
    )

    if not match:
        return None

    return (
        int(
            match.group(
                1
            )
        ),
        int(
            match.group(
                2
            )
        ),
        int(
            match.group(
                3
            )
            or 0
        ),
    )


def crosses_version(
    installed,
    target,
    threshold,
):
    installed_parsed = (
        parse_version(
            installed
        )
    )

    target_parsed = (
        parse_version(
            target
        )
    )

    if (
        installed_parsed is None
        or target_parsed is None
    ):
        return None

    return (
        installed_parsed
        < threshold
        <= target_parsed
    )


def path_within_root(
    root,
    relative_path,
):
    try:
        root_path = Path(
            root
        ).resolve()

        full_path = (
            root_path
            / relative_path
        ).resolve()

        full_path.relative_to(
            root_path
        )

        return full_path

    except Exception:
        return None


def write_report(
    report,
):
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
# Comment-aware YAML text handling
# ------------------------------------------------------------

def strip_yaml_comment(
    line,
):
    result = []

    single_quote = False
    double_quote = False
    escaped = False

    for char in line:

        if escaped:
            result.append(
                char
            )

            escaped = False
            continue

        if (
            char == "\\"
            and double_quote
        ):
            result.append(
                char
            )

            escaped = True
            continue

        if (
            char == "'"
            and not double_quote
        ):
            single_quote = (
                not single_quote
            )

            result.append(
                char
            )

            continue

        if (
            char == '"'
            and not single_quote
        ):
            double_quote = (
                not double_quote
            )

            result.append(
                char
            )

            continue

        if (
            char == "#"
            and not single_quote
            and not double_quote
        ):
            break

        result.append(
            char
        )

    return "".join(
        result
    )


def active_noncomment_lines(
    text,
):
    for (
        line_number,
        raw_line,
    ) in enumerate(
        text.splitlines(),
        start=1,
    ):

        if raw_line.lstrip().startswith(
            "#"
        ):
            continue

        line = strip_yaml_comment(
            raw_line
        )

        if not line.strip():
            continue

        yield (
            line_number,
            line,
        )


# ------------------------------------------------------------
# Recursive YAML traversal
# ------------------------------------------------------------

def walk_nodes(
    value,
    path=(),
):
    yield (
        path,
        value,
    )

    if isinstance(
        value,
        dict,
    ):

        for (
            key,
            child,
        ) in value.items():

            yield from walk_nodes(
                child,
                path
                + (
                    str(
                        key
                    ),
                ),
            )

    elif isinstance(
        value,
        list,
    ):

        for (
            index,
            child,
        ) in enumerate(
            value
        ):

            yield from walk_nodes(
                child,
                path
                + (
                    index,
                ),
            )


def structural_scope(
    path,
    relative_path,
):
    parts = {
        str(
            part
        ).lower()
        for part in path
        if isinstance(
            part,
            str,
        )
    }

    if (
        "automation" in parts
        or "automations" in parts
    ):
        return "automation"

    if (
        "script" in parts
        or "scripts" in parts
    ):
        return "script"

    lower_path = (
        str(
            relative_path
        )
        .lower()
        .replace(
            "\\",
            "/",
        )
    )

    name = Path(
        lower_path
    ).name

    if (
        name
        == "automations.yaml"
        or "/automations/"
        in lower_path
    ):
        return "automation"

    if (
        name
        == "scripts.yaml"
        or "/scripts/"
        in lower_path
    ):
        return "script"

    return (
        "other_active_yaml"
    )


# ------------------------------------------------------------
# LLM prompt evidence
# ------------------------------------------------------------

def find_token_lines(
    text,
    tokens,
):
    patterns = {
        token:
            re.compile(
                rf"(?<![A-Za-z0-9_])"
                rf"{re.escape(token)}\b"
            )
        for token in tokens
    }

    matches = []

    for (
        line_number,
        line,
    ) in active_noncomment_lines(
        text
    ):

        for (
            token,
            pattern,
        ) in patterns.items():

            if pattern.search(
                line
            ):
                matches.append(
                    {
                        "line":
                            line_number,

                        "token":
                            token,
                    }
                )

    return matches


# ------------------------------------------------------------
# Persistent Notification evidence
# ------------------------------------------------------------

def normalise_update_types(
    value,
):
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        return [
            value
            .strip()
            .lower()
        ]

    if isinstance(
        value,
        list,
    ):
        return sorted(
            {
                str(
                    item
                )
                .strip()
                .lower()

                for item
                in value

                if item
                is not None
            }
        )

    return [
        str(
            value
        )
        .strip()
        .lower()
    ]


def find_persistent_notification_triggers(
    document,
    relative_path,
):
    findings = []

    for (
        path,
        node,
    ) in walk_nodes(
        document
    ):

        if not isinstance(
            node,
            dict,
        ):
            continue

        trigger_type = node.get(
            "trigger",
            node.get(
                "platform"
            ),
        )

        if (
            str(
                trigger_type
                or ""
            )
            .strip()
            .lower()
            != "persistent_notification"
        ):
            continue

        update_types = (
            normalise_update_types(
                node.get(
                    "update_type"
                )
            )
        )

        findings.append(
            {
                "file":
                    relative_path,

                "structure_path":
                    [
                        str(
                            part
                        )
                        for part
                        in path
                    ],

                "scope":
                    structural_scope(
                        path,
                        relative_path,
                    ),

                "update_types":
                    update_types,

                "explicit_update_type":
                    (
                        "update_type"
                        in node
                    ),

                "added_without_updated":
                    (
                        "added"
                        in update_types

                        and "updated"
                        not in update_types
                    ),
            }
        )

    return findings


# ------------------------------------------------------------
# Update action evidence
# ------------------------------------------------------------

def find_update_actions(
    document,
    relative_path,
):
    findings = []

    for (
        path,
        node,
    ) in walk_nodes(
        document
    ):

        if not isinstance(
            node,
            dict,
        ):
            continue

        action = str(
            node.get(
                "action",
                node.get(
                    "service"
                ),
            )
            or ""
        )

        action = (
            action
            .strip()
            .lower()
        )

        if (
            action
            not in UPDATE_ACTIONS
        ):
            continue

        findings.append(
            {
                "file":
                    relative_path,

                "structure_path":
                    [
                        str(
                            part
                        )
                        for part
                        in path
                    ],

                "scope":
                    structural_scope(
                        path,
                        relative_path,
                    ),

                "action":
                    action,
            }
        )

    return findings


# ------------------------------------------------------------
# Platform evidence from upgrade_impact_audit.json
# ------------------------------------------------------------

def get_platform_integrations(
    impact,
    platform_name,
):
    section = impact.get(
        "platform_usage",
        {},
    )

    if not isinstance(
        section,
        dict,
    ):
        return []

    platforms = section.get(
        "platforms",
        [],
    )

    if not isinstance(
        platforms,
        list,
    ):
        return []

    for item in platforms:

        if not isinstance(
            item,
            dict,
        ):
            continue

        if (
            item.get(
                "platform"
            )
            != platform_name
        ):
            continue

        integrations = item.get(
            "integrations",
            [],
        )

        if not isinstance(
            integrations,
            list,
        ):
            return []

        return sorted(
            {
                str(
                    integration
                )
                for integration
                in integrations
                if integration
            }
        )

    return []


# ------------------------------------------------------------
# Custom integration source evidence
# ------------------------------------------------------------

def scan_python_name_token(
    root,
    name,
):
    matches = []

    root_path = Path(
        root
    )

    if not root_path.is_dir():
        return matches

    for path in sorted(
        root_path.rglob(
            "*.py"
        )
    ):

        if (
            "__pycache__"
            in path.parts
        ):
            continue

        try:
            if (
                path.stat().st_size
                > 2_000_000
            ):
                continue

            text = safe_read_text(
                path
            )

            if not text:
                continue

            lines = text.splitlines()

            tokens = (
                tokenize.generate_tokens(
                    io.StringIO(
                        text
                    ).readline
                )
            )

            seen_lines = set()

            for token in tokens:

                if (
                    token.type
                    != tokenize.NAME
                    or token.string
                    != name
                ):
                    continue

                line_number = (
                    token.start[
                        0
                    ]
                )

                if (
                    line_number
                    in seen_lines
                ):
                    continue

                seen_lines.add(
                    line_number
                )

                source_line = (
                    lines[
                        line_number
                        - 1
                    ]
                )

                kind = (
                    "name_reference"
                )

                if re.search(
                    rf"\b(?:async\s+)?"
                    rf"def\s+"
                    rf"{re.escape(name)}"
                    rf"\s*\(",
                    source_line,
                ):
                    kind = (
                        "property_or_method_definition"
                    )

                matches.append(
                    {
                        "file":
                            str(
                                path
                            ),

                        "line":
                            line_number,

                        "token":
                            name,

                        "kind":
                            kind,
                    }
                )

        except (
            OSError,
            tokenize.TokenError,
            IndentationError,
            SyntaxError,
        ):
            continue

    return matches


# ------------------------------------------------------------
# Load existing HA Audit evidence
# ------------------------------------------------------------

quality = load_json_optional(
    QUALITY_FILE
)

impact = load_json_optional(
    UPGRADE_IMPACT_FILE
)


pending = impact.get(
    "pending_updates",
    {},
)

pending_items = (
    pending.get(
        "updates",
        [],
    )
    if isinstance(
        pending,
        dict,
    )
    else []
)

if not isinstance(
    pending_items,
    list,
):
    pending_items = []


pending_core = next(
    (
        item
        for item
        in pending_items

        if isinstance(
            item,
            dict,
        )

        and item.get(
            "category"
        )
        == "core"
    ),
    None,
)


installed_core = (
    pending_core.get(
        "installed_version"
    )
    if pending_core
    else None
)


target_core = (
    pending_core.get(
        "latest_version"
    )
    if pending_core
    else None
)


applicable = crosses_version(
    installed_core,
    target_core,
    CORE_2026_9,
)


# ------------------------------------------------------------
# Stop cleanly when the 2026.9 rule pack does not apply
# ------------------------------------------------------------

if applicable is not True:

    if not pending_core:
        reason = (
            "no_pending_core_update"
        )

    elif applicable is None:
        reason = (
            "core_version_unavailable_or_unparseable"
        )

    else:
        reason = (
            "pending_window_does_not_cross_2026_9"
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
                "deterministic_upgrade_compatibility",

            "local_evidence_only":
                True,

            "external_fetch_performed":
                False,

            "readiness_verdict_produced":
                False,

            "rule_pack":
                "home_assistant_core_2026_9",

            "rule_pack_basis":
                (
                    "official Home Assistant "
                    "2026.9 release notes"
                ),

            "official_release_url":
                OFFICIAL_RELEASE_URL,
        },

        "core_upgrade_window": {
            "pending":
                bool(
                    pending_core
                ),

            "installed_version":
                installed_core,

            "target_version":
                target_core,

            "crosses_2026_9":
                applicable,

            "reason":
                reason,
        },

        "summary": {
            "rule_count":
                0,

            "status_counts":
                {},

            "review_required_count":
                0,

            "manual_review_count":
                0,
        },

        "review_required":
            [],

        "manual_review":
            [],

        "results":
            [],
    }

    write_report(
        report
    )

    print("")

    print(
        "Upgrade compatibility audit"
    )

    print(
        "------------------------------------------"
    )

    print(
        f"Core upgrade:                "
        f"{installed_core} -> {target_core}"
    )

    print(
        "Core 2026.9 rule pack:       "
        "NOT APPLICABLE"
    )

    print(
        "No safe-to-update verdict is produced."
    )

    print("")

    print(
        f"Detailed report: "
        f"{OUTPUT_FILE}"
    )

    raise SystemExit(
        0
    )


# ------------------------------------------------------------
# Local evidence sets
# ------------------------------------------------------------

config_info = impact.get(
    "home_assistant_config",
    {},
)

if not isinstance(
    config_info,
    dict,
):
    config_info = {}


config_root = (
    config_info.get(
        "root"
    )
    or DEFAULT_CONFIG_ROOT
)


configuration_tree = quality.get(
    "configuration_tree",
    {},
)

if not isinstance(
    configuration_tree,
    dict,
):
    configuration_tree = {}


active_yaml = (
    configuration_tree.get(
        "active_yaml",
        [],
    )
)

if not isinstance(
    active_yaml,
    list,
):
    active_yaml = []


active_yaml = sorted(
    {
        str(
            path
        )
        for path
        in active_yaml
        if path
    }
)


inventory = impact.get(
    "impact_inventory",
    {},
)

if not isinstance(
    inventory,
    dict,
):
    inventory = {}


configured_domains = set(
    inventory.get(
        "configured_integration_domains",
        [],
    )
    if isinstance(
        inventory.get(
            "configured_integration_domains",
            [],
        ),
        list,
    )
    else []
)


loaded_component_roots = set(
    inventory.get(
        "loaded_component_roots",
        [],
    )
    if isinstance(
        inventory.get(
            "loaded_component_roots",
            [],
        ),
        list,
    )
    else []
)


custom_active_domains = set(
    inventory.get(
        "custom_active_domains",
        [],
    )
    if isinstance(
        inventory.get(
            "custom_active_domains",
            [],
        ),
        list,
    )
    else []
)


loaded_section = impact.get(
    "loaded_components",
    {},
)

if not isinstance(
    loaded_section,
    dict,
):
    loaded_section = {}


loaded_components = set(
    loaded_section.get(
        "components",
        [],
    )
    if isinstance(
        loaded_section.get(
            "components",
            [],
        ),
        list,
    )
    else []
)


def local_domain_present(
    domain,
):
    return (
        domain
        in configured_domains

        or domain
        in loaded_component_roots

        or domain
        in custom_active_domains
    )


# ------------------------------------------------------------
# Scan active YAML
# ------------------------------------------------------------

yaml_scan_status = (
    "ok"
    if quality
    and active_yaml
    else "unavailable"
)

yaml_read_failures = []

llm_yaml_matches = []

persistent_triggers = []

update_actions = []


for relative_path in active_yaml:

    full_path = path_within_root(
        config_root,
        relative_path,
    )

    if (
        full_path is None
        or not full_path.is_file()
    ):
        yaml_read_failures.append(
            {
                "file":
                    relative_path,

                "reason":
                    "active_yaml_file_unavailable",
            }
        )

        continue

    text = safe_read_text(
        full_path
    )


    for match in find_token_lines(
        text,
        KNOWN_UNPREFIXED_LLM_TOOL_NAMES,
    ):
        llm_yaml_matches.append(
            {
                "file":
                    relative_path,

                **match,
            }
        )


    parsed = safe_load_yaml(
        full_path
    )

    if parsed is None:
        continue


    persistent_triggers.extend(
        find_persistent_notification_triggers(
            parsed,
            relative_path,
        )
    )


    update_actions.extend(
        find_update_actions(
            parsed,
            relative_path,
        )
    )


if (
    yaml_read_failures
    and yaml_scan_status
    == "ok"
):
    yaml_scan_status = (
        "partial"
    )


persistent_risky = [
    item
    for item
    in persistent_triggers
    if item.get(
        "added_without_updated"
    )
]


script_update_actions = [
    item
    for item
    in update_actions
    if item.get(
        "scope"
    )
    == "script"
]


automation_update_actions = [
    item
    for item
    in update_actions
    if item.get(
        "scope"
    )
    == "automation"
]


other_update_actions = [
    item
    for item
    in update_actions
    if item.get(
        "scope"
    )
    == "other_active_yaml"
]


# ------------------------------------------------------------
# Build rule results
# ------------------------------------------------------------

results = []


# ------------------------------------------------------------
# Integration-domain rules
# ------------------------------------------------------------

for (
    rule_id,
    area,
    domain,
    change,
) in INTEGRATION_RULES:

    present = (
        local_domain_present(
            domain
        )
    )

    results.append(
        {
            "id":
                rule_id,

            "area":
                area,

            "change":
                change,

            "local_match":
                present,

            "status":
                (
                    "local_match_manual_review"
                    if present
                    else "no_local_match"
                ),

            "evidence": {
                "integration_domain":
                    domain,

                "configured":
                    (
                        domain
                        in configured_domains
                    ),

                "loaded_component_root":
                    (
                        domain
                        in loaded_component_roots
                    ),

                "active_custom_integration":
                    (
                        domain
                        in custom_active_domains
                    ),
            },

            "note":
                (
                    "The integration is present locally, "
                    "so the documented change requires "
                    "integration-specific review."
                    if present

                    else
                    (
                        "No local integration-domain "
                        "evidence was found."
                    )
                ),
        }
    )


# ------------------------------------------------------------
# LLM API rule
# ------------------------------------------------------------

llm_present = (
    "llm"
    in loaded_components

    or "llm"
    in loaded_component_roots
)


if not llm_present:

    llm_status = (
        "no_local_match"
    )

    llm_note = (
        "The LLM component was not found "
        "in local component evidence."
    )


elif llm_yaml_matches:

    llm_status = (
        "local_match_review_required"
    )

    llm_note = (
        "Known unprefixed LLM tool names were "
        "found in active YAML. Review the matched "
        "custom prompt or configuration before "
        "upgrading."
    )


else:

    llm_status = (
        "local_match_no_active_yaml_usage_found"
    )

    llm_note = (
        "The LLM component is loaded, but no known "
        "unprefixed tool names were found in active "
        "YAML. UI-managed prompt/config-entry content "
        "is deliberately not inspected, so this is "
        "not proof that no custom prompt is affected."
    )


results.append(
    {
        "id":
            "core_2026_9_llm_tool_names",

        "area":
            "LLM APIs",

        "change":
            (
                "LLM tool names are prefixed with "
                "the integration domain. Custom "
                "prompts that name tools directly "
                "may need updating."
            ),

        "local_match":
            llm_present,

        "status":
            llm_status,

        "evidence": {
            "llm_component_loaded":
                llm_present,

            "active_yaml_match_count":
                len(
                    llm_yaml_matches
                ),

            "active_yaml_matches":
                llm_yaml_matches,

            "known_names_checked":
                list(
                    KNOWN_UNPREFIXED_LLM_TOOL_NAMES
                ),

            "ui_managed_prompt_content_inspected":
                False,
        },

        "note":
            llm_note,
    }
)


# ------------------------------------------------------------
# Persistent Notification rule
# ------------------------------------------------------------

persistent_present = (
    "persistent_notification"
    in loaded_components

    or "persistent_notification"
    in loaded_component_roots
)


if not persistent_present:

    persistent_status = (
        "no_local_match"
    )

    persistent_note = (
        "Persistent Notification was not found "
        "in local component evidence."
    )


elif persistent_risky:

    persistent_status = (
        "local_match_review_required"
    )

    persistent_note = (
        "At least one active YAML "
        "persistent-notification trigger explicitly "
        "uses 'added' without 'updated'."
    )


elif (
    yaml_scan_status
    == "unavailable"
):

    persistent_status = (
        "local_match_scan_unavailable"
    )

    persistent_note = (
        "Persistent Notification is present, "
        "but active YAML could not be checked."
    )


else:

    persistent_status = (
        "local_match_no_affected_usage_found"
    )

    persistent_note = (
        "Persistent Notification is present, but "
        "no active YAML trigger was found that "
        "explicitly uses 'added' without 'updated'."
    )


results.append(
    {
        "id":
            "core_2026_9_persistent_notification_updated",

        "area":
            "Persistent Notification",

        "change":
            (
                "Updating an existing persistent "
                "notification now reports update_type "
                "'updated' instead of 'added'."
            ),

        "local_match":
            persistent_present,

        "status":
            persistent_status,

        "evidence": {
            "component_loaded":
                persistent_present,

            "trigger_count":
                len(
                    persistent_triggers
                ),

            "review_candidate_count":
                len(
                    persistent_risky
                ),

            "review_candidates":
                persistent_risky,

            "yaml_scan_status":
                yaml_scan_status,
        },

        "note":
            persistent_note,
    }
)


# ------------------------------------------------------------
# Update rule
# ------------------------------------------------------------

update_integrations = (
    get_platform_integrations(
        impact,
        "update",
    )
)


update_present = (
    "update"
    in loaded_components

    or "update"
    in loaded_component_roots

    or bool(
        update_integrations
    )
)


if not update_present:

    update_status = (
        "no_local_match"
    )

    update_note = (
        "The Update platform was not found "
        "in local evidence."
    )


elif script_update_actions:

    update_status = (
        "local_match_review_required"
    )

    update_note = (
        "One or more scripts call an affected "
        "Update action. In Core 2026.9 these can "
        "fail when a non-admin user starts the "
        "script."
    )


elif other_update_actions:

    update_status = (
        "local_match_manual_review"
    )

    update_note = (
        "Update actions were found in active YAML "
        "whose automation/script scope could not "
        "be proven."
    )


elif (
    yaml_scan_status
    == "unavailable"
):

    update_status = (
        "local_match_scan_unavailable"
    )

    update_note = (
        "The Update platform is present, but "
        "active YAML was not checked."
    )


else:

    update_status = (
        "local_match_no_affected_usage_found"
    )

    update_note = (
        "No affected Update action was found in "
        "script scope. Update actions found only "
        "in automations are not affected by this "
        "permission change."
    )


results.append(
    {
        "id":
            "core_2026_9_update_admin_context",

        "area":
            "Update",

        "change":
            (
                "Installing, skipping, and clearing "
                "a skipped update now require "
                "administrator context. Automations "
                "are unaffected; manually started "
                "scripts can be affected."
            ),

        "local_match":
            update_present,

        "status":
            update_status,

        "evidence": {
            "platform_integrations":
                update_integrations,

            "script_action_count":
                len(
                    script_update_actions
                ),

            "script_actions":
                script_update_actions,

            "automation_action_count":
                len(
                    automation_update_actions
                ),

            "automation_actions":
                automation_update_actions,

            "other_scope_action_count":
                len(
                    other_update_actions
                ),

            "other_scope_actions":
                other_update_actions,

            "yaml_scan_status":
                yaml_scan_status,
        },

        "note":
            update_note,
    }
)


# ------------------------------------------------------------
# Vacuum rule
# ------------------------------------------------------------

vacuum_integrations = (
    get_platform_integrations(
        impact,
        "vacuum",
    )
)


active_custom_vacuum_integrations = sorted(
    set(
        vacuum_integrations
    )
    & custom_active_domains
)


vacuum_source_matches = []

vacuum_source_scan_failures = []


for domain in (
    active_custom_vacuum_integrations
):

    integration_root = (
        Path(
            config_root
        )
        / "custom_components"
        / domain
    )

    if not integration_root.is_dir():

        vacuum_source_scan_failures.append(
            {
                "domain":
                    domain,

                "reason":
                    (
                        "custom_integration_"
                        "directory_unavailable"
                    ),
            }
        )

        continue


    for match in scan_python_name_token(
        integration_root,
        "battery_level",
    ):

        try:
            relative_file = str(
                Path(
                    match[
                        "file"
                    ]
                )
                .resolve()
                .relative_to(
                    Path(
                        config_root
                    ).resolve()
                )
            )

        except Exception:
            relative_file = (
                match[
                    "file"
                ]
            )


        vacuum_source_matches.append(
            {
                "domain":
                    domain,

                **match,

                "file":
                    relative_file,
            }
        )


vacuum_present = bool(
    vacuum_integrations
)


if not vacuum_present:

    vacuum_status = (
        "no_local_match"
    )

    vacuum_note = (
        "The Vacuum platform was not found "
        "in local evidence."
    )


elif vacuum_source_matches:

    vacuum_status = (
        "local_match_review_required"
    )

    vacuum_note = (
        "An active custom vacuum integration "
        "contains battery_level Python name "
        "references. Review the listed source "
        "locations."
    )


elif vacuum_source_scan_failures:

    vacuum_status = (
        "local_match_scan_partial"
    )

    vacuum_note = (
        "One or more active custom vacuum "
        "integration source trees could not "
        "be fully checked."
    )


elif active_custom_vacuum_integrations:

    vacuum_status = (
        "local_match_no_affected_custom_usage_found"
    )

    vacuum_note = (
        "Active custom vacuum integrations are "
        "present, but no battery_level Python "
        "name reference was found in their source."
    )


else:

    vacuum_status = (
        "local_match_core_integrations_only"
    )

    vacuum_note = (
        "The Vacuum platform is present, but no "
        "active custom integration provides it. "
        "The official notes state Core vacuum "
        "integrations were already migrated."
    )


results.append(
    {
        "id":
            "core_2026_9_vacuum_battery_level",

        "area":
            "Vacuum",

        "change":
            (
                "The deprecated battery_level "
                "property was removed from the "
                "base vacuum entity. A custom "
                "integration still using it can "
                "lose battery-level reporting."
            ),

        "local_match":
            vacuum_present,

        "status":
            vacuum_status,

        "evidence": {
            "vacuum_platform_integrations":
                vacuum_integrations,

            "active_custom_vacuum_integrations":
                active_custom_vacuum_integrations,

            "battery_level_match_count":
                len(
                    vacuum_source_matches
                ),

            "battery_level_matches":
                vacuum_source_matches,

            "source_scan_failures":
                vacuum_source_scan_failures,
        },

        "note":
            vacuum_note,
    }
)


# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

status_counts = Counter(
    item.get(
        "status",
        "unknown",
    )
    for item
    in results
)


review_required = [
    item
    for item
    in results
    if item.get(
        "status"
    )
    == "local_match_review_required"
]


manual_review_statuses = {
    "local_match_manual_review",
    "local_match_scan_unavailable",
    "local_match_scan_partial",
}


manual_review = [
    item
    for item
    in results
    if item.get(
        "status"
    )
    in manual_review_statuses
]


report = {
    "audit_version":
        VERSION,

    "generated_at":
        datetime.now(
            timezone.utc
        ).isoformat(),

    "scope": {
        "phase":
            "deterministic_upgrade_compatibility",

        "local_evidence_only":
            True,

        "external_fetch_performed":
            False,

        "readiness_verdict_produced":
            False,

        "rule_pack":
            "home_assistant_core_2026_9",

        "rule_pack_basis":
            (
                "official Home Assistant "
                "2026.9 release notes"
            ),

        "official_release_url":
            OFFICIAL_RELEASE_URL,

        "vacuum_deprecation_reference":
            VACUUM_DEPRECATION_URL,

        "note":
            (
                "This scanner applies an embedded "
                "Core 2026.9 rule pack to local "
                "evidence. It records matches and "
                "review candidates; it does not "
                "declare an upgrade safe or unsafe."
            ),
    },

    "core_upgrade_window": {
        "pending":
            True,

        "installed_version":
            installed_core,

        "target_version":
            target_core,

        "crosses_2026_9":
            True,
    },

    "coverage": {
        "quality_report_available":
            bool(
                quality
            ),

        "upgrade_impact_report_available":
            bool(
                impact
            ),

        "active_yaml_file_count":
            len(
                active_yaml
            ),

        "active_yaml_scan_status":
            yaml_scan_status,

        "active_yaml_read_failures":
            yaml_read_failures,

        "ui_managed_prompt_content_inspected":
            False,

        "custom_component_source_scope":
            (
                "Only active custom integrations "
                "currently providing the vacuum "
                "platform are source-scanned, and "
                "only relevant Python name locations "
                "are recorded."
            ),
    },

    "summary": {
        "rule_count":
            len(
                results
            ),

        "status_counts":
            dict(
                sorted(
                    status_counts.items()
                )
            ),

        "review_required_count":
            len(
                review_required
            ),

        "manual_review_count":
            len(
                manual_review
            ),
    },

    "review_required":
        review_required,

    "manual_review":
        manual_review,

    "results":
        results,
}


write_report(
    report
)


# ------------------------------------------------------------
# Console output
# ------------------------------------------------------------

print("")

print(
    "Upgrade compatibility audit"
)

print(
    "------------------------------------------"
)

print(
    f"Core upgrade:                "
    f"{installed_core} -> {target_core}"
)

print(
    "Core 2026.9 rule pack:       "
    "APPLICABLE"
)

print(
    f"Rules checked:               "
    f"{len(results)}"
)

print(
    f"Review required:             "
    f"{len(review_required)}"
)

print(
    f"Manual review:               "
    f"{len(manual_review)}"
)

print(
    f"Active YAML scan:            "
    f"{yaml_scan_status}"
)

print(
    f"Active YAML files:           "
    f"{len(active_yaml)}"
)

print("")

print(
    "No safe-to-update verdict is produced."
)

print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
