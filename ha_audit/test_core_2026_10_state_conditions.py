"""Regression tests for the read-only Core 2026.10 state-condition scanner.

Run from the ha_audit directory:
    python test_core_2026_10_state_conditions.py

The scanner is not yet part of the audit pipeline. These tests protect its
standalone behaviour before it is integrated into update-readiness reporting.
"""

import unittest

import yaml

from core_2026_10_state_conditions import (
    RULE_ID,
    find_unsupported_state_durations,
)


class StateConditionDurationTests(unittest.TestCase):
    def scan(self, text, source="automations.yaml"):
        return find_unsupported_state_durations(text, source=source)

    def test_attribute_with_for_is_reported_with_location(self):
        matches = self.scan("""conditions:
  - condition: state
    entity_id: climate.living_room
    attribute: hvac_action
    state: heating
    for:
      minutes: 5
""")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0], {
            "rule_id": RULE_ID,
            "file": "automations.yaml",
            "line": 2,
            "entity_id": "climate.living_room",
            "reasons": ["attribute_with_for"],
        })

    def test_state_list_with_for_is_reported(self):
        matches = self.scan("""condition: state
entity_id: alarm_control_panel.home
state: [armed_home, armed_away]
for: "00:05:00"
""")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reasons"], ["state_list_with_for"])

    def test_each_supported_helper_as_state_with_for_is_reported(self):
        helpers = (
            "input_boolean.flag",
            "input_datetime.schedule",
            "input_number.threshold",
            "input_select.mode",
            "input_text.expected_state",
        )
        for helper in helpers:
            with self.subTest(helper=helper):
                matches = self.scan(f"""condition: state
entity_id: sensor.reading
state: {helper}
for: "00:00:30"
""")
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]["reasons"], ["helper_state_with_for"])

    def test_case_insensitive_helper_id_is_handled(self):
        matches = self.scan("""condition: state
entity_id: sensor.value
state: INPUT_SELECT.MODE
for: 15
""")
        self.assertEqual(matches[0]["reasons"], ["helper_state_with_for"])

    def test_multiple_conflicts_produce_one_finding(self):
        matches = self.scan("""condition: state
entity_id: climate.test
attribute: supported_modes
state: [heat, cool]
for: "00:00:20"
""")
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0]["reasons"],
            ["attribute_with_for", "state_list_with_for"],
        )

    def test_simple_state_with_for_is_not_reported(self):
        self.assertEqual(self.scan("""condition: state
entity_id: binary_sensor.motion
state: "off"
for:
  minutes: 5
"""), [])

    def test_multiple_entity_ids_with_literal_state_and_for_are_not_reported(self):
        self.assertEqual(self.scan("""condition: state
entity_id: [light.kitchen, light.living_room]
match: any
state: "on"
for: "00:02:00"
"""), [])

    def test_attribute_without_for_is_not_reported(self):
        self.assertEqual(self.scan("""condition: state
entity_id: climate.test
attribute: hvac_action
state: heating
"""), [])

    def test_list_without_for_is_not_reported(self):
        self.assertEqual(self.scan("""condition: state
entity_id: person.a
state: [home, away]
"""), [])

    def test_helper_as_state_without_for_is_not_reported(self):
        self.assertEqual(self.scan("""condition: state
entity_id: sensor.value
state: input_select.mode
"""), [])

    def test_helper_as_entity_id_does_not_trigger_helper_state_rule(self):
        self.assertEqual(self.scan("""condition: state
entity_id: input_boolean.mode
state: "on"
for: "00:01:00"
"""), [])

    def test_other_condition_types_are_not_reported(self):
        self.assertEqual(self.scan("""condition: numeric_state
entity_id: sensor.temp
attribute: target
state: [1, 2]
for: "00:01:00"
"""), [])

    def test_state_trigger_with_for_is_not_a_state_condition(self):
        self.assertEqual(self.scan("""triggers:
  - trigger: state
    entity_id: light.test
    attribute: brightness
    to: "on"
    for: "00:00:30"
conditions:
  - condition: state
    entity_id: light.test
    state: "on"
"""), [])

    def test_nested_or_choose_and_if_are_scanned(self):
        matches = self.scan("""actions:
  - choose:
      - conditions:
          - condition: or
            conditions:
              - condition: state
                entity_id: light.x
                state: [on, off]
                for: "00:01:00"
        sequence:
          - if:
              - condition: state
                entity_id: climate.y
                attribute: hvac_action
                state: heating
                for: "00:02:00"
            then: []
""", source="scripts.yaml")
        self.assertEqual(len(matches), 2)
        self.assertEqual([item["line"] for item in matches], [6, 12])
        self.assertTrue(all(item["file"] == "scripts.yaml" for item in matches))

    def test_comment_examples_are_ignored(self):
        self.assertEqual(self.scan("""# condition: state
# state: [on, off]
# for: "00:05:00"
condition: template
value_template: "{{ true }}"
"""), [])

    def test_custom_yaml_tags_do_not_prevent_structure_inspection(self):
        matches = self.scan("""- condition: state
  entity_id: !secret climate_id
  state: [heat, cool]
  for: "00:03:00"
""")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["reasons"], ["state_list_with_for"])

    def test_empty_document_returns_no_findings(self):
        self.assertEqual(self.scan("# no active content\n"), [])

    def test_malformed_yaml_does_not_silently_return_clear(self):
        with self.assertRaises(yaml.YAMLError):
            self.scan("condition: [unterminated")

    def test_cyclic_yaml_alias_does_not_silently_return_clear(self):
        with self.assertRaises(ValueError):
            self.scan("a: &anchor\n  b: *anchor\n")

    def test_non_text_input_does_not_silently_return_clear(self):
        with self.assertRaises(ValueError):
            find_unsupported_state_durations(None)

    def test_nesting_limit_does_not_silently_return_clear(self):
        deep = "[" * 85 + "true" + "]" * 85
        with self.assertRaises(ValueError):
            self.scan(deep)


if __name__ == "__main__":
    unittest.main()
