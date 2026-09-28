import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
import websocket


VERSION = os.environ.get(
    "HA_AUDIT_VERSION",
    "unknown",
)

TOKEN = os.environ["SUPERVISOR_TOKEN"]

SUPERVISOR = "http://supervisor"
WS_URL = "ws://supervisor/core/websocket"

UPDATE_READINESS_FILE = "/config/update_readiness_audit.json"
OUTPUT_FILE = "/config/upgrade_impact_audit.json"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
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


def get_json(
    path,
    timeout=30,
):
    response = requests.get(
        f"{SUPERVISOR}{path}",
        headers=HEADERS,
        timeout=timeout,
    )

    response.raise_for_status()

    payload = response.json()

    if (
        isinstance(
            payload,
            dict,
        )
        and "data" in payload
    ):
        return payload[
            "data"
        ]

    return payload


def safe_collect(function):
    try:
        return {
            "status": "ok",
            "data": function(),
        }

    except Exception as error:
        return {
            "status": "error",
            "error": str(
                error
            ),
        }


def normalise_text(value):
    return re.sub(
        r"[^a-z0-9]+",
        "",
        str(
            value
            or ""
        ).strip().lower(),
    )


def update_entity_slug(
    entity_id,
):
    slug = str(
        entity_id
        or ""
    )

    if slug.startswith(
        "update."
    ):
        slug = slug[
            len("update.") :
        ]

    if slug.endswith(
        "_update"
    ):
        slug = slug[
            : -len("_update")
        ]

    return slug


def component_tokens(
    component,
):
    text = str(
        component
        or ""
    ).strip()

    if not text:
        return []

    return [
        token
        for token
        in text.split(".")
        if token
    ]


def domain_loaded_by_components(
    domain,
    loaded_components,
):
    domain = str(
        domain
        or ""
    ).strip()

    if not domain:
        return False

    for component in loaded_components:
        component = str(
            component
        )

        if (
            component
            == domain
        ):
            return True

        if component.startswith(
            f"{domain}."
        ):
            return True

        if component.endswith(
            f".{domain}"
        ):
            return True

    return False


def find_ha_config_root():
    candidates = []

    explicit = os.environ.get(
        "HA_CONFIG_ROOT"
    )

    if explicit:
        candidates.append(
            explicit
        )

    candidates.extend(
        [
            "/homeassistant",
            "/config",
        ]
    )

    checked = []
    seen = set()

    for candidate in candidates:
        if candidate in seen:
            continue

        seen.add(
            candidate
        )

        checked.append(
            candidate
        )

        root = Path(
            candidate
        )

        if not root.is_dir():
            continue

        if (
            (
                root
                / "configuration.yaml"
            ).is_file()
            or (
                root
                / "custom_components"
            ).is_dir()
        ):
            return {
                "status": "ok",
                "path": str(
                    root
                ),
                "checked": checked,
            }

    return {
        "status": "unavailable",
        "path": None,
        "checked": checked,
    }


# ------------------------------------------------------------
# Home Assistant WebSocket evidence
# ------------------------------------------------------------

def collect_config_entries():
    ws = websocket.create_connection(
        WS_URL,
        timeout=30,
        suppress_origin=True,
    )

    try:
        greeting = json.loads(
            ws.recv()
        )

        if (
            greeting.get(
                "type"
            )
            != "auth_required"
        ):
            raise RuntimeError(
                "Unexpected WebSocket "
                "greeting: "
                f"{greeting}"
            )

        ws.send(
            json.dumps(
                {
                    "type": "auth",
                    "access_token": TOKEN,
                }
            )
        )

        authentication = json.loads(
            ws.recv()
        )

        if (
            authentication.get(
                "type"
            )
            != "auth_ok"
        ):
            raise RuntimeError(
                "WebSocket authentication "
                "failed: "
                f"{authentication}"
            )

        ws.send(
            json.dumps(
                {
                    "id": 1,
                    "type":
                        "config_entries/get",
                }
            )
        )

        while True:
            response = json.loads(
                ws.recv()
            )

            if (
                response.get(
                    "type"
                )
                != "result"
            ):
                continue

            if (
                response.get(
                    "id"
                )
                != 1
            ):
                continue

            if not response.get(
                "success"
            ):
                raise RuntimeError(
                    "config_entries/get "
                    "failed: "
                    f"{response.get('error')}"
                )

            result = response.get(
                "result",
                [],
            )

            if not isinstance(
                result,
                list,
            ):
                raise RuntimeError(
                    "config_entries/get "
                    "returned an unexpected "
                    "result shape"
                )

            return result

    finally:
        ws.close()


