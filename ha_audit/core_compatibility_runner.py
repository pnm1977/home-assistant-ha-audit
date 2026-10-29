"""Run selected, reusable Core compatibility checks against active YAML.

This module is release-independent: version policy belongs to
core_compatibility_rules.py, and YAML pattern logic to
core_compatibility_checks.py.

It produces *local check evidence only*. It never certifies update safety,
replaces dynamic correlation, or changes the existing readiness decision.
"""

import importlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from core_compatibility_rules import select_compatibility_rules


QUALITY_FILE = Path('/config/quality_audit.json')
IMPACT_FILE = Path('/config/upgrade_impact_audit.json')
OUTPUT_FILE = Path('/config/core_compatibility_checks_audit.json')
DEFAULT_CONFIG_ROOT = Path('/homeassistant')
MAX_ACTIVE_FILES = 2000
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_RULES = 100
_NAME = re.compile(r'[a-z][a-z0-9_]*\Z')


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _load_json(path):
    with Path(path).open('r', encoding='utf-8') as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError(f'{Path(path).name} must contain an object')
    return data


def _active_sources(quality):
    tree = _mapping(_mapping(quality).get('configuration_tree'))
    paths = tree.get('active_yaml')
    if not isinstance(paths, list) or not paths:
        raise ValueError('Active YAML inventory is absent or empty')
    if len(paths) > MAX_ACTIVE_FILES:
        raise ValueError('Active YAML inventory exceeds inspection limit')
    if any(not isinstance(p, str) or not p.strip() for p in paths):
        raise ValueError('Active YAML inventory contains invalid paths')
    return sorted(set(paths))


def _read_active_yaml(root, entry):
    """Read a bounded source, never following paths outside the HA config root."""
    root = Path(root).resolve(strict=True)
    path = Path(entry)
    if path.is_absolute():
        # HA's config is also exposed as /config on some installations.
        if path.parts[:2] == ('/', 'config'):
            path = Path(*path.parts[2:])
        else:
            raise ValueError('Absolute active YAML path is outside scan scope')
    if '..' in path.parts:
        raise ValueError('Parent directory reference in active YAML path')
    resolved = (root / path).resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError('Active YAML path escapes configuration directory') from exc
    if not resolved.is_file():
        raise ValueError('Active YAML entry is not a regular file')
    if resolved.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('Active YAML file exceeds inspection size limit')
    with resolved.open('rb') as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError('Active YAML file exceeds inspection size limit')
    return raw.decode('utf-8-sig')


def _resolve_check(rule):
    """Resolve only named local compatibility modules and public functions."""
    module = rule.get('module')
    function = rule.get('function')
    kind = rule.get('input_kind')
    if (kind != 'active_yaml' or not isinstance(module, str)
            or not module.startswith('core_compatibility_')
            or not _NAME.fullmatch(module)
            or not isinstance(function, str) or not _NAME.fullmatch(function)):
        raise ValueError('Unsupported or invalid compatibility rule descriptor')
    implementation = getattr(importlib.import_module(module), function)
    if not callable(implementation):
        raise ValueError('Selected compatibility check is not callable')
    return implementation


