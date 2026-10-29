"""Select locally implemented Core compatibility checks for an upgrade window.

This is a release-independent *selection* layer, not a compatibility verdict.
It never executes a check, treats missing rules as safe, or changes the
existing deterministic or dynamic correlation reports.

Adding an occasional targeted check requires a registry descriptor, not a
new release-specific runner. The existing 2026.9 rule pack remains separate
until it is explicitly adapted to this interface.
"""

import re


# Registered checks must have a specific, reviewable implementation.
# A release with no registered checks is supported and is NOT declared safe.
RULE_REGISTRY = (
    {
        "rule_id": "core_2026_10_state_conditions_for",
        "introduced_in": "2026.10",
        "official_group": "State conditions",
        "module": "core_2026_10_state_conditions",
        "function": "find_unsupported_state_durations",
        "input_kind": "active_yaml",
    },
)

_STABLE_CORE_VERSION = re.compile(r"(20\d{2})\.(\d{1,2})(?:\.(\d+))?\Z")
_RELEASE_FAMILY = re.compile(r"(20\d{2})\.(\d{1,2})\Z")


def parse_stable_core_version(value):
    """Return (year, month, patch), or None for unknown/prerelease values.

    Deliberately fail closed for beta/RC, decorated or malformed versions;
    treating them as stable could silently omit applicable upgrade checks.
    """
    if not isinstance(value, str):
        return None
    match = _STABLE_CORE_VERSION.fullmatch(value.strip())
    if not match:
        return None
    year, month, patch = (int(item) if item else 0 for item in match.groups())
    if not 1 <= month <= 12:
        return None
    return (year, month, patch)


def _parse_family(value):
    if not isinstance(value, str):
        return None
    match = _RELEASE_FAMILY.fullmatch(value)
    if not match:
        return None
    year, month = map(int, match.groups())
    if not 1 <= month <= 12:
        return None
    return (year, month, 0)


def _family_name(version):
    return f"{version[0]}.{version[1]}"


def _crossed_release_families(installed, target):
    """Release families introduced after the installed release, up to target.

    Patch-only upgrades do not cross a new release family.
    """
    start = installed[0] * 12 + installed[1] - 1
    end = target[0] * 12 + target[1] - 1
    return [
        f"{index // 12}.{index % 12 + 1}"
        for index in range(start + 1, end + 1)
    ]


def _validated_registry(registry):
    """Reject ambiguous/malformed local descriptors rather than skipping."""
    checked = []
    seen = set()
    for record in registry:
        if not isinstance(record, dict):
            raise ValueError("Compatibility registry records must be mappings")
        rule_id = record.get("rule_id")
        introduced = _parse_family(record.get("introduced_in"))
        if not isinstance(rule_id, str) or not re.fullmatch(r"[a-z0-9_]+", rule_id):
            raise ValueError("Invalid compatibility rule identifier")
        if rule_id in seen:
            raise ValueError(f"Duplicate compatibility rule: {rule_id}")
        if introduced is None:
            raise ValueError(f"Invalid introduced_in for {rule_id}")
        for key in ("official_group", "module", "function", "input_kind"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"Missing {key} for {rule_id}")
        seen.add(rule_id)
        checked.append((introduced, dict(record)))
    return checked


def select_compatibility_rules(installed_version, target_version, *, registry=RULE_REGISTRY):
    """Select registered checks introduced in (installed, target].

    Output status is only about window *selection*, never update readiness:
      selected: valid forward upgrade window (possibly zero available checks)
      no_update: target == installed
      unsupported_downgrade: target precedes installed
      incomplete: version(s) cannot be reliably parsed

    ``families_without_registered_rules`` describes registry coverage only.
    It does not classify official breaking changes or dynamic correlation.
    """
    validated = _validated_registry(registry)
    installed = parse_stable_core_version(installed_version)
    target = parse_stable_core_version(target_version)
    result = {
        "status": "incomplete",
        "installed_version": installed_version,
        "target_version": target_version,
        "selected_rules": [],
        "crossed_release_families": [],
        "families_without_registered_rules": [],
        "readiness_verdict_produced": False,
        "note": (
            "This is rule selection only. Missing rules do not mean a release "
            "or installation is compatible; official evidence and dynamic "
            "correlation must be assessed separately."
        ),
    }
    if installed is None or target is None:
        result["reason"] = "core_version_unavailable_or_unparseable"
        return result
    if target < installed:
        result["status"] = "unsupported_downgrade"
        return result
    if target == installed:
        result["status"] = "no_update"
        return result

    crossed = _crossed_release_families(installed, target)
    selected = [
        record for introduced, record in validated
        if installed < introduced <= target
    ]
    selected.sort(key=lambda record: (record["introduced_in"], record["rule_id"]))
    registered_families = {
        _family_name(introduced)
        for introduced, _ in validated
    }
    result.update({
        "status": "selected",
        "selected_rules": selected,
        "crossed_release_families": crossed,
        "families_without_registered_rules": [
            family for family in crossed if family not in registered_families
        ],
    })
    return result