# ------------------------------------------------------------
# Custom integration manifests
# ------------------------------------------------------------

def scan_custom_integrations(
    config_root,
):
    result = {
        "custom_components_root":
            None,
        "directory_exists":
            False,
        "scan_errors":
            [],
        "integrations":
            [],
    }

    if not config_root:
        return result

    custom_root = (
        Path(
            config_root
        )
        / "custom_components"
    )

    result[
        "custom_components_root"
    ] = str(
        custom_root
    )

    if not custom_root.is_dir():
        return result

    result[
        "directory_exists"
    ] = True

    try:
        directories = sorted(
            [
                item
                for item
                in custom_root.iterdir()
                if item.is_dir()
            ],
            key=lambda item:
                item.name.lower(),
        )

    except Exception as error:
        result[
            "scan_errors"
        ].append(
            {
                "path":
                    str(
                        custom_root
                    ),
                "error":
                    str(
                        error
                    ),
            }
        )

        return result

    for directory in directories:
        manifest_path = (
            directory
            / "manifest.json"
        )

        item = {
            "directory":
                directory.name,

            "manifest_path":
                str(
                    manifest_path
                ),

            "manifest_present":
                manifest_path.is_file(),

            "manifest_valid":
                False,

            "manifest_error":
                None,

            "domain":
                None,

            "name":
                None,

            "version":
                None,

            "documentation":
                None,

            "issue_tracker":
                None,

            "integration_type":
                None,

            "iot_class":
                None,

            "config_flow":
                None,

            "codeowners":
                [],

            "dependencies":
                [],

            "after_dependencies":
                [],

            "requirements":
                [],

            "directory_domain_match":
                None,
        }

        if not manifest_path.is_file():
            result[
                "integrations"
            ].append(
                item
            )

            continue

        try:
            with manifest_path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                manifest = json.load(
                    handle
                )

            if not isinstance(
                manifest,
                dict,
            ):
                raise ValueError(
                    "manifest root is "
                    "not an object"
                )

            item.update(
                {
                    "manifest_valid":
                        True,

                    "domain":
                        manifest.get(
                            "domain"
                        ),

                    "name":
                        manifest.get(
                            "name"
                        ),

                    "version":
                        manifest.get(
                            "version"
                        ),

                    "documentation":
                        manifest.get(
                            "documentation"
                        ),

                    "issue_tracker":
                        manifest.get(
                            "issue_tracker"
                        ),

                    "integration_type":
                        manifest.get(
                            "integration_type"
                        ),

                    "iot_class":
                        manifest.get(
                            "iot_class"
                        ),

                    "config_flow":
                        manifest.get(
                            "config_flow"
                        ),
                }
            )

            for key in (
                "codeowners",
                "dependencies",
                "after_dependencies",
                "requirements",
            ):
                value = manifest.get(
                    key,
                    [],
                )

                item[
                    key
                ] = (
                    value
                    if isinstance(
                        value,
                        list,
                    )
                    else []
                )

            domain = item.get(
                "domain"
            )

            item[
                "directory_domain_match"
            ] = (
                str(
                    domain
                )
                == directory.name
                if domain
                else False
            )

        except Exception as error:
            item[
                "manifest_error"
            ] = str(
                error
            )

        result[
            "integrations"
        ].append(
            item
        )

    return result


# ------------------------------------------------------------
# Collect local evidence
# ------------------------------------------------------------

components_result = safe_collect(
    lambda: get_json(
        "/core/api/components"
    )
)

config_entries_result = safe_collect(
    collect_config_entries
)

config_root_result = (
    find_ha_config_root()
)

