#!/usr/bin/env python3
"""Read-only scheduled-maintenance evidence for HA Audit investigations.

Compare sampled Home Assistant System Log *source-record timestamps* against
one user-configured recurring local-time maintenance schedule. Matching the
schedule is not proof that maintenance occurred or caused an error. Logs are
Home Assistant-deduplicated; first/last timestamps are not every occurrence.

No Home Assistant requests, writes, priority changes, or status changes.
User-controlled configuration is checked here even though the Web UI also
validates it. A missing timezone database fails closed (UNKNOWN), never INSIDE.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LOG_FAMILIES = Path("/config/log_issue_families.json")
MAX_JSON_BYTES = 1024 * 1024
MAX_MEMBERS = 25
MAX_SAMPLES = 4
TIME_PATTERN = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z")
FAMILY_ID_PATTERN = re.compile(r"[a-z0-9_]+\Z")
FREQUENCIES = {"daily", "weekly", "monthly_date", "monthly_weekday"}
OCCURRENCES = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def _parse_instant(value: object) -> datetime | None:
    """Accept explicit-offset timestamps only (never assume local or UTC)."""
    if not isinstance(value, str) or len(value) > 50:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else None
    except (ValueError, OverflowError):
        return None


def _parse_window(window: object) -> tuple[dict | None, str]:
    """Revalidate the exact schema saved by the Web UI in v0.8.20."""
    if not isinstance(window, dict):
        return None, "Missing maintenance schedule"
    start = window.get("start_local")
    end = window.get("end_local")
    tz_name = window.get("timezone")
    frequency = window.get("schedule", "daily")
    if (not isinstance(start, str) or not TIME_PATTERN.fullmatch(start)
            or not isinstance(end, str) or not TIME_PATTERN.fullmatch(end)
            or start == end):
        return None, "Invalid maintenance start/end times"
    if (not isinstance(tz_name, str) or not 1 <= len(tz_name) <= 64
            or not isinstance(frequency, str) or frequency not in FREQUENCIES):
        return None, "Invalid timezone or maintenance frequency"
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return None, "Timezone data unavailable or timezone not recognised"

    rule = {
        "start_min": int(start[:2]) * 60 + int(start[3:]),
        "end_min": int(end[:2]) * 60 + int(end[3:]),
        "frequency": frequency,
        "timezone": tz,
    }
    if frequency == "weekly":
        days = window.get("weekdays")
        if (not isinstance(days, list) or not days or len(days) > 7
                or any(type(day) is not int or day < 0 or day > 6 for day in days)
                or len(set(days)) != len(days)):
            return None, "Invalid weekly weekdays"
        rule["weekdays"] = frozenset(days)
    elif frequency == "monthly_date":
        day = window.get("day_of_month")
        if type(day) is not int or not 1 <= day <= 31:
            return None, "Invalid monthly calendar day"
        rule["day_of_month"] = day
    elif frequency == "monthly_weekday":
        occurrence = window.get("occurrence")
        weekday = window.get("weekday")
        if (not isinstance(occurrence, str)
                or occurrence not in {*OCCURRENCES, "last"}
                or type(weekday) is not int or not 0 <= weekday <= 6):
            return None, "Invalid monthly weekday schedule"
        rule["occurrence"] = occurrence
        rule["weekday"] = weekday
    return rule, ""


def _scheduled_on_day(day: date, rule: dict) -> bool:
    """Test the calendar date the maintenance *starts*, not the end date."""
    frequency = rule["frequency"]
    if frequency == "daily":
        return True
    if frequency == "weekly":
        return day.weekday() in rule["weekdays"]
    if frequency == "monthly_date":
        return day.day == rule["day_of_month"]
    if day.weekday() != rule["weekday"]:
        return False
    occurrence = rule["occurrence"]
    if occurrence == "last":
        return (day + timedelta(days=7)).month != day.month
    return (day.day - 1) // 7 + 1 == OCCURRENCES[occurrence]


def _in_window(instant: datetime, rule: dict) -> tuple[bool, str]:
    """Compare actual UTC instant to wall time in the configured IANA zone.

    For overnight windows, times after midnight belong to the *previous*
    date's scheduled occurrence. `start` is inclusive, `end` exclusive.
    Converting from UTC handles BST/GMT and repeated autumn clock times.
    """
    local = instant.astimezone(rule["timezone"])
    minute = local.hour * 60 + local.minute
    start, end = rule["start_min"], rule["end_min"]
    if start < end:  # ordinary same-day window
        in_range = start <= minute < end
        scheduled_day = local.date()
    else:  # crosses midnight
        in_range = minute >= start or minute < end
        scheduled_day = (
            local.date() - timedelta(days=1)
            if minute < end else local.date()
        )
    return (in_range and _scheduled_on_day(scheduled_day, rule),
            local.isoformat(timespec="seconds"))


def _logged_times(family_id: str, log_file: Path) -> tuple[list[datetime], int | None, str]:
    """Take actual first/last timestamps from the same source as Sonos.

    Deliberately do not fabricate individual occurrences between those times.
    """
    try:
        if log_file.stat().st_size > MAX_JSON_BYTES:
            return [], None, "Log-family report is too large"
        payload = json.loads(log_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return [], None, "Log-family report unavailable"
    if not isinstance(payload, dict) or not isinstance(payload.get("families"), list):
        return [], None, "Log-family report has an invalid format"
    family = next((item for item in payload["families"]
                   if isinstance(item, dict) and item.get("family_id") == family_id), None)
    if family is None:
        return [], None, "Finding not present in the log-family report"
    total = family.get("occurrence_count")
    total = total if type(total) is int and 0 <= total <= 1_000_000_000 else None
    members = family.get("members")
    if not isinstance(members, list):
        return [], total, "No source log entries available"
    now_utc = datetime.now(timezone.utc)
    instants = set()
    for item in members[:MAX_MEMBERS]:
        if not isinstance(item, dict):
            continue
        for field in ("first_seen", "last_seen"):
            instant = _parse_instant(item.get(field))
            if instant is not None and instant <= now_utc:
                instants.add(instant)
    return sorted(instants, reverse=True)[:MAX_SAMPLES], total, ""


def check_maintenance_window(
    family_id: str, window: dict, *, log_file: Path = LOG_FAMILIES,
) -> dict:
    """Return bounded sampled evidence; never treat matching as proof of cause.

    `window` must be the saved `investigations[fingerprint].maintenance_window`.
    The caller is responsible for confirming the relationship to this finding.
    """
    if not isinstance(family_id, str) or not FAMILY_ID_PATTERN.fullmatch(family_id):
        return {"status": "invalid", "message": "Invalid issue identifier",
                "samples": [], "counts": {"inside": 0, "outside": 0, "unknown": 0}}
    rule, error = _parse_window(window)
    if rule is None:
        return {"status": "invalid_schedule", "message": error,
                "samples": [], "counts": {"inside": 0, "outside": 0, "unknown": 0}}
    times, occurrences, source_error = _logged_times(family_id, log_file)
    if not times:
        return {
            "status": "insufficient_evidence",
            "family_id": family_id,
            "message": source_error or "No sampled source-record timestamps available",
            "source_occurrence_count": occurrences,
            "sample_count": 0,
            "counts": {"inside": 0, "outside": 0, "unknown": 0},
            "samples": [],
        }
    counts = {"inside": 0, "outside": 0, "unknown": 0}
    samples = []
    for instant in times:
        try:
            inside, local_time = _in_window(instant, rule)
            match = "inside" if inside else "outside"
            basis = ("Timestamp falls within the configured schedule"
                     if inside else "Timestamp falls outside the configured schedule")
        except (ValueError, OverflowError):
            match, local_time, basis = "unknown", "", "Cannot resolve local time"
        counts[match] += 1
        samples.append({
            "observed_at_utc": instant.isoformat(timespec="seconds"),
            "observed_at_local": local_time,
            "window_match": match,
            "evidence": basis,
        })
    if counts["outside"]:
        interpretation = "Some sampled errors occurred outside scheduled maintenance"
        recommendation = "Investigate outside-window samples; keep monitoring."
    elif counts["unknown"]:
        interpretation = "Insufficient evidence for some samples"
        recommendation = "Do not dismiss unverified samples."
    else:
        interpretation = "All sampled timestamps match the configured schedule"
        recommendation = "Matches support a maintenance explanation, not proof. Monitor new errors."
    return {
        "status": "ok",
        "family_id": family_id,
        "source_occurrence_count": occurrences,
        "sample_count": len(samples),
        "counts": counts,
        "interpretation": interpretation,
        "recommendation": recommendation,
        "samples": samples,
        "limitation": (
            "Only sampled first/last System Log record timestamps were checked; "
            "deduplicated occurrence counts are not per-event timestamps. "
            "A time-window match does not verify that maintenance took place "
            "or caused the error. Unsampled errors are unassessed. "
            "Original technical priority and user status remain unchanged."
        ),
    }
