"""Regression tests for the release-independent compatibility rule framework.

Run from ha_audit/ with:
    python3 -m unittest -v test_core_compatibility_framework

These tests do not replace the established 2026.9 compatibility rules and
must not be interpreted as an update-readiness or safety verdict.
"""

import copy
import unittest

import yaml

from core_compatibility_checks import find_state_condition_conflicts
from core_compatibility_rules import (
    RULE_REGISTRY,
    parse_stable_core_version,
    select_compatibility_rules,
)


STATE_YAML = """actions:
  - if:
      - condition: state
        entity_id: climate.study
        attribute: hvac_action
        state: heating
        for: '00:00:10'
    then:
      - condition: state
        entity_id: sensor.example
        state: [on, off]
        for: '00:00:10'
      - condition: state
        entity_id: sensor.example
        state: input_select.mode
        for: '00:00:10'
"""


def fake_rule(identifier, introduced):
    return {
        "rule_id": identifier,
        "introduced_in": introduced,
        "official_group": "Example change",
        "module": "core_compatibility_checks",
        "function": "find_state_condition_conflicts",
        "input_kind": "active_yaml",
        "check_parameters": {"prohibited_patterns": ["attribute_with_for"]},
    }


class WindowSelectionTests(unittest.TestCase):
    def test_stable_release_parses_without_patch(self):
        self.assertEqual(parse_stable_core_version("2027.1"), (2027, 1, 0))

    def test_prereleases_not_assumed_stable(self):
        for value in ("2026.10.0b1", "2026.10.0rc1", "2026.10.0.dev0", "dev", None):
            with self.subTest(version=value):
                self.assertIsNone(parse_stable_core_version(value))

    def test_impossible_month_is_rejected(self):
        for value in ("2027.0.1", "2027.13.0", "2027.-1.0"):
            with self.subTest(version=value):
                self.assertIsNone(parse_stable_core_version(value))

    def test_current_upgrade_selects_one_october_rule(self):
        result = select_compatibility_rules("2026.8.3", "2026.10.4")
        self.assertEqual(result["status"], "selected")
        self.assertEqual([r["rule_id"] for r in result["selected_rules"]],
                         ["core_2026_10_state_conditions_for"])
        self.assertEqual(result["crossed_release_families"], ["2026.9", "2026.10"])

    def test_patch_only_upgrade_does_not_reapply_prior_rule(self):
        result = select_compatibility_rules("2026.10.2", "2026.10.4")
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_rules"], [])
        self.assertEqual(result["crossed_release_families"], [])

    def test_future_release_without_registered_rule_remains_unassessed(self):
        result = select_compatibility_rules("2026.10.4", "2026.11.1")
        self.assertEqual(result["status"], "selected")
        self.assertEqual(result["selected_rules"], [])
        self.assertEqual(result["families_without_registered_rules"], ["2026.11"])
        self.assertFalse(result["readiness_verdict_produced"])

    def test_year_boundary_crossing(self):
        result = select_compatibility_rules("2026.12.3", "2027.2.1")
        self.assertEqual(result["crossed_release_families"], ["2027.1", "2027.2"])
        self.assertEqual(result["families_without_registered_rules"], ["2027.1", "2027.2"])

    def test_future_rule_can_be_registered_without_updating_selector(self):
        future = fake_rule("new_future_check", "2027.1")
        result = select_compatibility_rules("2026.12.3", "2027.2.1", registry=[future])
        self.assertEqual([r["rule_id"] for r in result["selected_rules"]],
                         ["new_future_check"])
        self.assertEqual(result["families_without_registered_rules"], ["2027.2"])

    def test_rule_at_installed_version_not_rerun(self):
        result = select_compatibility_rules("2026.10.0", "2027.1.0")
        self.assertEqual(result["selected_rules"], [])

    def test_window_with_no_change_has_no_update_status(self):
        self.assertEqual(select_compatibility_rules("2026.10.4", "2026.10.4")["status"],
                         "no_update")

    def test_downgrade_is_not_an_upgrade(self):
        self.assertEqual(select_compatibility_rules("2026.10.4", "2026.9.4")["status"],
                         "unsupported_downgrade")

    def test_unparseable_version_cannot_produce_rule_selection(self):
        result = select_compatibility_rules("unknown", "2026.10.4")
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["readiness_verdict_produced"])

    def test_registry_duplicates_are_rejected(self):
        repeated = fake_rule("future", "2027.1")
        with self.assertRaises(ValueError):
            select_compatibility_rules("2026.12", "2027.1", registry=[repeated, repeated])

    def test_invalid_registry_descriptors_are_rejected(self):
        invalid = fake_rule("valid", "2027.13")
        with self.assertRaises(ValueError):
            select_compatibility_rules("2026.12", "2027.1", registry=[invalid])

    def test_rule_parameter_data_is_not_mutated_by_selection(self):
        original = copy.deepcopy(RULE_REGISTRY)
        select_compatibility_rules("2026.8.3", "2026.10.1")
        select_compatibility_rules("2026.8.3", "2026.10.4")
        self.assertEqual(original, RULE_REGISTRY)

    def test_selected_output_is_not_safe_to_update_verdict(self):
        result = select_compatibility_rules("2026.8.3", "2027.2.1")
        self.assertFalse(result["readiness_verdict_produced"])
        self.assertNotIn("safe", result["status"])