custom_scan_result = safe_collect(
    lambda:
        scan_custom_integrations(
            config_root_result.get(
                "path"
            )
        )
)

update_readiness = load_json_optional(
    UPDATE_READINESS_FILE
)


# ------------------------------------------------------------
# Loaded component evidence
# ------------------------------------------------------------

loaded_components = (
    components_result.get(
        "data",
        [],
    )
    if components_result.get(
        "status"
    )
    == "ok"
    else []
)

if not isinstance(
    loaded_components,
    list,
):
    loaded_components = []

loaded_components = sorted(
    {
        str(
            component
        )
        for component
        in loaded_components
        if component
    }
)

bare_loaded_components = sorted(
    [
        component
        for component
        in loaded_components
        if "."
        not in component
    ]
)

component_token_candidates = sorted(
    {
        token
        for component
        in loaded_components
        for token
        in component_tokens(
            component
        )
    }
)


# ------------------------------------------------------------
# Config-entry evidence
# ------------------------------------------------------------

config_entries = (
    config_entries_result.get(
        "data",
        [],
    )
    if config_entries_result.get(
        "status"
    )
    == "ok"
    else []
)

if not isinstance(
    config_entries,
    list,
):
    config_entries = []

entries_by_domain = defaultdict(
    list
)

entry_state_counts = Counter()

for entry in config_entries:
    if not isinstance(
        entry,
        dict,
    ):
        continue

    domain = entry.get(
        "domain"
    )

    state = str(
        entry.get(
            "state"
        )
        or "unknown"
    )

    disabled = (
        entry.get(
            "disabled_by"
        )
        is not None
    )

    entry_state_counts[
        state
    ] += 1

    if domain:
        entries_by_domain[
            str(
                domain
            )
        ].append(
            {
                "state":
                    state,

                "disabled":
                    disabled,
            }
        )

config_domain_details = []

for domain in sorted(
    entries_by_domain
):
    entries = (
        entries_by_domain[
            domain
        ]
    )

    state_counts = Counter(
        entry.get(
            "state",
            "unknown",
        )
        for entry
        in entries
    )

    config_domain_details.append(
        {
            "domain":
                domain,

            "entry_count":
                len(
                    entries
                ),

            "enabled_count":
                sum(
                    1
                    for entry
                    in entries
                    if not entry.get(
                        "disabled"
                    )
                ),

            "disabled_count":
                sum(
                    1
                    for entry
                    in entries
                    if entry.get(
                        "disabled"
                    )
                ),

            "state_counts":
                dict(
                    sorted(
                        state_counts.items()
                    )
                ),
        }
    )

configured_domains = sorted(
    entries_by_domain
)

configured_domain_set = set(
    configured_domains
)


# ------------------------------------------------------------
# Pending update and HACS evidence
# ------------------------------------------------------------

readiness_updates = (
    update_readiness.get(
        "updates",
        {},
    )
)

if not isinstance(
    readiness_updates,
    dict,
):
    readiness_updates = {}

available_updates = (
    readiness_updates.get(
        "available",
        [],
    )
)

all_updates = (
    readiness_updates.get(
        "all",
        [],
    )
)

if not isinstance(
    available_updates,
    list,
):
    available_updates = []

if not isinstance(
    all_updates,
    list,
):
    all_updates = []

pending_updates = []

for item in available_updates:
    if not isinstance(
        item,
        dict,
    ):
        continue

    pending_updates.append(
        {
            "entity_id":
                item.get(
                    "entity_id"
                ),

            "category":
                item.get(
                    "category"
                ),

            "title":
                (
                    item.get(
                        "title"
                    )
                    or item.get(
                        "name"
                    )
                ),

            "installed_version":
                item.get(
                    "installed_version"
                ),

            "latest_version":
                item.get(
                    "latest_version"
                ),

            "release_url":
                item.get(
                    "release_url"
                ),

            "platform":
                item.get(
                    "platform"
                ),
        }
    )

hacs_updates = []

