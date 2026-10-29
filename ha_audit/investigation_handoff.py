#!/usr/bin/env python3
"""Append saved user investigation feedback to HA Audit's AI handoff.

Run AFTER ai_handoff.py, which rebuilds the handoff on every audit.
This module reads feedback created by the Ingress web UI. It never edits
investigation storage, audit priorities, or Home Assistant configuration.

Kept separate from ai_handoff.py to avoid changing the existing audit logic.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone

from power_state_evidence import check_power_state
from maintenance_window_evidence import check_maintenance_window
from pathlib import Path

CONTEXT_FILE = Path("/config/investigation_context.json")
FINDINGS_FILE = Path("/config/log_priority_final.json")
HANDOFF_FILE = Path("/config/ha_audit_ai_handoff.md")
START_MARKER = "<!-- HA_AUDIT_INVESTIGATION_CONTEXT_START -->"
END_MARKER = "<!-- HA_AUDIT_INVESTIGATION_CONTEXT_END -->"
MAX_BYTES = 1024 * 1024
MAX_FEEDBACK_ITEMS = 200
MAX_POWER_CHECKS = 4  # Bound Recorder requests during the audit.
MAX_MAINTENANCE_CHECKS = 8  # Bounded local-file checks; no extra HA requests.
EVIDENCE_FILE = Path("/config/investigation_evidence.json")
MAINTENANCE_EVIDENCE_FILE = Path("/config/investigation_maintenance_evidence.json")
SWITCH_ID = re.compile(r"switch\.[a-z0-9_]+\Z")
VALID_STATUSES = {"Investigating", "Monitoring", "Explained", "Resolved"}


def read_json_file(path: Path) -> dict | None:
    try:
        if path.stat().st_size > MAX_BYTES:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError, UnicodeError):
        return None


def one_line(value: object, limit: int = 200) -> str:
    """Render user text safely in a Markdown quote, not as instructions."""
    text = " ".join(str(value).split()).strip()
    return text[:limit]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def power_recommendation(off: int, on: int, unknown: int) -> tuple[str, str]:
    """Interpret sampled switch state, without modifying technical priority."""
    if on:
        return (
            "Needs investigation",
            "Some sampled errors occurred while the switch was ON. Investigate "
            "those timestamps even if the user marked the issue Explained.",
        )
    if off and not unknown:
        return (
            "Consistent with expected power-off",
            "No immediate action indicated by these sampled OFF-only events. "
            "Investigate new errors while powered ON, or where power state is unknown.",
        )
    if off:
        return (
            "Partially supported; unverified samples remain",
            "OFF samples support the power-off explanation, but UNKNOWN samples "
            "remain unresolved. Check available history before dismissing errors.",
        )
    return (
        "Insufficient evidence",
        "No reliable power-state match is available. Do not dismiss this "
        "finding based on the saved explanation alone.",
    )


def gather_power_evidence(context: dict, findings: dict) -> dict:
    """Check confirmed relationships after the audit, never changing findings.

    The result is an evidence snapshot, not a user verdict or severity score.
    Source timestamps are first/last records sampled by power_state_evidence.
    """
    report: dict = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "source": "Home Assistant System Log record timestamps and Recorder switch history",
        "scope": "At most four first/last timestamps per finding, not all errors",
        "changes_audit_priorities": False,
        "findings": {},
    }
    investigations = context.get("investigations")
    families = findings.get("families")
    if not isinstance(investigations, dict) or not isinstance(families, list):
        return report

    # Only examine current findings with a saved physical switch relationship.
    # Never infer switch associations from free-text notes.
    for family in families:
        if len(report["findings"]) >= MAX_POWER_CHECKS:
            break
        if not isinstance(family, dict):
            continue
        fingerprint = family.get("stable_fingerprint")
        family_id = family.get("family_id")
        if not isinstance(fingerprint, str) or not isinstance(family_id, str):
            continue
        saved = investigations.get(fingerprint)
        if not isinstance(saved, dict):
            continue
        switch = saved.get("power_entity_id")
        if not isinstance(switch, str) or not SWITCH_ID.fullmatch(switch):
            continue

        try:
            checked = check_power_state(family_id, switch)
        except Exception:
            # Evidence failure must not prevent generation of the AI handoff.
            checked = {"status": "unavailable", "samples": [],
                       "message": "Power-state check failed"}
        samples = checked.get("samples")
        if not isinstance(samples, list):
            samples = []
        samples = [item for item in samples[:4] if isinstance(item, dict)]
        counts = {"off": 0, "on": 0, "unknown": 0}
        sanitized = []
        for item in samples:
            state = item.get("power_state", "unknown")
            state = state if state in ("on", "off") else "unknown"
            counts[state] += 1
            sanitized.append({
                "observed_at_utc": one_line(item.get("observed_at_utc", ""), 50),
                "power_state": state,
                "evidence": one_line(item.get("evidence", ""), 140),
            })
        interpretation, recommendation = power_recommendation(
            counts["off"], counts["on"], counts["unknown"]
        )
        report["findings"][fingerprint] = {
            "title": one_line(family.get("title", "Unnamed finding"), 150),
            "family_id": family_id,
            "audit_priority": one_line(family.get("final_priority", ""), 20),
            "user_status": one_line(saved.get("status", ""), 20),
            "feedback_updated_at_utc": one_line(saved.get("updated_at_utc", ""), 50),
            "power_entity_id": switch,
            "source_status": one_line(checked.get("status", "unavailable"), 32),
            "source_message": one_line(checked.get("message", ""), 200),
            "sample_count": len(sanitized),
            "counts": counts,
            "interpretation": interpretation,
            "recommendation": recommendation,
            "samples": sanitized,
        }
    return report


def save_evidence_snapshot(report: dict) -> bool:
    """Atomically replace the last-run read-only evidence snapshot."""
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(
            prefix=".ha-audit-power-", suffix=".tmp", dir=EVIDENCE_FILE.parent
        )
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, EVIDENCE_FILE)
        return True
    except OSError:
        return False
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def gather_maintenance_evidence(context: dict, findings: dict) -> dict:
    """Check each current finding with a saved recurring maintenance schedule.

    This is *time correlation*, not verification that a reboot took place.
    Only the actual source-record first/last timestamps can be classified;
    HA's deduplicated occurrence counts are not a series of event times.
    """
    report: dict = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "source": "Home Assistant System Log source-record timestamps",
        "scope": "Up to four first/last timestamps per finding; unsampled errors unassessed",
        "changes_audit_priorities": False,
        "findings": {},
    }
    investigations = context.get("investigations")
    families = findings.get("families")
    if not isinstance(investigations, dict) or not isinstance(families, list):
        return report

    for family in families:
        if len(report["findings"]) >= MAX_MAINTENANCE_CHECKS:
            break
        if not isinstance(family, dict):
            continue
        fingerprint, family_id = family.get("stable_fingerprint"), family.get("family_id")
        if not isinstance(fingerprint, str) or not isinstance(family_id, str):
            continue
        saved = investigations.get(fingerprint)
        if not isinstance(saved, dict):
            continue
        window = saved.get("maintenance_window")
        if not isinstance(window, dict):
            continue

        try:
            checked = check_maintenance_window(family_id, window)
        except Exception:
            # A malformed schedule or evidence file must not stop the audit.
            checked = {
                "status": "unavailable", "message": "Maintenance check failed",
                "samples": [],
            }

        raw_samples = checked.get("samples")
        if not isinstance(raw_samples, list):
            raw_samples = []
        counts = {"inside": 0, "outside": 0, "unknown": 0}
        samples = []
        for raw in raw_samples[:4]:
            if not isinstance(raw, dict):
                continue
            match = raw.get("window_match")
            match = match if match in counts else "unknown"
            counts[match] += 1
            samples.append({
                "observed_at_utc": one_line(raw.get("observed_at_utc", ""), 50),
                "observed_at_local": one_line(raw.get("observed_at_local", ""), 50),
                "window_match": match,
                "evidence": one_line(raw.get("evidence", ""), 140),
            })

        if checked.get("status") != "ok":
            interpretation = "Unable to verify scheduled maintenance against log timestamps"
            recommendation = "Keep monitoring; do not assume errors occurred during maintenance."
        elif counts["outside"]:
            interpretation = "Some sampled errors occurred outside scheduled maintenance"
            recommendation = "Investigate outside-window samples; keep monitoring."
        elif counts["unknown"]:
            interpretation = "Some sampled timestamps cannot be classified"
            recommendation = "Verify UNKNOWN samples before drawing a conclusion."
        elif counts["inside"]:
            interpretation = "All sampled timestamps match the configured schedule"
            recommendation = "Time matches support, but do not prove, a maintenance explanation. Keep monitoring."
        else:
            interpretation = "No usable timestamps were sampled"
            recommendation = "Keep monitoring until timestamp evidence is available."

        occurrences = checked.get("source_occurrence_count")
        if type(occurrences) is not int or not 0 <= occurrences <= 1_000_000_000:
            occurrences = None
        report["findings"][fingerprint] = {
            "title": one_line(family.get("title", "Unnamed finding"), 150),
            "family_id": family_id,
            "audit_priority": one_line(family.get("final_priority", ""), 20),
            "user_status": one_line(saved.get("status", ""), 20),
            "feedback_updated_at_utc": one_line(saved.get("updated_at_utc", ""), 50),
            "maintenance_window": window,
            "source_status": one_line(checked.get("status", "unavailable"), 32),
            "source_message": one_line(checked.get("message", ""), 200),
            "source_occurrence_count": occurrences,
            "sample_count": len(samples),
            "counts": counts,
            "interpretation": interpretation,
            "recommendation": recommendation,
            "samples": samples,
        }
    return report


def save_maintenance_snapshot(report: dict) -> bool:
    """Save a *separate* atomic snapshot, without touching Sonos evidence."""
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(
            prefix=".ha-audit-maintenance-", suffix=".tmp",
            dir=MAINTENANCE_EVIDENCE_FILE.parent,
        )
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, MAINTENANCE_EVIDENCE_FILE)
        return True
    except OSError:
        return False
    finally:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def describe_maintenance_window(window: dict) -> str:
    """Render saved user schedule as data, not as an independently proven event."""
    frequency = one_line(window.get("schedule", "daily"), 32)
    weekdays = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    if frequency == "weekly":
        selected = window.get("weekdays", [])
        if isinstance(selected, list):
            frequency += " (" + ", ".join(weekdays[d] for d in selected
                  if type(d) is int and 0 <= d <= 6) + ")"
    elif frequency == "monthly_date":
        frequency += " (day " + one_line(window.get("day_of_month", "?"), 4) + ")"
    elif frequency == "monthly_weekday":
        day = window.get("weekday")
        weekday = weekdays[day] if type(day) is int and 0 <= day <= 6 else "?"
        frequency += " (" + one_line(window.get("occurrence", "?"), 10) + " " + weekday + ")"
    return (frequency + ", " + one_line(window.get("start_local", "?"), 5)
            + "–" + one_line(window.get("end_local", "?"), 5)
            + " (" + one_line(window.get("timezone", "?"), 64) + ")")


def maintenance_evidence_lines(fingerprint: str, report: dict) -> list[str]:
    evidence = report.get("findings", {}).get(fingerprint)
    if not isinstance(evidence, dict):
        return []
    counts = evidence["counts"]
    lines = [
        "- **Automatic maintenance-window check (UTC):** "
        + one_line(report.get("generated_at_utc", ""), 50),
        "- **User-configured maintenance schedule:** "
        + describe_maintenance_window(evidence["maintenance_window"]),
        "- **Sampled source-record timestamps:** "
        + str(evidence["sample_count"])
        + "; INSIDE " + str(counts["inside"])
        + ", OUTSIDE " + str(counts["outside"])
        + ", UNKNOWN " + str(counts["unknown"]),
    ]
    occurrences = evidence.get("source_occurrence_count")
    if occurrences is not None:
        lines.append("- **Grouped log occurrences:** " + str(occurrences)
                     + " (not individually timestamped or classified)")
    lines.extend([
        "- **Maintenance interpretation:** " + evidence["interpretation"],
        "- **Suggested next action:** " + evidence["recommendation"],
    ])
    if not evidence["samples"]:
        lines.append("- **Evidence availability:** " + (
            evidence["source_message"] or "No usable source timestamps"))
    else:
        for sample in evidence["samples"]:
            lines.append(
                "  - `" + sample["observed_at_utc"] + "` (UTC) — "
                + sample["window_match"].upper() + " (local: `"
                + sample["observed_at_local"] + "`)"
            )
    lines.append(
        "- **Limitation:** Time matching does not prove a scheduled reboot "
        "happened or caused the error. Only sampled first/last log timestamps "
        "were checked. All other occurrences are unassessed. "
        "Original audit priority and user status unchanged."
    )
    return lines


def evidence_lines(fingerprint: str, report: dict) -> list[str]:
    evidence = report.get("findings", {}).get(fingerprint)
    if not isinstance(evidence, dict):
        return []
    counts = evidence["counts"]
    lines = [
        "- **Automatic Recorder check (UTC):** "
        + one_line(report.get("generated_at_utc", ""), 50),
        "- **User-confirmed power switch:** `" + evidence["power_entity_id"] + "`",
        "- **Sampled source-record timestamps:** "
        + str(evidence["sample_count"])
        + "; OFF " + str(counts["off"])
        + ", ON " + str(counts["on"])
        + ", UNKNOWN " + str(counts["unknown"]),
        "- **Evidence interpretation:** " + evidence["interpretation"],
        "- **Suggested next action:** " + evidence["recommendation"],
    ]
    if not evidence["samples"]:
        lines.append("- **Evidence availability:** " + (
            evidence["source_message"] or "No usable source timestamps"))
    else:
        for sample in evidence["samples"]:
            lines.append(
                "  - `" + sample["observed_at_utc"] + "` — "
                + sample["power_state"].upper()
                + " (" + sample["evidence"] + ")"
            )
    lines.append("- **Limitation:** Only sampled first/last log timestamps were "
                 "checked. OFF is consistent with power loss, not proof of cause. "
                 "Unsampled errors are not assessed. Original audit priority unchanged.")
    return lines


def make_appendix(context: dict, findings: dict, evidence: dict | None = None,
                  maintenance_evidence: dict | None = None) -> str:
    investigations = context.get("investigations")
    if context.get("schema_version") != 1 or not isinstance(investigations, dict):
        return ""

    found = findings.get("families", []) if isinstance(findings, dict) else []
    current = {
        row.get("stable_fingerprint"): row
        for row in found
        if isinstance(row, dict) and isinstance(row.get("stable_fingerprint"), str)
    } if isinstance(found, list) else {}

    evidence = evidence or {}
    maintenance_evidence = maintenance_evidence or {}
    records = []
    for fingerprint, data in list(investigations.items())[:MAX_FEEDBACK_ITEMS]:
        if not isinstance(fingerprint, str) or not isinstance(data, dict):
            continue
        status = data.get("status")
        note = data.get("note")
        if not isinstance(status, str) or status not in VALID_STATUSES or not isinstance(note, str) or not note.strip():
            continue
        current_row = current.get(fingerprint)
        title = (current_row.get("title") if current_row else None) or data.get("title") or "Unnamed finding"
        updated_at = one_line(data.get("updated_at_utc", "Not recorded"), 48)
        count = len(data.get("history", [])) if isinstance(data.get("history"), list) else 0
        records.append({
            "title": one_line(title, 150),
            "status": status,
            "note": one_line(note, 4000),
            "updated_at": updated_at,
            "history_count": count,
            "present": current_row is not None,
            "priority": one_line(current_row.get("final_priority", ""), 20) if current_row else "",
            "fingerprint": fingerprint,
        })

    if not records:
        return ""

    # Visible current findings first; then retain context for historical issues.
    records.sort(key=lambda row: (not row["present"], row["title"].casefold()))
    lines = [
        START_MARKER,
        "## Saved investigation context (user feedback)",
        "",
        "These notes were entered through the HA Audit web interface and saved",
        "across runs. They are **user-reported context**, not independently",
        "verified causes or findings. The original audit priorities remain unchanged.",
        "Do not treat an 'Explained' or 'Resolved' label as proof that new errors",
        "are harmless. Compare new evidence and timestamps with these notes,",
        "and ask for verification if they conflict or are insufficient.",
        "",
    ]
    for row in records:
        presence = (
            f"Current finding; audit priority: {row['priority']}"
            if row["present"] else "Historical finding; not in current result"
        )
        lines.extend([
            f"### {row['title']}",
            f"- **User investigation status:** {row['status']}",
            f"- **Audit presence:** {presence}",
            f"- **Last user update (UTC):** {row['updated_at']}",
            f"- **Saved changes:** {row['history_count']} (full history held locally)",
            "- **User's latest note:**",
            f"> {row['note']}",
            "",
        ])
        if row["present"]:
            verification = evidence_lines(row["fingerprint"], evidence)
            if verification:
                lines.extend(verification)
                lines.append("")
            maintenance_verification = maintenance_evidence_lines(
                row["fingerprint"], maintenance_evidence
            )
            if maintenance_verification:
                lines.extend(maintenance_verification)
                lines.append("")
    lines += [END_MARKER, ""]
    return "\n".join(lines)


def update_handoff(handoff_path: Path, appendix: str) -> bool:
    if not appendix:
        return False
    try:
        content = handoff_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    # Running the stage twice never duplicates user context.
    start = content.find(START_MARKER)
    if start != -1:
        end = content.find(END_MARKER, start)
        if end == -1:
            # Unrecognised or interrupted appendix; preserve the original.
            return False
        content = content[:start].rstrip() + "\n" + content[end + len(END_MARKER):].lstrip("\n")
    updated = content.rstrip() + "\n\n" + appendix

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(prefix=".ha-audit-handoff-", suffix=".tmp", dir=handoff_path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, handoff_path)
        temp_path = None
    finally:
        if temp_path is not None:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    return True


def main() -> None:
    context = read_json_file(CONTEXT_FILE)
    if context is None:
        # First startup, or no user feedback saved. Keep the original handoff.
        return
    findings = read_json_file(FINDINGS_FILE) or {}
    # One bounded live evidence check per saved physical-switch relationship.
    # This checks Recorder at audit time; it does not modify audit findings.
    evidence = gather_power_evidence(context, findings)
    save_evidence_snapshot(evidence)
    maintenance_evidence = gather_maintenance_evidence(context, findings)
    save_maintenance_snapshot(maintenance_evidence)
    appendix = make_appendix(context, findings, evidence, maintenance_evidence)
    update_handoff(HANDOFF_FILE, appendix)


if __name__ == "__main__":
    main()
