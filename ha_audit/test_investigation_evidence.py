#!/usr/bin/env python3
"""Regression tests for existing read-only investigation evidence checks.

Run: python3 ha_audit/test_investigation_evidence.py
Uses synthetic log/Recorder data; does not contact Home Assistant or edit reports.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import maintenance_window_evidence as maintenance
import power_state_evidence as power


SHELLY_FIRST = "2026-10-21T11:56:19+00:00"  # 12:56:19 BST
SHELLY_LAST = "2026-10-29T03:01:14+00:00"  # 03:01:14 GMT
SONOS_FIRST = "2026-10-29T11:18:45+00:00"
SONOS_LAST = "2026-10-29T11:18:52+00:00"


def family(family_id, first_seen, last_seen, count=64):
    return {
        "family_id": family_id,
        "occurrence_count": count,
        "members": [{"first_seen": first_seen, "last_seen": last_seen}],
    }


def schedule(start="03:00", end="03:05", **options):
    return {
        "start_local": start,
        "end_local": end,
        "timezone": "Europe/London",
        "schedule": "daily",
        **options,
    }


class InvestigationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.log_file = Path(self.tempdir.name) / "log_issue_families.json"
        self.write_log([
            family("shelly", SHELLY_FIRST, SHELLY_LAST),
            family("sonos", SONOS_FIRST, SONOS_LAST, count=4),
        ])

    def write_log(self, families):
        self.log_file.write_text(
            json.dumps({"families": families}), encoding="utf-8"
        )

    def check_maintenance(self, window, family_id="shelly"):
        return maintenance.check_maintenance_window(
            family_id, window, log_file=self.log_file
        )

    def check_power(self, family_id="sonos", switch="switch.backroom_tv_cabinet_r"):
        return power.check_power_state(
            family_id, switch, log_file=self.log_file
        )

    def test_daily_window_converts_bst_gmt_and_preserves_counts(self):
        result = self.check_maintenance(schedule())
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["counts"], {"inside": 1, "outside": 1, "unknown": 0})
        self.assertEqual(result["source_occurrence_count"], 64)
        self.assertEqual(result["sample_count"], 2)
        self.assertEqual(result["samples"][0]["window_match"], "inside")
        self.assertTrue(result["samples"][1]["observed_at_local"].endswith("+01:00"))
        self.assertIn("not", result["limitation"].lower())

    def test_window_boundaries_start_inclusive_end_exclusive(self):
        self.write_log([family("shelly", "2026-10-29T03:00:00+00:00",
                               "2026-10-29T03:05:00+00:00", 2)])
        self.assertEqual(self.check_maintenance(schedule())["counts"],
                         {"inside": 1, "outside": 1, "unknown": 0})

    def test_weekly_overnight_uses_start_day(self):
        # Sunday 25 Oct 2026 23:58 GMT -> Monday 26 Oct 00:02 GMT.
        self.write_log([family("shelly", "2026-10-25T23:58:00+00:00",
                               "2026-10-26T00:02:00+00:00", 2)])
        result = self.check_maintenance(schedule(
            "23:55", "00:05", schedule="weekly", weekdays=[6]
        ))
        self.assertEqual(result["counts"], {"inside": 2, "outside": 0, "unknown": 0})

    def test_weekly_requires_selected_days(self):
        result = self.check_maintenance(schedule(schedule="weekly", weekdays=[]))
        self.assertEqual(result["status"], "invalid_schedule")
        self.assertFalse(result["samples"])

    def test_monthly_date_requires_actual_day(self):
        self.write_log([family("shelly", "2026-02-28T03:01:00+00:00",
                               "2026-03-31T02:01:00+00:00", 2)])
        result = self.check_maintenance(schedule(
            schedule="monthly_date", day_of_month=31
        ))
        # March 31 is BST, so 02:01 UTC corresponds to 03:01 BST.
        self.assertEqual(result["counts"], {"inside": 1, "outside": 1, "unknown": 0})

    def test_monthly_last_weekday(self):
        self.write_log([family("shelly", "2026-10-18T02:01:00+00:00",
                               "2026-10-25T03:01:00+00:00", 2)])
        result = self.check_maintenance(schedule(
            schedule="monthly_weekday", weekday=6, occurrence="last"
        ))
        self.assertEqual(result["counts"], {"inside": 1, "outside": 1, "unknown": 0})

    def test_invalid_timezone_does_not_claim_inside(self):
        result = self.check_maintenance(schedule(timezone="Not/A_Real_Zone"))
        self.assertEqual(result["status"], "invalid_schedule")
        self.assertEqual(result["counts"]["inside"], 0)

    def test_missing_log_data_does_not_claim_inside(self):
        self.write_log([])
        result = self.check_maintenance(schedule())
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertFalse(result["samples"])

    def test_power_samples_off_on_unknown_without_network(self):
        states = iter([
            ("off", "Recorded off"),
            ("on", "Recorded on"),
        ])
        with patch.object(power, "_get_recorded_state", side_effect=lambda *_: next(states)):
            result = self.check_power()
        self.assertEqual(result["status"], "ok")
        self.assertEqual([s["power_state"] for s in result["samples"]], ["off", "on"])
        self.assertEqual([s["interpretation"] for s in result["samples"]], [
            "consistent_with_expected_power_off", "needs_investigation"
        ])
        with patch.object(power, "_get_recorded_state", return_value=("unknown", "No history")):
            result = self.check_power()
        self.assertTrue(all(s["interpretation"] == "unknown" for s in result["samples"]))

    def test_recorder_history_cannot_use_future_or_missing_state(self):
        observed_at = datetime(2026, 10, 29, 11, 18, 47, tzinfo=timezone.utc)
        history = [[
            {"state": "off", "last_changed": "2026-10-29T11:17:53+00:00"},
            {"state": "on", "last_changed": "2026-10-29T11:20:00+00:00"},
        ]]
        self.assertEqual(power._state_from_history(history, observed_at), "off")
        self.assertEqual(power._state_from_history([[history[0][1]]], observed_at), "unknown")
        self.assertEqual(power._state_from_history([], observed_at), "unknown")

    def test_power_rejects_untrusted_entity_ids(self):
        self.assertEqual(self.check_power(switch="sensor.fake")["status"], "invalid")
        self.assertEqual(self.check_power(family_id="../../config")["status"], "invalid")

    def test_power_off_in_mixed_device_family_is_not_device_verified(self):
        """Do not attribute multi-speaker log records to one smart plug.

        When a family contains records for different devices, the link between
        a sampled error and the saved power switch cannot be established.
        Fail closed as UNKNOWN even if the physical switch could be OFF.
        """
        self.write_log([{
            "family_id": "sonos",
            "occurrence_count": 2,
            "members": [
                {
                    "first_seen": "2026-10-29T11:18:45+00:00",
                    "last_seen": "2026-10-29T11:18:45+00:00",
                    "name": "homeassistant.components.sonos.speaker",
                    "messages": ["No recent activity and cannot reach Backroom"],
                },
                {
                    "first_seen": "2026-10-29T11:18:52+00:00",
                    "last_seen": "2026-10-29T11:18:52+00:00",
                    "name": "homeassistant.components.sonos.speaker",
                    "messages": ["No recent activity and cannot reach Living Room"],
                },
            ],
        }])
        with patch.object(power, "_get_recorded_state",
                          return_value=("off", "Recorded switch OFF")) as get_state:
            result = self.check_power()
            # Mixed-device evidence is not tied to the configured device, so
            # the Recorder lookup must not be used to justify an OFF verdict.
            get_state.assert_not_called()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["samples"]), 2)
        self.assertTrue(all(
            sample["power_state"] == "unknown"
            and sample["interpretation"] == "unknown"
            for sample in result["samples"]
        ), "Mixed-device family timestamps must remain UNKNOWN")
        self.assertIn("device", result["limitation"].lower())

    def test_both_checks_limit_samples_not_expand_grouped_occurrences(self):
        records = []
        for i in range(8):
            records.append({
                "first_seen": f"2026-10-{20+i:02d}T03:01:00+00:00",
                "last_seen": f"2026-10-{20+i:02d}T03:02:00+00:00",
            })
        self.write_log([{"family_id": "shelly", "occurrence_count": 120,
                         "members": records}])
        maintenance_result = self.check_maintenance(schedule())
        self.assertEqual(maintenance_result["sample_count"], 4)
        self.assertEqual(maintenance_result["source_occurrence_count"], 120)
        with patch.object(power, "_get_recorded_state", return_value=("off", "Synthetic")):
            power_result = self.check_power(family_id="shelly")
        self.assertEqual(len(power_result["samples"]), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