for item in all_updates:
    if not isinstance(
        item,
        dict,
    ):
        continue

    if (
        item.get(
            "platform"
        )
        != "hacs"
    ):
        continue

    hacs_updates.append(
        {
            "entity_id":
                item.get(
                    "entity_id"
                ),

            "state":
                item.get(
                    "state"
                ),

            "name":
                item.get(
                    "name"
                ),

            "title":
                item.get(
                    "title"
                ),

            "device":
                item.get(
                    "device"
                ),

            "installed_version":
                item.get(
                    "installed_version"
                ),

            "latest_version":
                item.get(
                    "latest_version"
                ),

            "release_url":
                item.get(
                    "release_url"
                ),
        }
    )

hacs_updates.sort(
    key=lambda item:
        str(
            item.get(
                "entity_id"
            )
            or ""
        )
)


# ------------------------------------------------------------
# Enrich custom integration evidence
# ------------------------------------------------------------

custom_payload = (
    custom_scan_result.get(
        "data",
        {},
    )
    if custom_scan_result.get(
        "status"
    )
    == "ok"
    else {}
)

if not isinstance(
    custom_payload,
    dict,
):
    custom_payload = {}

custom_integrations = (
    custom_payload.get(
        "integrations",
        [],
    )
)

if not isinstance(
    custom_integrations,
    list,
):
    custom_integrations = []

for integration in custom_integrations:
    if not isinstance(
        integration,
        dict,
    ):
        continue

    domain = str(
        integration.get(
            "domain"
        )
        or integration.get(
            "directory"
        )
        or ""
    )

    integration[
        "loaded"
    ] = domain_loaded_by_components(
        domain,
        loaded_components,
    )

    entries = (
        entries_by_domain.get(
            domain,
            [],
        )
    )

    enabled_entry_count = sum(
        1
        for entry
        in entries
        if not entry.get(
            "disabled"
        )
    )

    disabled_entry_count = sum(
        1
        for entry
        in entries
        if entry.get(
            "disabled"
        )
    )

    integration[
        "config_entry_count"
    ] = len(
        entries
    )

    integration[
        "enabled_config_entry_count"
    ] = enabled_entry_count

    integration[
        "disabled_config_entry_count"
    ] = disabled_entry_count

    integration[
        "configured_via_entry"
    ] = (
        domain
        in configured_domain_set
    )

    integration[
        "config_entry_states"
    ] = dict(
        sorted(
            Counter(
                entry.get(
                    "state",
                    "unknown",
                )
                for entry
                in entries
            ).items()
        )
    )

    integration[
        "in_use_evidence"
    ] = bool(
        integration.get(
            "loaded"
        )
        or enabled_entry_count > 0
    )

    domain_norm = normalise_text(
        domain
    )

    name_norm = normalise_text(
        integration.get(
            "name"
        )
    )

    matches = []

    for update in hacs_updates:
        slug = update_entity_slug(
            update.get(
                "entity_id"
            )
        )

        update_names = {
            normalise_text(
                update.get(
                    "title"
                )
            ),
            normalise_text(
                update.get(
                    "name"
                )
            ),
            normalise_text(
                update.get(
                    "device"
                )
            ),
        }

        update_names.discard(
            ""
        )

        match_type = None

        if (
            domain
            and slug
            == domain
        ):
            match_type = (
                "exact_domain_slug"
            )

        elif (
            domain_norm
            and normalise_text(
                slug
            )
            == domain_norm
        ):
            match_type = (
                "normalised_domain_slug"
            )

        elif (
            name_norm
            and name_norm
            in update_names
        ):
            match_type = (
                "exact_normalised_name"
            )

        if match_type:
            matches.append(
                {
                    "match_type":
                        match_type,

                    "entity_id":
                        update.get(
                            "entity_id"
                        ),

                    "state":
                        update.get(
                            "state"
                        ),

                    "installed_version":
                        update.get(
                            "installed_version"
                        ),

                    "latest_version":
                        update.get(
                            "latest_version"
                        ),

                    "release_url":
                        update.get(
                            "release_url"
                        ),
                }
            )

    integration[
        "hacs_update_matches"
    ] = matches

    integration[
        "hacs_managed_evidence"
    ] = bool(
        matches
    )

custom_integrations.sort(
    key=lambda item:
        str(
            item.get(
                "domain"
            )
            or item.get(
                "directory"
            )
            or ""
        ).lower()
)


