"""Regression tests for the version-independent Core compatibility runner.

Run with: python -m unittest -v test_core_compatibility_runner

These tests exercise the report boundary, rule selection, file-scope safety,
partial failures, and future release behaviour. They do not assert upgrade
safety or replace integration tests against a live Home Assistant instance.
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from core_compatibility_rules import RULE_REGISTRY
from core_compatibility_runner import (
    inspect_upgrade,
    scan_from_reports,
    write_report,
)


BAD_ATTRIBUTE_CONDITION = (
    '- condition: state\n'
    '  entity_id: binary_sensor.door\n'
    '  state: "on"\n'
    '  attribute: something\n'
    '  for: "00:00:10"\n'
)
VALID_DURATION_CONDITION = (
    '- condition: state\n'
    '  entity_id: binary_sensor.door\n'
    '  state: "on"\n'
    '  for: "00:00:10"\n'
)
LIST_DURATION_CONDITION = (
    '- condition: state\n'
    '  entity_id: binary_sensor.door\n'
    '  state: ["on", "off"]\n'
    '  for: "00:00:10"\n'
)


class CoreCompatibilityRunnerTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name) / 'homeassistant'
        self.root.mkdir()
        self.source = self.root / 'automations.yaml'
        self.source.write_text(BAD_ATTRIBUTE_CONDITION, encoding='utf-8')
        self.quality = {
            'configuration_tree': {'active_yaml': ['automations.yaml']}
        }

    def run_upgrade(self, installed='2026.8.3', target='2026.10.4',
                    quality=None, registry=None):
        arguments = {}
        if registry is not None:
            arguments['registry'] = registry
        return inspect_upgrade(
            installed, target, self.quality if quality is None else quality,
            self.root, **arguments)

    def test_detects_applicable_rule_with_exact_source_and_line(self):
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'local_checks_completed')
        self.assertEqual(result['selected_rule_count'], 1)
        self.assertEqual(result['summary']['review_required_count'], 1)
        self.assertEqual(result['summary']['incomplete_rule_count'], 0)
        self.assertEqual(result['findings'][0]['file'], 'automations.yaml')
        self.assertEqual(result['findings'][0]['line'], 1)
        self.assertEqual(result['findings'][0]['reasons'], ['attribute_with_for'])

    def test_valid_condition_is_not_affected_but_never_declared_safe(self):
        self.source.write_text(VALID_DURATION_CONDITION, encoding='utf-8')
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'local_checks_completed')
        self.assertEqual(result['rules'][0]['status'], 'no_affected_usage_found')
        self.assertFalse(result['findings'])
        self.assertIs(result['scope']['readiness_verdict_produced'], False)

    def test_pre_patch_list_with_duration_is_reported(self):
        self.source.write_text(LIST_DURATION_CONDITION, encoding='utf-8')
        result = self.run_upgrade(target='2026.10.1')
        self.assertEqual(result['summary']['review_required_count'], 1)
        self.assertEqual(result['findings'][0]['reasons'], ['state_list_with_for'])

    def test_patch_corrected_list_with_duration_is_not_reported(self):
        self.source.write_text(LIST_DURATION_CONDITION, encoding='utf-8')
        result = self.run_upgrade(target='2026.10.4')
        self.assertEqual(result['rules'][0]['status'], 'no_affected_usage_found')
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['rules'][0]['policy_applied_from'], '2026.10.2')

    def test_future_year_does_not_discard_applicable_earlier_rules(self):
        result = self.run_upgrade(target='2027.1.1')
        self.assertEqual(result['selected_rule_count'], 1)
        self.assertIn('2027.1', result['families_without_registered_rules'])
        self.assertEqual(result['summary']['review_required_count'], 1)
        self.assertFalse(result['scope']['readiness_verdict_produced'])

    def test_future_unregistered_releases_are_not_assumed_clean(self):
        result = self.run_upgrade(installed='2026.10.4', target='2027.2.1')
        self.assertEqual(result['status'], 'no_registered_checks')
        self.assertEqual(result['rules'], [])
        self.assertEqual(result['families_without_registered_rules'], [
            '2026.11', '2026.12', '2027.1', '2027.2'])
        self.assertFalse(result['scope']['readiness_verdict_produced'])

    def test_patch_only_update_does_not_repeat_older_rule(self):
        result = self.run_upgrade(installed='2026.10.2', target='2026.10.4')
        self.assertEqual(result['status'], 'no_registered_checks')
        self.assertEqual(result['selected_rule_count'], 0)

    def test_bad_version_fails_closed(self):
        result = self.run_upgrade(installed='2026.8.3', target='unknown')
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['selected_rule_count'], 0)
        self.assertFalse(result['scope']['readiness_verdict_produced'])

    def test_absent_active_yaml_inventory_is_incomplete(self):
        result = self.run_upgrade(quality={})
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['summary']['incomplete_rule_count'], 1)
        self.assertTrue(result['read_failures'])

    def test_invalid_inventory_entries_are_incomplete(self):
        for values in ([], [None], [''], ['automations.yaml', 5]):
            with self.subTest(paths=values):
                result = self.run_upgrade(quality={
                    'configuration_tree': {'active_yaml': values},
                })
                self.assertEqual(result['status'], 'incomplete')

    def test_missing_yaml_file_is_not_counted_as_checked(self):
        self.quality['configuration_tree']['active_yaml'] = ['missing.yaml']
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['rules'][0]['files_checked'], 0)
        self.assertEqual(result['summary']['incomplete_rule_count'], 1)

    def test_invalid_yaml_is_not_reported_as_clear(self):
        self.source.write_text('conditions: [\n', encoding='utf-8')
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['rules'][0]['files_checked'], 0)
        self.assertTrue(result['read_failures'])

    def test_partial_file_failure_never_reports_completed_assessment(self):
        second = self.root / 'missing.yaml'
        self.quality['configuration_tree']['active_yaml'] = [
            'automations.yaml', second.name]
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['summary']['review_required_count'], 0)
        self.assertEqual(result['summary']['incomplete_rule_count'], 1)
        self.assertEqual(result['rules'][0]['files_checked'], 1)
        self.assertEqual(len(result['findings']), 1)

    def test_relative_path_escape_is_rejected(self):
        self.quality['configuration_tree']['active_yaml'] = ['../secret.yaml']
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['rules'][0]['files_checked'], 0)

    def test_absolute_path_outside_config_is_rejected(self):
        self.quality['configuration_tree']['active_yaml'] = ['/etc/passwd']
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['rules'][0]['files_checked'], 0)

    def test_symlink_outside_config_is_rejected(self):
        external = self.root.parent / 'outside.yaml'
        external.write_text(BAD_ATTRIBUTE_CONDITION, encoding='utf-8')
        (self.root / 'alias.yaml').symlink_to(external)
        self.quality['configuration_tree']['active_yaml'] = ['alias.yaml']
        result = self.run_upgrade()
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['rules'][0]['files_checked'], 0)

    def test_unavailable_check_implementation_is_incomplete(self):
        rule = copy.deepcopy(RULE_REGISTRY[0])
        rule['function'] = 'nonexistent_check'
        result = self.run_upgrade(registry=[rule])
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['summary']['incomplete_rule_count'], 1)
        self.assertIn('Check unavailable:', result['rules'][0]['read_failures'][0]['reason'])

    def test_unknown_module_is_not_executed(self):
        rule = copy.deepcopy(RULE_REGISTRY[0])
        rule['module'] = 'os'
        result = self.run_upgrade(registry=[rule])
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['summary']['incomplete_rule_count'], 1)

    def test_existing_upgrade_report_structure_is_consumed(self):
        impact = {
            'pending_updates': {'updates': [{
                'category': 'core',
                'installed_version': '2026.8.3',
                'latest_version': '2026.10.4',
            }]},
            'home_assistant_config': {'root': str(self.root)},
        }
        result = scan_from_reports(self.quality, impact)
        self.assertEqual(result['status'], 'local_checks_completed')
        self.assertEqual(result['summary']['review_required_count'], 1)

    def test_missing_pending_update_evidence_is_incomplete(self):
        result = scan_from_reports(self.quality, {})
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(result['read_failures'])

    def test_no_core_update_is_distinct_from_missing_evidence(self):
        result = scan_from_reports(
            self.quality, {'pending_updates': {'updates': []}})
        self.assertEqual(result['status'], 'no_core_update_pending')
        self.assertFalse(result['scope']['readiness_verdict_produced'])

    def test_report_is_written_as_valid_json_and_replaces_old_report(self):
        destination = self.root.parent / 'core_compatibility_checks_audit.json'
        destination.write_text('{"old": true}', encoding='utf-8')
        report = self.run_upgrade()
        write_report(report, path=destination)
        written = json.loads(destination.read_text(encoding='utf-8'))
        self.assertEqual(written['status'], 'local_checks_completed')
        self.assertNotIn('old', written)
        self.assertEqual(written['findings'][0]['file'], 'automations.yaml')


if __name__ == '__main__':
    unittest.main()