def inspect_upgrade(installed_version, target_version, active_yaml, config_root,
                    *, registry=None):
    """Return bounded, explicit inspection evidence for one Core upgrade.

    ``registry=None`` uses the default registered rules. A missing rule is
    not an error and is never interpreted as absence of compatibility risk.
    """
    result = {
        'schema_version': 1,
        'audit_version': os.environ.get('HA_AUDIT_VERSION', 'unknown'),
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'scope': {
            'phase': 'generic_local_core_compatibility_checks',
            'external_fetch_performed': False,
            'readiness_verdict_produced': False,
            'note': ('This is local evidence from selected checks only. '
                     'Missing checks or no findings do not establish update safety.'),
        },
        'installed_version': installed_version,
        'target_version': target_version,
        'status': 'incomplete',
        'crossed_release_families': [],
        'families_without_registered_rules': [],
        'selected_rule_count': 0,
        'rules': [],
        'findings': [],
        'read_failures': [],
        'summary': {
            'review_required_count': 0,
            'incomplete_rule_count': 0,
            'checked_yaml_file_count': 0,
        },
    }
    try:
        selection = (select_compatibility_rules(installed_version, target_version)
                     if registry is None else select_compatibility_rules(
                         installed_version, target_version, registry=registry))
    except Exception as exc:
        result['read_failures'].append({'reason': f'Rule selection failed: {exc}'})
        return result

    result['crossed_release_families'] = selection['crossed_release_families']
    result['families_without_registered_rules'] = selection['families_without_registered_rules']
    if selection['status'] != 'selected':
        result['status'] = selection['status']
        return result

    rules = selection['selected_rules']
    result['selected_rule_count'] = len(rules)
    if len(rules) > MAX_RULES:
        result['read_failures'].append({'reason': 'Too many selected rules'})
        return result
    if not rules:
        result['status'] = 'no_registered_checks'
        return result

    try:
        sources = _active_sources(active_yaml)
        root = Path(config_root).resolve(strict=True)
        if not root.is_dir():
            raise ValueError('Configuration root is not a directory')
    except (OSError, ValueError, RuntimeError) as exc:
        result['read_failures'].append({'reason': f'Active YAML scope unavailable: {exc}'})
        result['summary']['incomplete_rule_count'] = len(rules)
        return result

    for rule in rules:
        item = {
            'rule_id': rule['rule_id'],
            'introduced_in': rule['introduced_in'],
            'official_group': rule['official_group'],
            'policy_applied_from': rule.get('policy_applied_from'),
            'status': 'incomplete',
            'files_checked': 0,
            'findings': [],
            'read_failures': [],
        }
        try:
            check = _resolve_check(rule)
            parameters = rule['check_parameters']
            if not isinstance(parameters, dict):
                raise ValueError('Invalid check_parameters')
            for source in sources:
                try:
                    content = _read_active_yaml(root, source)
                    findings = check(
                        content, source=source, rule_id=rule['rule_id'],
                        **parameters)
                    if not isinstance(findings, list):
                        raise ValueError('Check returned invalid findings')
                    item['findings'].extend(findings)
                    item['files_checked'] += 1
                except Exception as exc:
                    # Includes YAML parser errors. A failed file is never
                    # silently counted as inspected or clear.
                    item['read_failures'].append({
                        'file': source, 'reason': f'{type(exc).__name__}: {exc}'
                    })
        except Exception as exc:
            item['read_failures'].append({
                'reason': f'Check unavailable: {type(exc).__name__}: {exc}'
            })
        if not item['read_failures']:
            item['status'] = ('review_required' if item['findings']
                              else 'no_affected_usage_found')
        result['rules'].append(item)
        result['findings'].extend(item['findings'])
        result['read_failures'].extend(item['read_failures'])

    result['summary'] = {
        'review_required_count': sum(r['status'] == 'review_required'
                                     for r in result['rules']),
        'incomplete_rule_count': sum(r['status'] == 'incomplete'
                                     for r in result['rules']),
        'checked_yaml_file_count': sum(r['files_checked'] for r in result['rules']),
    }
    result['status'] = ('incomplete' if result['summary']['incomplete_rule_count']
                        else 'local_checks_completed')
    return result


def scan_from_reports(quality, impact):
    """Use the same local inventory and pending-upgrade evidence as HA Audit."""
    if not isinstance(_mapping(impact).get('pending_updates'), dict):
        return {
            'schema_version': 1,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'incomplete',
            'read_failures': [{'reason': 'Pending-update evidence is missing'}],
            'scope': {'readiness_verdict_produced': False},
        }
    pending = _mapping(impact['pending_updates'])
    upgrades = pending.get('updates', [])
    if not isinstance(upgrades, list):
        upgrades = []
    core = next((item for item in upgrades
                 if isinstance(item, dict) and item.get('category') == 'core'), None)
    if core is None:
        return {
            'schema_version': 1,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'no_core_update_pending',
            'selected_rule_count': 0,
            'rules': [],
            'findings': [],
            'scope': {'readiness_verdict_produced': False},
        }
    root = _mapping(_mapping(impact).get('home_assistant_config')).get('root')
    return inspect_upgrade(
        core.get('installed_version'), core.get('latest_version'),
        quality, root or DEFAULT_CONFIG_ROOT)


def write_report(report, path=OUTPUT_FILE):
    """Atomic report replacement so readers never see partial JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    name = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8',
                                         dir=path.parent, prefix='.core_compat_',
                                         delete=False) as stream:
            name = stream.name
            json.dump(report, stream, indent=2)
            stream.write('\n')
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def main():
    try:
        quality = _load_json(QUALITY_FILE)
        impact = _load_json(IMPACT_FILE)
        report = scan_from_reports(quality, impact)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            'schema_version': 1,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'incomplete',
            'read_failures': [{'reason': f'Required evidence unavailable: {exc}'}],
            'scope': {'readiness_verdict_produced': False},
        }
    write_report(report)
    print('Generic local Core checks:', report['status'])
    print('Detailed report:', OUTPUT_FILE)


if __name__ == '__main__':
    main()