# ------------------------------------------------------------
# Derived custom integration groups
# ------------------------------------------------------------

custom_in_use = [
    item
    for item
    in custom_integrations
    if item.get(
        "in_use_evidence"
    )
]

custom_not_in_use = [
    item
    for item
    in custom_integrations
    if not item.get(
        "in_use_evidence"
    )
]

custom_hacs_matched = [
    item
    for item
    in custom_integrations
    if item.get(
        "hacs_managed_evidence"
    )
]

custom_manifest_invalid = [
    item
    for item
    in custom_integrations
    if not item.get(
        "manifest_valid"
    )
]

custom_missing_version = [
    item
    for item
    in custom_integrations
    if item.get(
        "manifest_valid"
    )
    and not item.get(
        "version"
    )
]

custom_domain_mismatch = [
    item
    for item
    in custom_integrations
    if item.get(
        "manifest_valid"
    )
    and item.get(
        "directory_domain_match"
    )
    is False
]

custom_domains = sorted(
    {
        str(
            item.get(
                "domain"
            )
            or item.get(
                "directory"
            )
        )
        for item
        in custom_integrations
        if (
            item.get(
                "domain"
            )
            or item.get(
                "directory"
            )
        )
    }
)

custom_in_use_domains = sorted(
    {
        str(
            item.get(
                "domain"
            )
            or item.get(
                "directory"
            )
        )
        for item
        in custom_in_use
        if (
            item.get(
                "domain"
            )
            or item.get(
                "directory"
            )
        )
    }
)

custom_not_in_use_domains = sorted(
    set(
        custom_domains
    )
    - set(
        custom_in_use_domains
    )
)