class PatchPolicyAndScanTests(unittest.TestCase):
    def _scan_for_target(self, version, source="automations.yaml"):
        selected = select_compatibility_rules("2026.9.4", version)["selected_rules"]
        self.assertEqual(len(selected), 1)
        rule = selected[0]
        self.assertEqual(rule["module"], "core_compatibility_checks")
        self.assertEqual(rule["function"], "find_state_condition_conflicts")
        return find_state_condition_conflicts(
            STATE_YAML,
            source=source,
            rule_id=rule["rule_id"],
            **rule["check_parameters"],
        )

    def test_original_october_restrictions_found(self):
        findings = self._scan_for_target("2026.10.1")
        self.assertEqual(len(findings), 3)
        self.assertEqual([f["line"] for f in findings], [3, 9, 13])

    def test_october_patch_restores_state_list_with_duration(self):
        findings = self._scan_for_target("2026.10.2")
        self.assertEqual(len(findings), 2)
        self.assertEqual([f["reasons"] for f in findings],
                         [["attribute_with_for"], ["helper_state_with_for"]])

    def test_later_patch_still_uses_corrected_policy(self):
        findings = self._scan_for_target("2026.10.4")
        self.assertEqual(len(findings), 2)

    def test_future_target_respects_existing_patch_override(self):
        findings = self._scan_for_target("2027.1.1")
        self.assertEqual(len(findings), 2)

    def test_originating_rule_is_not_hardcoded_into_scanner(self):
        findings = find_state_condition_conflicts(
            STATE_YAML, rule_id="independent_future_rule",
            prohibited_patterns=["state_list_with_for"],
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "independent_future_rule")

    def test_rule_name_and_source_are_preserved_in_finding(self):
        findings = self._scan_for_target("2026.10.1", source="entities/test.yaml")
        self.assertTrue(all(f["file"] == "entities/test.yaml" for f in findings))
        self.assertTrue(all(f["rule_id"] == "core_2026_10_state_conditions_for"
                            for f in findings))

    def test_triggers_are_not_misclassified_as_conditions(self):
        text = """trigger: state
entity_id: sensor.example
state: [on, off]
for: '00:00:10'
"""
        findings = find_state_condition_conflicts(
            text, rule_id="example", prohibited_patterns=["state_list_with_for"])
        self.assertEqual(findings, [])

    def test_ordinary_state_for_condition_remains_valid(self):
        text = """condition: state
entity_id: binary_sensor.test
state: 'on'
for: '00:00:10'
"""
        findings = find_state_condition_conflicts(
            text, rule_id="example", prohibited_patterns=["attribute_with_for",
                                                                 "helper_state_with_for"])
        self.assertEqual(findings, [])

    def test_invalid_yaml_must_not_be_reported_clear(self):
        with self.assertRaises(yaml.YAMLError):
            find_state_condition_conflicts("condition: [", rule_id="example",
                                           prohibited_patterns=["attribute_with_for"])

    def test_unsupported_pattern_must_not_be_skipped(self):
        with self.assertRaises(ValueError):
            find_state_condition_conflicts(STATE_YAML, rule_id="example",
                                           prohibited_patterns=["unrecognised_check"])

    def test_cyclic_yaml_cannot_be_assumed_clean(self):
        with self.assertRaises(ValueError):
            find_state_condition_conflicts("a: &a\n  b: *a\n", rule_id="example",
                                           prohibited_patterns=["attribute_with_for"])

    def test_invalid_patch_policy_is_rejected(self):
        rule = fake_rule("example", "2027.1")
        rule["parameter_overrides"] = [{
            "effective_from": "2026.12.1",
            "check_parameters": {"prohibited_patterns": []},
        }]
        with self.assertRaises(ValueError):
            select_compatibility_rules("2026.12.1", "2027.1.1", registry=[rule])

    def test_duplicate_patch_versions_are_rejected(self):
        rule = fake_rule("example", "2027.1")
        rule["parameter_overrides"] = [
            {"effective_from": "2027.1.2", "check_parameters": {"prohibited_patterns": []}},
            {"effective_from": "2027.1.2", "check_parameters": {"prohibited_patterns": []}},
        ]
        with self.assertRaises(ValueError):
            select_compatibility_rules("2026.12.1", "2027.1.3", registry=[rule])


if __name__ == "__main__":
    unittest.main()
