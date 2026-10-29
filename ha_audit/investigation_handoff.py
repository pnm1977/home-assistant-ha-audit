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
import tempfile
from pathlib import Path

CONTEXT_FILE = Path("/config/investigation_context.json")
FINDINGS_FILE = Path("/config/log_priority_final.json")
HANDOFF_FILE = Path("/config/ha_audit_ai_handoff.md")
START_MARKER = "<!-- HA_AUDIT_INVESTIGATION_CONTEXT_START -->"
END_MARKER = "<!-- HA_AUDIT_INVESTIGATION_CONTEXT_END -->"
MAX_BYTES = 1024 * 1024
MAX_FEEDBACK_ITEMS = 200
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


def make_appendix(context: dict, findings: dict) -> str:
    investigations = context.get("investigations")
    if context.get("schema_version") != 1 or not isinstance(investigations, dict):
        return ""

    found = findings.get("families", []) if isinstance(findings, dict) else []
    current = {
        row.get("stable_fingerprint"): row
        for row in found
        if isinstance(row, dict) and isinstance(row.get("stable_fingerprint"), str)
    } if isinstance(found, list) else {}

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
            "note": one_line(note, 500),
            "updated_at": updated_at,
            "history_count": count,
            "present": current_row is not None,
            "priority": one_line(current_row.get("final_priority", ""), 20) if current_row else "",
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
    appendix = make_appendix(context, findings)
    update_handoff(HANDOFF_FILE, appendix)


if __name__ == "__main__":
    main()