strong_domain_evidence = sorted(
    set(
        configured_domains
    )
    | set(
        bare_loaded_components
    )
    | set(
        custom_in_use_domains
    )
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
            "upgrade_impact_inventory",

        "local_evidence_only":
            True,

        "external_release_notes_fetched":
            False,

        "breaking_changes_matched":
            False,

        "compatibility_assessed":
            False,

        "readiness_verdict_produced":
            False,

        "note":
            (
                "This report inventories local "
                "integration evidence for later "
                "upgrade-impact matching. It does "
                "not yet decide whether a pending "
                "Home Assistant upgrade affects "
                "this installation."
            ),
    },

    "pending_updates": {
        "source_report_available":
            bool(
                update_readiness
            ),

        "count":
            len(
                pending_updates
            ),

        "updates":
            pending_updates,
    },

    "home_assistant_config": {
        "root_status":
            config_root_result.get(
                "status"
            ),

        "root":
            config_root_result.get(
                "path"
            ),

        "paths_checked":
            config_root_result.get(
                "checked",
                [],
            ),

        "custom_components_root":
            custom_payload.get(
                "custom_components_root"
            ),

        "custom_components_directory_exists":
            custom_payload.get(
                "directory_exists",
                False,
            ),
    },

    "loaded_components": {
        "component_count":
            len(
                loaded_components
            ),

        "bare_component_count":
            len(
                bare_loaded_components
            ),

        "component_token_candidate_count":
            len(
                component_token_candidates
            ),

        "bare_components":
            bare_loaded_components,

        "component_token_candidates":
            component_token_candidates,

        "components":
            loaded_components,

        "important":
            (
                "Component tokens are matching "
                "aids only. A dotted loaded "
                "component name does not by "
                "itself prove which token is the "
                "integration domain."
            ),
    },

    "config_entries": {
        "entry_count":
            sum(
                item.get(
                    "entry_count",
                    0,
                )
                for item
                in config_domain_details
            ),

        "domain_count":
            len(
                configured_domains
            ),

        "state_counts":
            dict(
                sorted(
                    entry_state_counts.items()
                )
            ),

        "domains":
            configured_domains,

        "domain_details":
            config_domain_details,
    },

    "custom_integrations": {
        "directory_count":
            len(
                custom_integrations
            ),

        "in_use_evidence_count":
            len(
                custom_in_use
            ),

        "no_in_use_evidence_count":
            len(
                custom_not_in_use
            ),

        "hacs_matched_count":
            len(
                custom_hacs_matched
            ),

        "manifest_invalid_count":
            len(
                custom_manifest_invalid
            ),

        "missing_version_count":
            len(
                custom_missing_version
            ),

        "directory_domain_mismatch_count":
            len(
                custom_domain_mismatch
            ),

        "scan_errors":
            custom_payload.get(
                "scan_errors",
                [],
            ),

        "in_use_evidence":
            custom_in_use,

        "no_in_use_evidence":
            custom_not_in_use,

        "hacs_matched":
            custom_hacs_matched,

        "manifest_invalid":
            custom_manifest_invalid,

        "missing_version":
            custom_missing_version,

        "directory_domain_mismatch":
            custom_domain_mismatch,

        "all":
            custom_integrations,
    },

    "hacs_update_evidence": {
        "source_report_available":
            bool(
                update_readiness
            ),

        "update_entity_count":
            len(
                hacs_updates
            ),

        "entities":
            hacs_updates,
    },

    "impact_inventory": {
        "strong_domain_evidence_count":
            len(
                strong_domain_evidence
            ),

        "custom_installed_domain_count":
            len(
                custom_domains
            ),

        "custom_in_use_domain_count":
            len(
                custom_in_use_domains
            ),

        "custom_no_in_use_evidence_domain_count":
            len(
                custom_not_in_use_domains
            ),

        "strong_domain_evidence":
            strong_domain_evidence,

        "custom_installed_domains":
            custom_domains,

        "custom_in_use_domains":
            custom_in_use_domains,

        "custom_no_in_use_evidence_domains":
            custom_not_in_use_domains,

        "component_token_candidates":
            component_token_candidates,

        "important":
            (
                "Strong domain evidence is "
                "suitable for later release-note "
                "matching, but even a domain "
                "match will remain review "
                "evidence rather than proof of "
                "impact until the actual change "
                "is assessed."
            ),
    },

    "collector_status": {
        "loaded_components":
            components_result.get(
                "status"
            ),

        "config_entries":
            config_entries_result.get(
                "status"
            ),

        "home_assistant_config_root":
            config_root_result.get(
                "status"
            ),

        "custom_integration_manifests":
            custom_scan_result.get(
                "status"
            ),

        "update_readiness_report":
            (
                "ok"
                if update_readiness
                else "unavailable"
            ),
    },
}


if (
    components_result.get(
        "status"
    )
    != "ok"
):
    report[
        "collector_status"
    ][
        "loaded_components_error"
    ] = components_result.get(
        "error"
    )


if (
    config_entries_result.get(
        "status"
    )
    != "ok"
):
    report[
        "collector_status"
    ][
        "config_entries_error"
    ] = config_entries_result.get(
        "error"
    )


if (
    custom_scan_result.get(
        "status"
    )
    != "ok"
):
    report[
        "collector_status"
    ][
        "custom_integration_manifests_error"
    ] = custom_scan_result.get(
        "error"
    )


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
    "Upgrade impact inventory"
)

print(
    "------------------------------------------"
)

print(
    f"Pending updates:             "
    f"{len(pending_updates)}"
)

print(
    f"Loaded components:           "
    f"{len(loaded_components)}"
)

print(
    f"Configured domains:          "
    f"{len(configured_domains)}"
)

print(
    f"Custom integrations:         "
    f"{len(custom_integrations)}"
)

print(
    f"Custom integrations in use:  "
    f"{len(custom_in_use)}"
)

print(
    f"HACS matches:                "
    f"{len(custom_hacs_matched)}"
)

print(
    f"Invalid manifests:           "
    f"{len(custom_manifest_invalid)}"
)

print(
    f"Missing manifest versions:   "
    f"{len(custom_missing_version)}"
)

print(
    "Domain/directory mismatches: "
    f"{len(custom_domain_mismatch)}"
)

print("")

print(
    "This stage is local inventory only."
)

print(
    "No release-note compatibility "
    "verdict is produced."
)

print("")

print(
    f"Detailed report: "
    f"{OUTPUT_FILE}"
)
