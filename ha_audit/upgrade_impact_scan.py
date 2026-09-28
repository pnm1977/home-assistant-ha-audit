import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

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


def normalise_version(value):
    if value is None:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    if text[:1].lower() == "v":
        text = text[1:]

    return text.lower()


def versions_agree(
    left,
    right,
):
    left_normalised = normalise_version(
        left
    )

    right_normalised = normalise_version(
        right
    )

    if (
        left_normalised is None
        or right_normalised is None
    ):
        return None

    return (
        left_normalised
        == right_normalised
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


def component_root(
    component,
):
    tokens = component_tokens(
        component
    )

    if not tokens:
        return None

    return tokens[0]


def component_platform(
    component,
):
    tokens = component_tokens(
        component
    )

    if len(
        tokens
    ) < 2:
        return None

    return tokens[1]


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

    return False


def normalise_repository_url(
    value,
):
    if not value:
        return None

    text = str(
        value
    ).strip()

    if not text:
        return None

    if "://" not in text:
        text = (
            "https://"
            + text
        )

    try:
        parsed = urlparse(
            text
        )

    except Exception:
        return None

    host = (
        parsed.netloc
        or ""
    ).lower()

    if host.startswith(
        "www."
    ):
        host = host[4:]

    if host != "github.com":
        return None

    path_parts = [
        part
        for part
        in parsed.path.split("/")
        if part
    ]

    if len(
        path_parts
    ) < 2:
        return None

    owner = path_parts[0].lower()

    repository = (
        path_parts[1]
        .removesuffix(
            ".git"
        )
        .lower()
    )

    return (
        f"github.com/"
        f"{owner}/"
        f"{repository}"
    )


def repository_candidates_from_manifest(
    integration,
):
    candidates = set()

    for key in (
        "documentation",
        "issue_tracker",
    ):
        repository = normalise_repository_url(
            integration.get(
                key
            )
        )

        if repository:
            candidates.add(
                repository
            )

    return sorted(
        candidates
    )


def repository_from_release_url(
    release_url,
):
    return normalise_repository_url(
        release_url
    )


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

loaded_component_roots = sorted(
    {
        root
        for component
        in loaded_components
        for root
        in [
            component_root(
                component
            )
        ]
        if root
    }
)

platform_integrations = defaultdict(
    set
)

for component in loaded_components:
    root = component_root(
        component
    )

    platform = component_platform(
        component
    )

    if (
        root
        and platform
    ):
        platform_integrations[
            platform
        ].add(
            root
        )

platform_usage = []

for platform in sorted(
    platform_integrations
):
    platform_usage.append(
        {
            "platform":
                platform,

            "integration_count":
                len(
                    platform_integrations[
                        platform
                    ]
                ),

            "integrations":
                sorted(
                    platform_integrations[
                        platform
                    ]
                ),
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

    loaded_entry_count = sum(
        1
        for entry
        in entries
        if (
            not entry.get(
                "disabled"
            )
            and entry.get(
                "state"
            )
            == "loaded"
        )
    )

    enabled_count = sum(
        1
        for entry
        in entries
        if not entry.get(
            "disabled"
        )
    )

    disabled_count = sum(
        1
        for entry
        in entries
        if entry.get(
            "disabled"
        )
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
                enabled_count,

            "disabled_count":
                disabled_count,

            "loaded_enabled_count":
                loaded_entry_count,

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

configured_loaded_domains = sorted(
    [
        item.get(
            "domain"
        )
        for item
        in config_domain_details
        if item.get(
            "loaded_enabled_count",
            0,
        )
        > 0
    ]
)

configured_not_loaded_domains = sorted(
    [
        item.get(
            "domain"
        )
        for item
        in config_domain_details
        if (
            item.get(
                "enabled_count",
                0,
            )
            > 0
            and item.get(
                "loaded_enabled_count",
                0,
            )
            == 0
        )
    ]
)

configured_disabled_domains = sorted(
    [
        item.get(
            "domain"
        )
        for item
        in config_domain_details
        if (
            item.get(
                "entry_count",
                0,
            )
            > 0
            and item.get(
                "enabled_count",
                0,
            )
            == 0
        )
    ]
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

            "repository":
                repository_from_release_url(
                    item.get(
                        "release_url"
                    )
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

    enabled_entries = [
        entry
        for entry
        in entries
        if not entry.get(
            "disabled"
        )
    ]

    disabled_entries = [
        entry
        for entry
        in entries
        if entry.get(
            "disabled"
        )
    ]

    loaded_enabled_entries = [
        entry
        for entry
        in enabled_entries
        if entry.get(
            "state"
        )
        == "loaded"
    ]

    integration[
        "config_entry_count"
    ] = len(
        entries
    )

    integration[
        "enabled_config_entry_count"
    ] = len(
        enabled_entries
    )

    integration[
        "disabled_config_entry_count"
    ] = len(
        disabled_entries
    )

    integration[
        "loaded_enabled_config_entry_count"
    ] = len(
        loaded_enabled_entries
    )

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

    if (
        integration.get(
            "loaded"
        )
        or loaded_enabled_entries
    ):
        activity = "active"

    elif (
        entries
        and not enabled_entries
    ):
        activity = "disabled"

    elif enabled_entries:
        activity = (
            "configured_not_active"
        )

    else:
        activity = "installed_only"

    integration[
        "activity"
    ] = activity

    integration[
        "active_evidence"
    ] = (
        activity
        == "active"
    )

    manifest_repositories = (
        repository_candidates_from_manifest(
            integration
        )
    )

    integration[
        "manifest_repository_candidates"
    ] = manifest_repositories

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

        update_repository = (
            update.get(
                "repository"
            )
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
            update_repository
            and update_repository
            in manifest_repositories
        ):
            match_type = (
                "repository_url"
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
            agreement = versions_agree(
                integration.get(
                    "version"
                ),
                update.get(
                    "installed_version"
                ),
            )

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

                    "repository":
                        update_repository,

                    "manifest_version":
                        integration.get(
                            "version"
                        ),

                    "hacs_installed_version":
                        update.get(
                            "installed_version"
                        ),

                    "hacs_latest_version":
                        update.get(
                            "latest_version"
                        ),

                    "version_agreement":
                        agreement,

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

    if not matches:
        integration[
            "hacs_version_agreement"
        ] = None

        integration[
            "hacs_version_agreement_reason"
        ] = "no_hacs_match"

    elif len(
        matches
    ) > 1:
        integration[
            "hacs_version_agreement"
        ] = None

        integration[
            "hacs_version_agreement_reason"
        ] = "multiple_hacs_matches"

    else:
        agreement = matches[0].get(
            "version_agreement"
        )

        integration[
            "hacs_version_agreement"
        ] = agreement

        if agreement is True:
            reason = "match"

        elif agreement is False:
            reason = "mismatch"

        else:
            reason = "version_unavailable"

        integration[
            "hacs_version_agreement_reason"
        ] = reason

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

custom_active = [
    item
    for item
    in custom_integrations
    if item.get(
        "activity"
    )
    == "active"
]

custom_configured_not_active = [
    item
    for item
    in custom_integrations
    if item.get(
        "activity"
    )
    == "configured_not_active"
]

custom_disabled = [
    item
    for item
    in custom_integrations
    if item.get(
        "activity"
    )
    == "disabled"
]

custom_installed_only = [
    item
    for item
    in custom_integrations
    if item.get(
        "activity"
    )
    == "installed_only"
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

custom_version_mismatches = [
    item
    for item
    in custom_integrations
    if item.get(
        "hacs_version_agreement"
    )
    is False
]

custom_active_version_mismatches = [
    item
    for item
    in custom_version_mismatches
    if item.get(
        "activity"
    )
    == "active"
]

custom_inactive_version_mismatches = [
    item
    for item
    in custom_version_mismatches
    if item.get(
        "activity"
    )
    != "active"
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

custom_active_domains = sorted(
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
        in custom_active
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

custom_configured_not_active_domains = sorted(
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
        in custom_configured_not_active
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

custom_disabled_domains = sorted(
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
        in custom_disabled
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

custom_installed_only_domains = sorted(
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
        in custom_installed_only
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


# ------------------------------------------------------------
# HACS evidence not matched to custom integrations
# ------------------------------------------------------------

matched_hacs_entity_ids = {
    match.get(
        "entity_id"
    )
    for integration
    in custom_integrations
    for match
    in integration.get(
        "hacs_update_matches",
        [],
    )
    if match.get(
        "entity_id"
    )
}

unmatched_hacs_updates = [
    item
    for item
    in hacs_updates
    if item.get(
        "entity_id"
    )
    not in matched_hacs_entity_ids
]


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
                "integration and platform evidence "
                "for later upgrade-impact matching. "
                "It does not yet decide whether a "
                "pending Home Assistant upgrade "
                "affects this installation."
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

        "component_root_count":
            len(
                loaded_component_roots
            ),

        "bare_components":
            bare_loaded_components,

        "component_roots":
            loaded_component_roots,

        "components":
            loaded_components,

        "important":
            (
                "Loaded component roots are useful "
                "matching evidence, but they include "
                "both integration domains and generic "
                "Home Assistant components. They are "
                "not treated as equivalent to configured "
                "integration domains."
            ),
    },

    "platform_usage": {
        "platform_count":
            len(
                platform_usage
            ),

        "platforms":
            platform_usage,

        "important":
            (
                "Platform usage is derived from dotted "
                "loaded component names such as "
                "robovac.vacuum. This allows later "
                "release-note matching to distinguish "
                "platform changes from integration-domain "
                "changes."
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

        "loaded_domain_count":
            len(
                configured_loaded_domains
            ),

        "configured_not_loaded_domain_count":
            len(
                configured_not_loaded_domains
            ),

        "disabled_domain_count":
            len(
                configured_disabled_domains
            ),

        "state_counts":
            dict(
                sorted(
                    entry_state_counts.items()
                )
            ),

        "domains":
            configured_domains,

        "loaded_domains":
            configured_loaded_domains,

        "configured_not_loaded_domains":
            configured_not_loaded_domains,

        "disabled_domains":
            configured_disabled_domains,

        "domain_details":
            config_domain_details,
    },

    "custom_integrations": {
        "directory_count":
            len(
                custom_integrations
            ),

        "active_count":
            len(
                custom_active
            ),

        "configured_not_active_count":
            len(
                custom_configured_not_active
            ),

        "disabled_count":
            len(
                custom_disabled
            ),

        "installed_only_count":
            len(
                custom_installed_only
            ),

        "hacs_matched_count":
            len(
                custom_hacs_matched
            ),

        "hacs_version_mismatch_count":
            len(
                custom_version_mismatches
            ),

        "active_hacs_version_mismatch_count":
            len(
                custom_active_version_mismatches
            ),

        "inactive_hacs_version_mismatch_count":
            len(
                custom_inactive_version_mismatches
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

        "active":
            custom_active,

        "configured_not_active":
            custom_configured_not_active,

        "disabled":
            custom_disabled,

        "installed_only":
            custom_installed_only,

        "hacs_matched":
            custom_hacs_matched,

        "hacs_version_mismatches":
            custom_version_mismatches,

        "active_hacs_version_mismatches":
            custom_active_version_mismatches,

        "inactive_hacs_version_mismatches":
            custom_inactive_version_mismatches,

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

        "matched_to_custom_integration_count":
            len(
                matched_hacs_entity_ids
            ),

        "unmatched_count":
            len(
                unmatched_hacs_updates
            ),

        "unmatched_entities":
            unmatched_hacs_updates,

        "entities":
            hacs_updates,
    },

    "impact_inventory": {
        "configured_integration_domain_count":
            len(
                configured_domains
            ),

        "configured_loaded_domain_count":
            len(
                configured_loaded_domains
            ),

        "custom_installed_domain_count":
            len(
                custom_domains
            ),

        "custom_active_domain_count":
            len(
                custom_active_domains
            ),

        "custom_configured_not_active_domain_count":
            len(
                custom_configured_not_active_domains
            ),

        "custom_disabled_domain_count":
            len(
                custom_disabled_domains
            ),

        "custom_installed_only_domain_count":
            len(
                custom_installed_only_domains
            ),

        "loaded_component_root_count":
            len(
                loaded_component_roots
            ),

        "platform_count":
            len(
                platform_usage
            ),

        "configured_integration_domains":
            configured_domains,

        "configured_loaded_domains":
            configured_loaded_domains,

        "custom_installed_domains":
            custom_domains,

        "custom_active_domains":
            custom_active_domains,

        "custom_configured_not_active_domains":
            custom_configured_not_active_domains,

        "custom_disabled_domains":
            custom_disabled_domains,

        "custom_installed_only_domains":
            custom_installed_only_domains,

        "loaded_component_roots":
            loaded_component_roots,

        "platform_usage":
            platform_usage,

        "important":
            (
                "Configured integration domains, custom "
                "integration activity, loaded component "
                "roots, and platform usage are deliberately "
                "kept as separate evidence classes. A later "
                "release-note match remains review evidence "
                "rather than proof of impact until the "
                "specific change is assessed."
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
    f"Configured + loaded domains: "
    f"{len(configured_loaded_domains)}"
)

print(
    f"Custom integrations:         "
    f"{len(custom_integrations)}"
)

print(
    f"Custom active:               "
    f"{len(custom_active)}"
)

print(
    f"Custom configured inactive:  "
    f"{len(custom_configured_not_active)}"
)

print(
    f"Custom disabled:             "
    f"{len(custom_disabled)}"
)

print(
    f"Custom installed only:       "
    f"{len(custom_installed_only)}"
)

print(
    f"HACS matches:                "
    f"{len(custom_hacs_matched)}"
)

print(
    f"HACS version mismatches:     "
    f"{len(custom_version_mismatches)}"
)

print(
    f"Active version mismatches:   "
    f"{len(custom_active_version_mismatches)}"
)

print(
    f"Inactive version mismatches: "
    f"{len(custom_inactive_version_mismatches)}"
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
