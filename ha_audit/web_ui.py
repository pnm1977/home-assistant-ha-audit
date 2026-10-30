#!/usr/bin/env python3
"""HA Audit Ingress UI: findings and persistent user investigation feedback.

Feedback is deliberately separate from audit evidence and priority calculations.
Physical power-control relationships and recurring maintenance schedules can
be recorded as structured user context, not treated as verified causes.
Last-audit power and maintenance-window checks are shown as sampled evidence
only, never proof of cause or reasons to suppress issues. Latest-activity
indicators reuse HA Audit's independent cross-audit recurrence evidence.
It is stored in the app's private /config directory and survives audit runs.
"""

from __future__ import annotations

import html
import json
import os
import re
import secrets
import tempfile
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

from power_state_evidence import check_power_state

PORT = int(os.environ.get("HA_AUDIT_WEB_PORT", "8099"))
REPORT = Path("/config/ha_audit_latest.txt")
ISSUES = Path("/config/log_priority_final.json")
AI_EVIDENCE = Path("/config/ha_audit_ai_evidence.json")
HANDOFF = Path("/config/ha_audit_ai_handoff.md")
CONTEXT = Path("/config/investigation_context.json")
POWER_SNAPSHOT = Path("/config/investigation_evidence.json")
MAINTENANCE_SNAPSHOT = Path("/config/investigation_maintenance_evidence.json")
RECURRENCE_REPORT = Path("/config/log_recurrence.json")
RUN_STATE = Path("/config/ha_audit_run_status.json")
CORE_READINESS = Path("/config/update_readiness_audit.json")
CORE_CORRELATION = Path("/config/upgrade_correlation_audit.json")
CORE_GENERIC_CHECKS = Path("/config/core_compatibility_checks_audit.json")
MAX_REPORT_BYTES = 256 * 1024
MAX_HANDOFF_BYTES = 256 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_POST_BYTES = 65536
MAX_NOTE_LENGTH = 4000
MAX_POWER_ENTITY_LENGTH = 128
MAX_MAINTENANCE_TZ_LENGTH = 64
MAINTENANCE_TIME = re.compile(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]\Z")
MAINTENANCE_TZ = re.compile(r"(?:UTC|[A-Za-z][A-Za-z0-9_+\-]*(?:/[A-Za-z0-9_+\-]+){1,3})\Z")
MAINTENANCE_FREQUENCIES = ("daily", "weekly", "monthly_date", "monthly_weekday")
MAINTENANCE_OCCURRENCES = ("first", "second", "third", "fourth", "last")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
INGRESS_PROXY = "172.30.32.2"
ALLOW_LOCALHOST = os.environ.get("HA_AUDIT_WEB_TEST_LOCAL", "") == "1"
STATUSES = ("Investigating", "Monitoring", "Explained", "Resolved")
CSRF_TOKEN = secrets.token_urlsafe(32)
WRITE_LOCK = threading.Lock()


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def initial_context() -> dict:
    return {
        "schema_version": 1,
        "created_at_utc": utc_now(),
        "scheduled_events": [],
        "investigations": {},
    }


def initialize_context() -> str | None:
    """Create private context only on first launch; never overwrite it."""
    try:
        CONTEXT.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(CONTEXT, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(initial_context(), file, indent=2, ensure_ascii=False)
            file.write("\n")
        return None
    except FileExistsError:
        return None
    except OSError as exc:
        return f"Could not initialize investigation storage: {exc.strerror or type(exc).__name__}"


def read_json(path: Path) -> dict | None:
    try:
        if path.stat().st_size > MAX_JSON_BYTES:
            return None
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (FileNotFoundError, OSError, UnicodeError, json.JSONDecodeError):
        return None


def report_is_current(kind: str, path: Path) -> bool:
    """Fail closed when a run marker says the latest audit is not complete.

    Older installations without a run marker remain readable until the
    runtime begins creating one. Once the marker exists, malformed status,
    a failed stage, or a report older than the run cannot be treated as
    evidence from the latest audit.
    """
    if not RUN_STATE.exists():
        return True  # Legacy reports, before run-state tracking is enabled.
    state = read_json(RUN_STATE)
    if not state or state.get("status") != "complete":
        return False
    if state.get({
        "summary": "summary_status",
        "handoff": "handoff_status",
        "issues": "issues_status",
    }[kind]) != "ok":
        return False
    try:
        started = datetime.fromisoformat(
            str(state["run_started_at_utc"]).replace("Z", "+00:00")
        )
        if started.tzinfo is None:
            return False
        # Allow the filesystem's timestamp precision to vary slightly.
        return path.stat().st_mtime + 2 >= started.timestamp()
    except (KeyError, TypeError, ValueError, OverflowError, OSError):
        return False


def read_summary() -> str:
    if not report_is_current("summary", REPORT):
        return ("The latest audit is incomplete or its report is not verified. "
                "Previous audit results are not displayed as current. "
                "Check the app Log for failed stages, then restart the audit.")
    try:
        if REPORT.stat().st_size > MAX_REPORT_BYTES:
            return "The latest report is too large to display."
        return REPORT.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "No audit summary yet. Start HA Audit to generate its first report."
    except (OSError, UnicodeError):
        return "The latest audit summary could not be read."


def read_handoff() -> str | None:
    """Return the generated AI handoff, including saved investigation feedback."""
    if not report_is_current("handoff", HANDOFF):
        return None
    try:
        if HANDOFF.stat().st_size > MAX_HANDOFF_BYTES:
            return None
        text = HANDOFF.read_text(encoding="utf-8")
        return text if text.strip() else None
    except (FileNotFoundError, OSError, UnicodeError):
        return None


def build_ai_export() -> str:
    """Expose the complete local handoff, not just the short audit summary."""
    handoff = read_handoff()
    if handoff is None:
        return (
            '<h2>Share with AI</h2>'
            '<p class="muted">AI handoff not available yet. Run HA Audit first.</p>'
        )
    return (
        '<h2>Share with AI</h2>'
        '<p class="muted">Includes the latest audit evidence and any saved investigation notes. '
        'Review before sharing outside your Home Assistant.</p>'
        '<button type="button" id="copy-ai-handoff">Copy for AI</button> '
        '<a href="ai-handoff.md" download="ha_audit_ai_handoff.md">Download handoff</a>'
        '<span id="copy-result" role="status" aria-live="polite"></span>'
        '<details id="ai-handoff-details"><summary>View / select handoff text</summary>'
        '<textarea id="ai-handoff-text" rows="12" readonly aria-label="AI handoff text">'
        + escape(handoff) + '</textarea></details>'
    )


# Kept in this Python file so no additional repository file is needed.
# JavaScript is served as a separate resource with a restrictive CSP.
COPY_JS = r"""(function () {
  'use strict';
  const btn = document.getElementById('copy-ai-handoff');
  const field = document.getElementById('ai-handoff-text');
  const result = document.getElementById('copy-result');
  const detail = document.getElementById('ai-handoff-details');
  if (!btn || !field || !result || !detail) return;
  btn.addEventListener('click', async function () {
    const handoff = field.value;
    if (!handoff) return;
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error('Clipboard API unavailable');
      }
      await navigator.clipboard.writeText(handoff);
      result.textContent = ' Copied — paste into your AI chat.';
      return;
    } catch (_) {
      // Useful when browser clipboard permission is unavailable in Ingress.
      detail.open = true;
      field.focus();
      field.select();
      try {
        if (document.execCommand && document.execCommand('copy')) {
          result.textContent = ' Copied — paste into your AI chat.';
          return;
        }
      } catch (_) {}
      result.textContent = ' Select the text below and copy it manually.';
    }
  });
}());

// Each investigation has its own schedule selector. Keep irrelevant fields
// out of view without removing them from the form; server validation always
// checks only the fields relevant to the selected frequency.
(function () {
  'use strict';
  document.querySelectorAll('.maintenance-settings').forEach(function (fieldset) {
    const frequency = fieldset.querySelector('select[name="maintenance_frequency"]');
    if (!frequency) return;
    const sections = fieldset.querySelectorAll('[data-maintenance-for]');
    function update() {
      sections.forEach(function (section) {
        section.hidden = section.getAttribute('data-maintenance-for') !== frequency.value;
      });
    }
    frequency.addEventListener('change', update);
    update();
  });
}());"""


def current_families() -> list[dict]:
    if not report_is_current("issues", ISSUES):
        return []
    payload = read_json(ISSUES)
    if not payload or not isinstance(payload.get("families"), list):
        return []
    return [family for family in payload["families"] if isinstance(family, dict)]



def current_reader_guidance() -> dict[str, dict[str, str]]:
    """Return scoped, same-run explanations keyed by stable issue ID.

    AI evidence is optional. Do not show descriptions from an old run, a
    different audit version, a different issue family, or incomplete reports.
    The runtime's run marker is required for this additional UI display;
    older installations without it simply omit the expandable guidance.
    """
    if not RUN_STATE.exists():
        return {}
    if not (report_is_current("issues", ISSUES)
            and report_is_current("issues", AI_EVIDENCE)):
        return {}

    state = read_json(RUN_STATE)
    priority = read_json(ISSUES)
    evidence = read_json(AI_EVIDENCE)
    if not state or not priority or not evidence:
        return {}
    version = priority.get("audit_version")
    if (not isinstance(version, str) or not version
            or evidence.get("audit_version") != version):
        return {}
    running_version = os.environ.get("HA_AUDIT_VERSION")
    if running_version and running_version != version:
        return {}

    # A filesystem mtime alone cannot establish that these are the same run:
    # check both report timestamps against the completed run marker as well.
    try:
        def stamp(value):
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("Timezone missing")
            return parsed.timestamp()

        started = stamp(state["run_started_at_utc"])
        finished = stamp(state["run_finished_at_utc"])
        issue_time = stamp(priority["generated_at"])
        evidence_time = stamp(evidence["generated_at"])
        if not (started - 2 <= issue_time <= evidence_time <= finished + 2):
            return {}
    except (KeyError, ValueError, TypeError, OverflowError, OSError):
        return {}

    if not isinstance(evidence.get("system_issues"), list):
        return {}
    result = {}
    duplicates = set()
    for issue in evidence["system_issues"]:
        if not isinstance(issue, dict):
            continue
        issue_id = issue.get("stable_issue_id")
        family_id = issue.get("family_id")
        summary = issue.get("reader_summary")
        if (not isinstance(issue_id, str) or not issue_id
                or not isinstance(family_id, str) or not family_id
                or not isinstance(summary, dict)):
            continue
        # Duplicate IDs are ambiguous; do not select an arbitrary entry.
        if issue_id in result:
            duplicates.add(issue_id)
            continue
        result[issue_id] = {
            "family_id": family_id,
            "observed": summary.get("observed"),
            "first_check": summary.get("first_check"),
            "uncertainty": summary.get("uncertainty"),
        }
    for issue_id in duplicates:
        result.pop(issue_id, None)
    return result


def render_reader_guidance(family: dict, guidance: dict[str, dict[str, str]]) -> str:
    """Display existing structured evidence, without inventing a diagnosis."""
    fingerprint = family.get("stable_fingerprint")
    if not isinstance(fingerprint, str):
        return ""
    item = guidance.get(fingerprint)
    if not isinstance(item, dict) or item.get("family_id") != family.get("family_id"):
        return ""

    observed = item.get("observed")
    first_check = item.get("first_check")
    uncertainty = item.get("uncertainty")
    if not any(isinstance(value, str) and value.strip()
               for value in (observed, first_check, uncertainty)):
        return ""

    def row(label: str, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            return ""
        # Avoid unbounded HTML and escape all report-derived text.
        cleaned = value.strip()
        safe_value = escape(cleaned[:700] + ("… [truncated]" if len(cleaned) > 700 else ""))
        return '<p><strong>' + label + ':</strong> ' + safe_value + '</p>'

    return (
        '<details class="reader-guidance">'
        '<summary>What happened / first check</summary>'
        + row("What happened", observed)
        + row("Suggested first check", first_check or
              "No specific first check is available from this audit.")
        + (row("Still unknown", uncertainty) or
           '<p class="muted">Remaining uncertainty not described in this report.</p>')
        + '</details>'
    )


def latest_activity_by_fingerprint() -> dict[str, str] | None:
    """Read the existing independent cross-audit recurrence evidence.

    Home Assistant retains deduplicated System Log records. A historical
    RECURRING 24H+ class does not say whether this *audit* found new activity.
    Reuse log_recurrence.json's last_activity_status instead of inferring
    fresh errors from first/last timestamps or cumulative occurrence counts.

    Require both reports to come from the same audit run. If this cannot be
    established, omit activity claims rather than reporting 'no new errors'.
    """
    report = read_json(RECURRENCE_REPORT)
    issues = read_json(ISSUES)
    if (not report or not issues or report.get("status") != "ok"
            or not isinstance(report.get("families"), list)
            or report.get("audit_version") != issues.get("audit_version")):
        return None
    try:
        recurrence_at = datetime.fromisoformat(
            str(report["generated_at"]).replace("Z", "+00:00")
        )
        priority_at = datetime.fromisoformat(
            str(issues["generated_at"]).replace("Z", "+00:00")
        )
        difference = (priority_at - recurrence_at).total_seconds()
        if (recurrence_at.tzinfo is None or priority_at.tzinfo is None
                or not 0 <= difference <= 30):
            return None
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

    # Only current, securely matched records. History may also include
    # findings which are no longer present in this audit.
    current = {
        family.get("stable_fingerprint"): family.get("family_id")
        for family in issues.get("families", [])
        if isinstance(family, dict)
        and isinstance(family.get("stable_fingerprint"), str)
        and isinstance(family.get("family_id"), str)
    }
    statuses = {}
    for row in report["families"]:
        if not isinstance(row, dict) or row.get("seen_in_latest_audit") is not True:
            continue
        key = row.get("stable_fingerprint")
        if (not isinstance(key, str)
                or row.get("family_id") != current.get(key)):
            continue
        status = row.get("last_activity_status")
        if status in ("NEW ACTIVITY", "RETAINED EVIDENCE", "BASELINE"):
            statuses[key] = status
    return statuses


def activity_status_line(family: dict, statuses: dict[str, str] | None) -> str:
    """Careful run-to-run context, never a fault verdict or priority change."""
    key = family.get("stable_fingerprint")
    status = statuses.get(key) if statuses is not None else None
    messages = {
        "NEW ACTIVITY": (
            "New System Log activity observed since the previous audit. "
            "The timestamp of any user repair is not assessed."
        ),
        "RETAINED EVIDENCE": (
            "Retained log evidence; no independently new activity detected in "
            "this audit. This does not prove the errors have stopped."
        ),
        "BASELINE": (
            "First audit observation; no earlier comparison available."
        ),
    }
    if status not in messages:
        return ''
    return ('<div class="activity-evidence muted"><strong>Latest audit activity:</strong> '
            + escape(messages[status]) + '</div>')


def activity_focus_hint(family: dict, statuses: dict[str, str] | None) -> str:
    """A short *last run* indicator for already-monitored/explained issues."""
    status = statuses.get(family.get("stable_fingerprint")) if statuses else None
    if status == "NEW ACTIVITY":
        return "new activity in latest audit"
    if status == "RETAINED EVIDENCE":
        return "no new activity detected in latest audit"
    if status == "BASELINE":
        return "first observation; no comparison yet"
    return ""


def load_context() -> dict | None:
    data = read_json(CONTEXT)
    if (not data or data.get("schema_version") != 1
            or not isinstance(data.get("investigations"), dict)):
        return None
    return data


def current_manual_review_scope() -> tuple[str, str, list[dict]] | None:
    """List *exact* unassessed official groups in this completed Core audit.

    A stale, inconsistent, or missing report must not accept confirmations.
    The user does not supply versions or group names independently.
    """
    if not report_is_current("summary", REPORT):
        return None
    readiness, correlation = read_json(CORE_READINESS), read_json(CORE_CORRELATION)
    if not isinstance(readiness, dict) or not isinstance(correlation, dict):
        return None
    window = readiness.get("core_upgrade_window")
    scope = correlation.get("scope")
    summary = correlation.get("summary")
    rows = correlation.get("correlations")
    if (not isinstance(window, dict) or window.get("pending") is not True
            or not isinstance(scope, dict) or scope.get("dynamic_correlation_performed") is not True
            or not isinstance(summary, dict) or not isinstance(rows, list)
            or type(summary.get("insufficient_evidence_count")) is not int
            or type(summary.get("official_crossed_group_count")) is not int
            or summary["official_crossed_group_count"] != len(rows)):
        return None
    installed, target = window.get("installed_version"), window.get("target_version")
    if (not isinstance(installed, str) or not installed
            or not isinstance(target, str) or not target):
        return None
    # When audit run state exists, both inputs must belong to this run.
    run_started_timestamp = None
    if RUN_STATE.exists():
        state = read_json(RUN_STATE)
        try:
            started = datetime.fromisoformat(str(state["run_started_at_utc"]).replace("Z", "+00:00"))
            if (started.tzinfo is None or started.utcoffset() is None
                    or any(path.stat().st_mtime + 2 < started.timestamp()
                           for path in (CORE_READINESS, CORE_CORRELATION))):
                return None
            run_started_timestamp = started.timestamp()
        except (KeyError, TypeError, ValueError, OSError, OverflowError):
            return None
    groups, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            return None
        if row.get("correlation_status") != "insufficient_evidence":
            continue
        release, heading = row.get("release_family"), row.get("heading")
        if (not isinstance(release, str) or not release or len(release) > 40
                or not isinstance(heading, str) or not heading or len(heading) > 200
                or (release, heading) in seen):
            return None
        seen.add((release, heading))
        groups.append({"release_family": release, "heading": heading})
    if len(groups) != summary["insufficient_evidence_count"]:
        return None

    # Dynamic correlation records the *raw* insufficient-evidence groups.
    # The readiness engine separately reconciles them against completed
    # generic compatibility checks. Use that same engine here rather than
    # asking the user to manually confirm a change already assessed locally.
    generic = read_json(CORE_GENERIC_CHECKS)
    if generic is not None and run_started_timestamp is not None:
        try:
            if CORE_GENERIC_CHECKS.stat().st_mtime + 2 < run_started_timestamp:
                generic = None  # Do not display an earlier run's clearance.
        except OSError:
            generic = None
    if generic is not None:
        from readiness_guidance import reconcile_dynamic_insufficient_evidence
        reconciled = reconcile_dynamic_insufficient_evidence(
            correlation, generic,
            installed_version=installed, target_version=target,
        )
        if (reconciled.get("status") == "reconciled"
                and reconciled.get("original_insufficient_count") == len(groups)
                and reconciled.get("remaining_insufficient_count")
                == len(reconciled.get("unresolved_groups", []))):
            remaining = {
                (row["release_family"], row["heading"])
                for row in reconciled["unresolved_groups"]
            }
            groups = [row for row in groups
                      if (row["release_family"], row["heading"]) in remaining]
    return installed, target, groups


def save_manual_core_review(release_family: str, official_group: str,
                            decision: str) -> tuple[int, str]:
    """Record or revoke an *explicit* user assertion; never infer a clearance."""
    if decision not in ("confirmed", "remove"):
        return 400, "Choose a valid manual review action."
    scope = current_manual_review_scope()
    if scope is None:
        return 409, "Current Core compatibility evidence is incomplete or stale. Run HA Audit again."
    installed, target, groups = scope
    if not any(row["release_family"] == release_family and row["heading"] == official_group
               for row in groups):
        return 400, "This change is not an unassessed group in the latest Core audit."
    with WRITE_LOCK:
        data = load_context()
        if data is None:
            return 503, "Saved feedback is unreadable; nothing was changed."
        old = data.get("manual_compatibility_review", {})
        if not isinstance(old, dict):
            return 503, "Existing manual review data is invalid; nothing was changed."
        # Reviews from another version window are kept out of the current input.
        if (old.get("schema_version") == 1 and old.get("installed_version") == installed
                and old.get("target_version") == target):
            reviews = old.get("reviews", [])
            if not isinstance(reviews, list) or len(reviews) > 100:
                return 503, "Existing manual reviews are invalid; nothing was changed."
        else:
            reviews = []
        validated = []
        for row in reviews:
            if not isinstance(row, dict):
                return 503, "Existing manual reviews are invalid; nothing was changed."
            if row.get("release_family") == release_family and row.get("official_group") == official_group:
                continue
            validated.append(row)
        if decision == "confirmed":
            validated.append({
                "release_family": release_family,
                "official_group": official_group,
                "source": "explicit_user_confirmation",
                "outcome": "user_checked_no_issue",
                "confirmed_by_user": True,
                "reviewed_at": utc_now(),
            })
        data["manual_compatibility_review"] = {
            "schema_version": 1,
            "installed_version": installed,
            "target_version": target,
            "reviews": validated,
        }
        try:
            atomic_save(data)
        except OSError:
            return 503, "Could not save manual review; nothing was changed."
    return 200, ("Manual confirmation saved. Rerun HA Audit to apply it."
                 if decision == "confirmed" else
                 "Manual confirmation revoked. Rerun HA Audit to refresh readiness.")


def build_manual_core_review() -> str:
    """Small opt-in section. User confirmation is not automatic evidence."""
    scope = current_manual_review_scope()
    if scope is None:
        return ('<h2>Core compatibility manual review</h2><p class="muted">'
                'No current, verified Core-change report is available for manual review.</p>')
    installed, target, groups = scope
    if not groups:
        return ('<h2>Core compatibility manual review</h2><p class="muted">'
                'No change groups currently require manual evidence collection here.</p>')
    data = load_context()
    stored = data.get("manual_compatibility_review", {}) if data else {}
    reviews = (stored.get("reviews", []) if isinstance(stored, dict)
               and stored.get("installed_version") == installed
               and stored.get("target_version") == target else [])
    if not isinstance(reviews, list):
        reviews = []
    confirmed = {(r.get("release_family"), r.get("official_group"))
                 for r in reviews if isinstance(r, dict)
                 and r.get("source") == "explicit_user_confirmation"
                 and r.get("confirmed_by_user") is True}
    rows = []
    for row in groups:
        release, heading = row["release_family"], row["heading"]
        checked = (release, heading) in confirmed
        decision = "remove" if checked else "confirmed"
        label = "Revoke my confirmation" if checked else "Save my confirmation"
        checkbox = ('' if checked else
                    '<label><input type="checkbox" name="confirmed" value="yes" required> '
                    'I reviewed the official change and found no issue for this installation.</label>')
        rows.append(
            '<div class="focus-card"><strong>' + escape(release) + ' — ' + escape(heading) + '</strong>'
            + ('<p>Manually confirmed for this exact upgrade.</p>' if checked else
               '<p class="muted">Not confirmed. Only tick after checking this change yourself.</p>')
            + '<form method="post" action="">'
            + '<input type="hidden" name="token" value="' + escape(CSRF_TOKEN) + '">'
            + '<input type="hidden" name="action" value="manual_core_review">'
            + '<input type="hidden" name="release_family" value="' + escape(release) + '">'
            + '<input type="hidden" name="official_group" value="' + escape(heading) + '">'
            + '<input type="hidden" name="decision" value="' + decision + '">'
            + checkbox + '<button type="submit">' + escape(label) + '</button></form></div>'
        )
    return ('<h2>Core compatibility manual review</h2>'
            '<p class="muted">Current Core upgrade: ' + escape(installed) + ' → ' + escape(target)
            + '. These are unassessed changes, not confirmed problems. User reviews are assertions, '
            'not automatic verification or a safety guarantee. Rerun HA Audit after saving.</p>'
            '<div class="focus-grid">' + ''.join(rows) + '</div>')


def last_audit_power_snapshot() -> dict | None:
    """Read last audit's saved evidence; never query Recorder on page load.

    Ensure a new log-priority run cannot accidentally display evidence saved
    by an earlier run when the power-evidence stage did not complete.
    """
    snapshot = read_json(POWER_SNAPSHOT)
    if (not snapshot or snapshot.get("schema_version") != 1
            or not isinstance(snapshot.get("findings"), dict)):
        return None
    try:
        if POWER_SNAPSHOT.stat().st_mtime + 2 < ISSUES.stat().st_mtime:
            return None
    except OSError:
        return None
    return snapshot


def evidence_for_current_finding(family: dict, saved: dict,
                                 snapshot: dict | None) -> dict | None:
    """Only show evidence for the same current issue and saved relationship."""
    if not snapshot:
        return None
    key = family.get("stable_fingerprint")
    candidate = snapshot["findings"].get(key) if isinstance(key, str) else None
    if not isinstance(candidate, dict):
        return None
    if (candidate.get("family_id") != family.get("family_id")
            or candidate.get("power_entity_id") != saved.get("power_entity_id")
            or candidate.get("feedback_updated_at_utc") != saved.get("updated_at_utc")
            or candidate.get("audit_priority") != family.get("final_priority")):
        return None
    counts = candidate.get("counts")
    count = candidate.get("sample_count")
    if (not isinstance(counts, dict) or not isinstance(count, int)
            or isinstance(count, bool) or not 0 <= count <= 4):
        return None
    if any(type(counts.get(state)) is not int or not 0 <= counts[state] <= 4
           for state in ("off", "on", "unknown")):
        return None
    if sum(counts[state] for state in ("off", "on", "unknown")) != count:
        return None
    return candidate


def last_audit_maintenance_snapshot() -> dict | None:
    """Use only a completed audit's saved maintenance evidence, not live queries.

    A stale file from an earlier audit must not be treated as new evidence.
    """
    snapshot = read_json(MAINTENANCE_SNAPSHOT)
    if (not snapshot or snapshot.get("schema_version") != 1
            or not isinstance(snapshot.get("findings"), dict)):
        return None
    try:
        if MAINTENANCE_SNAPSHOT.stat().st_mtime + 2 < ISSUES.stat().st_mtime:
            return None
    except OSError:
        return None
    return snapshot


def matching_maintenance_evidence(family: dict, saved: dict,
                                  snapshot: dict | None) -> dict | None:
    """Match issue, user schedule, feedback revision, priority and bounded samples.

    Reject malformed or out-of-date evidence rather than showing confident but
    misleading counts. This check does not compare *every* source occurrence.
    """
    window = saved.get("maintenance_window")
    if not isinstance(window, dict) or not snapshot:
        return None
    key = family.get("stable_fingerprint")
    candidate = snapshot["findings"].get(key) if isinstance(key, str) else None
    if not isinstance(candidate, dict):
        return None
    if (candidate.get("family_id") != family.get("family_id")
            or candidate.get("maintenance_window") != window
            or candidate.get("feedback_updated_at_utc") != saved.get("updated_at_utc")
            or candidate.get("audit_priority") != family.get("final_priority")):
        return None
    counts = candidate.get("counts")
    count = candidate.get("sample_count")
    samples = candidate.get("samples")
    if (type(count) is not int or count < 0 or count > 4
            or not isinstance(counts, dict) or not isinstance(samples, list)
            or len(samples) != count):
        return None
    if any(type(counts.get(state)) is not int or not 0 <= counts[state] <= 4
           for state in ("inside", "outside", "unknown")):
        return None
    if sum(counts[state] for state in ("inside", "outside", "unknown")) != count:
        return None
    for item in samples:
        if not isinstance(item, dict) or item.get("window_match") not in ("inside", "outside", "unknown"):
            return None
        stamp = item.get("observed_at_utc")
        if not isinstance(stamp, str) or len(stamp) > 50:
            return None
        try:
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
    for state in ("inside", "outside", "unknown"):
        if sum(x["window_match"] == state for x in samples) != counts[state]:
            return None
    return candidate


def latest_maintenance_sample(candidate: dict) -> dict | None:
    """Find latest *sampled source record*; it may not be new activity.

    Do not infer a change date from free-text notes or equate 64 grouped
    occurrences with 64 independently dated errors.
    """
    samples = candidate.get("samples", [])
    if not samples:
        return None
    return max(samples, key=lambda x: datetime.fromisoformat(
        x["observed_at_utc"].replace("Z", "+00:00")))


def maintenance_focus_label(family: dict, saved: dict,
                            snapshot: dict | None) -> str:
    """Short factual indicator for Where to focus; never re-rank priority."""
    candidate = matching_maintenance_evidence(family, saved, snapshot)
    if not candidate or candidate.get("source_status") != "ok":
        return "maintenance evidence not verified" if isinstance(saved.get("maintenance_window"), dict) else ""
    counts = candidate["counts"]
    latest = latest_maintenance_sample(candidate)
    if latest is None:
        return "no usable maintenance timestamp samples"
    latest_match = latest["window_match"]
    if latest_match == "inside" and counts["outside"]:
        return "latest sampled error inside maintenance; earlier sample outside"
    if latest_match == "outside":
        return "latest sampled error outside maintenance — check"
    if counts["unknown"]:
        return "some maintenance timestamps unverified"
    if counts["outside"]:
        return "some sampled errors outside maintenance"
    return "sampled errors inside maintenance; continue monitoring"


def show_maintenance_summary(family: dict, saved: dict,
                             snapshot: dict | None) -> str:
    """Give sampled inside/outside evidence context without false reassurance."""
    if not isinstance(saved.get("maintenance_window"), dict):
        return ""
    candidate = matching_maintenance_evidence(family, saved, snapshot)
    if candidate is None:
        return (
            '<div class="maintenance-evidence"><strong>Maintenance evidence:</strong> '
            'No matching completed-audit check available.'
            '<div><strong>Investigation recommendation:</strong> '
            'Keep the finding under review until timestamp evidence is available.</div></div>'
        )
    counts = candidate["counts"]
    inside, outside, unknown = counts["inside"], counts["outside"], counts["unknown"]
    latest = latest_maintenance_sample(candidate)
    status_ok = candidate.get("source_status") == "ok"
    interpretation = ""
    if not status_ok or latest is None:
        interpretation = "Maintenance verification is incomplete or unavailable."
        recommendation = "Continue investigating or monitoring; do not assume maintenance caused the errors."
    else:
        stamp = latest["observed_at_utc"]
        latest_match = latest["window_match"]
        interpretation = "Most recent sampled log timestamp: " + stamp + " — " + latest_match.upper() + "."
        if latest_match == "outside":
            recommendation = (
                "Review the most recent OUTSIDE-window sample; a scheduled reboot "
                "does not explain that timestamp. Continue monitoring."
            )
        elif outside:
            recommendation = (
                "The most recent sampled timestamp matches maintenance, but "
                "older OUTSIDE-window evidence remains. Monitor for new errors "
                "outside the window; do not assume all grouped errors are explained."
            )
        elif unknown:
            recommendation = (
                "Some timestamps are unverified. Review them, and continue "
                "monitoring for errors outside the maintenance window."
            )
        elif inside:
            recommendation = (
                "Sampled timestamps match maintenance. Continue monitoring; "
                "the schedule match alone does not prove the cause."
            )
        else:
            recommendation = "No usable samples; continue monitoring."

    occurrences = candidate.get("source_occurrence_count")
    if type(occurrences) is int and 0 <= occurrences <= 1_000_000_000:
        context = '<div class="muted">Grouped log occurrences: ' + str(occurrences) +                   ' (not individually timestamped or classified).</div>'
    else:
        context = ""
    timestamp = snapshot.get("generated_at_utc", "") if snapshot else ""
    checked = ('<div class="muted">Last audit check: ' + escape(timestamp) + '</div>'
               if isinstance(timestamp, str) and len(timestamp) <= 40 else "")
    return (
        '<div class="maintenance-evidence"><strong>Maintenance evidence — sampled log times:</strong> '
        'INSIDE ' + str(inside) + ' · OUTSIDE ' + str(outside) + ' · UNKNOWN ' + str(unknown)
        + '<div>' + escape(interpretation) + '</div>'
        + '<div><strong>Investigation recommendation:</strong> ' + escape(recommendation) + '</div>'
        + context
        + '<div class="muted">These are first/last source-record samples, not proof '
          'that maintenance occurred. Do not interpret the latest sample as new '
          'activity or assume unsampled errors are explained. Original priority '
          'and saved status unchanged.</div>'
        + checked + '</div>'
    )


def power_sample_assessment(family: dict, saved: dict,
                            snapshot: dict | None) -> str:
    """Triage *sampled* power evidence, never technical priority or all errors.

    Returns one of: on, unknown, off_only, unverified. An OFF-only outcome
    means ONLY that the checked timestamps agree with deliberate power loss.
    Any ON sample takes precedence over OFF/UNKNOWN samples.
    """
    power_id = saved.get("power_entity_id")
    if (not isinstance(power_id, str)
            or not re.fullmatch(r"switch\.[a-z0-9_]+", power_id)):
        return "unverified"
    sample = evidence_for_current_finding(family, saved, snapshot)
    if sample is None or sample.get("source_status", "ok") != "ok":
        return "unverified"
    counts = sample["counts"]
    if counts["on"] > 0:
        return "on"
    if counts["unknown"] > 0:
        return "unknown"
    if counts["off"] > 0:
        return "off_only"
    return "unverified"


def show_power_summary(family: dict, saved: dict, snapshot: dict | None) -> str:
    """A short last-audit evidence line beside the user's investigation.

    The original HIGH/MEDIUM priority always remains in its own column.
    This is evidence about *sampled* log timestamps, not a fault verdict.
    """
    power_id = saved.get("power_entity_id")
    if not isinstance(power_id, str) or not re.fullmatch(r"switch\.[a-z0-9_]+", power_id):
        return ""
    fingerprint = family.get("stable_fingerprint", "")
    link = ('<a href="verify-power?fingerprint=' + escape(quote(fingerprint, safe=""))
            + '">Check current evidence</a>')
    sample = evidence_for_current_finding(family, saved, snapshot)
    if sample is None:
        return (
            '<div class="power-evidence"><strong>Power evidence:</strong> '
            'No matching completed-audit check available.'
            '<div><strong>Investigation recommendation:</strong> '
            'Keep the existing investigation open to verification until new '
            'power-state evidence is available.</div>' + link + '</div>'
        )
    counts = sample["counts"]
    off, on, unknown = counts["off"], counts["on"], counts["unknown"]
    assessment = power_sample_assessment(family, saved, snapshot)
    if assessment == "on":
        judgement = "Some sampled errors happened with power ON; investigate."
        recommendation = (
            "Investigate the power-ON samples, even if this finding was previously "
            "marked Explained or Resolved."
        )
    elif assessment == "unknown":
        judgement = "Power history is incomplete; do not dismiss unknown samples."
        recommendation = (
            "Verify the UNKNOWN samples. The saved explanation does not yet "
            "cover those timestamps."
        )
    elif assessment == "off_only":
        judgement = "All sampled errors happened with power OFF; consistent with intentional shutdown."
        if saved.get("status") in ("Explained", "Resolved"):
            recommendation = (
                "No immediate action indicated for these sampled OFF-only events. "
                "Watch for new ON or UNKNOWN errors."
            )
        else:
            recommendation = (
                "OFF-only samples support the proposed explanation; "
                "the investigation itself is still open."
            )
    else:
        judgement = "No usable log timestamp samples; no conclusion."
        recommendation = "Retain investigation attention until useful evidence is available."
    timestamp = snapshot.get("generated_at_utc", "") if snapshot else ""
    checked = ""
    if isinstance(timestamp, str) and len(timestamp) <= 40:
        checked = '<div class="muted">Last audit check: ' + escape(timestamp) + '</div>'
    return (
        '<div class="power-evidence"><strong>Power evidence — sampled log times:</strong> '
        'OFF ' + str(off) + ' · ON ' + str(on) + ' · UNKNOWN ' + str(unknown)
        + '<div>' + escape(judgement) + '</div>'
        + '<div><strong>Investigation recommendation:</strong> '
        + escape(recommendation) + '</div>'
        + '<div class="muted">Not every error was checked. Original priority unchanged.</div>'
        + checked + link + '</div>'
    )


def atomic_save(data: dict) -> None:
    """Replace private context only after a complete, durable JSON write."""
    temp_name: str | None = None
    try:
        fd, temp_name = tempfile.mkstemp(prefix=".ha-audit-context-", suffix=".tmp", dir=CONTEXT.parent)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, CONTEXT)
        temp_name = None
    finally:
        if temp_name is not None:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def validate_maintenance_window(
    start: str, end: str, timezone_name: str,
    frequency: str | None = None,
    weekdays: list[str] | None = None,
    month_day: str | None = None,
    occurrence: str | None = None,
    weekday: str | None = None,
) -> tuple[dict | None, str | None]:
    """Validate a local-time recurring maintenance schedule without using it as evidence.

    Weekday numbers use Python/ISO ordering (Monday=0, Sunday=6).
    An overnight window belongs to its *start* day's schedule. Monthly day 31
    is valid but does not run in shorter months. Timezone/DST handling is for
    the future verifier; this stage only saves user-reported configuration.
    """
    start, end, timezone_name = start.strip(), end.strip(), timezone_name.strip()
    if not (start or end or timezone_name):
        return None, None
    if not (start and end and timezone_name):
        return None, "Provide start time, end time and timezone, or clear all three."
    if not MAINTENANCE_TIME.fullmatch(start) or not MAINTENANCE_TIME.fullmatch(end):
        return None, "Enter maintenance times in 24-hour HH:MM format."
    if start == end:
        return None, "Maintenance start and end times must be different."
    if (len(timezone_name) > MAX_MAINTENANCE_TZ_LENGTH
            or not MAINTENANCE_TZ.fullmatch(timezone_name)):
        return None, "Enter an IANA timezone such as Europe/London."

    frequency = "daily" if frequency is None else frequency.strip()
    if frequency not in MAINTENANCE_FREQUENCIES:
        return None, "Choose a valid maintenance frequency."

    result = {
        "schedule": frequency,
        "start_local": start,
        "end_local": end,
        "timezone": timezone_name,
    }
    if frequency == "weekly":
        if not isinstance(weekdays, list) or not weekdays or len(weekdays) > 7:
            return None, "Choose at least one weekday for weekly maintenance."
        if any(day not in ("0", "1", "2", "3", "4", "5", "6") for day in weekdays):
            return None, "Choose valid weekdays for weekly maintenance."
        days = sorted({int(day) for day in weekdays})
        if len(days) != len(weekdays):
            return None, "A weekday was selected more than once."
        result["weekdays"] = days
    elif frequency == "monthly_date":
        if not isinstance(month_day, str) or not re.fullmatch(r"[1-9]|[12][0-9]|3[01]", month_day):
            return None, "Enter a calendar day from 1 to 31 for monthly maintenance."
        result["day_of_month"] = int(month_day)
    elif frequency == "monthly_weekday":
        if occurrence not in MAINTENANCE_OCCURRENCES:
            return None, "Choose first, second, third, fourth or last for monthly maintenance."
        if weekday not in ("0", "1", "2", "3", "4", "5", "6"):
            return None, "Choose a weekday for monthly maintenance."
        result["occurrence"] = occurrence
        result["weekday"] = int(weekday)
    return result, None


def save_feedback(fingerprint: str, status: str, note: str,
                  power_entity_id: str = "",
                  maintenance_start_local: str | None = None,
                  maintenance_end_local: str | None = None,
                  maintenance_timezone: str | None = None,
                  maintenance_frequency: str | None = None,
                  maintenance_weekdays: list[str] | None = None,
                  maintenance_month_day: str | None = None,
                  maintenance_occurrence: str | None = None,
                  maintenance_weekday: str | None = None) -> tuple[int, str]:
    if status not in STATUSES:
        return 400, "Choose a valid investigation status."
    note = note.strip()
    if not note or len(note) > MAX_NOTE_LENGTH:
        return 400, f"Please enter a note of 1–{MAX_NOTE_LENGTH} characters."
    power_entity_id = power_entity_id.strip()
    if (len(power_entity_id) > MAX_POWER_ENTITY_LENGTH
            or (power_entity_id and not re.fullmatch(r"switch\.[a-z0-9_]+", power_entity_id))):
        return 400, "Enter a valid switch entity ID, or leave the field blank."
    if not fingerprint or len(fingerprint) > 100:
        return 400, "Invalid finding identifier."

    # Older callers that do not include maintenance fields preserve the saved
    # schedule. Older daily-only forms still save as 'daily'. Clearing all
    # three time fields explicitly removes the schedule without data loss.
    has_maintenance_fields = any(value is not None for value in (
        maintenance_start_local, maintenance_end_local, maintenance_timezone,
        maintenance_frequency, maintenance_weekdays, maintenance_month_day,
        maintenance_occurrence, maintenance_weekday,
    ))
    maintenance_window = None
    if has_maintenance_fields:
        if not all(isinstance(value, str) for value in (
                maintenance_start_local, maintenance_end_local, maintenance_timezone)):
            return 400, "Invalid maintenance fields."
        if any(value is not None and not isinstance(value, str) for value in (
                maintenance_frequency, maintenance_month_day,
                maintenance_occurrence, maintenance_weekday)):
            return 400, "Invalid maintenance fields."
        maintenance_window, error = validate_maintenance_window(
            maintenance_start_local, maintenance_end_local, maintenance_timezone,
            maintenance_frequency, maintenance_weekdays, maintenance_month_day,
            maintenance_occurrence, maintenance_weekday,
        )
        if error:
            return 400, error

    # Accept only an ID from the current evidence, not arbitrary file/data keys.
    matching = next(
        (item for item in current_families()
         if item.get("stable_fingerprint") == fingerprint), None
    )
    if matching is None:
        return 400, "This finding is no longer in the latest audit. Refresh and try again."

    with WRITE_LOCK:
        data = load_context()
        if data is None:
            return 503, "Investigation storage is unreadable; nothing was changed."
        existing = data["investigations"].get(fingerprint, {})
        if not isinstance(existing, dict):
            return 503, "This investigation record is invalid; nothing was changed."
        history = existing.get("history", [])
        if not isinstance(history, list) or len(history) > 1000:
            return 503, "Investigation history is invalid; nothing was changed."

        timestamp = utc_now()
        entry = {"at_utc": timestamp, "status": status, "note": note,
                 "power_entity_id": power_entity_id, "source": "user_feedback"}
        if has_maintenance_fields:
            # Preserve an auditable record of the user's schedule changes,
            # including deliberate removal (None).
            entry["maintenance_window"] = maintenance_window
        updated = {
            **existing,
            "family_id": str(matching.get("family_id", ""))[:100],
            "title": str(matching.get("title", "Unnamed issue"))[:200],
            "status": status,
            "note": note,
            "power_entity_id": power_entity_id,
            "updated_at_utc": timestamp,
            "history": [*history, entry],
        }
        if has_maintenance_fields:
            if maintenance_window is None:
                updated.pop("maintenance_window", None)
            else:
                updated["maintenance_window"] = maintenance_window
        data["investigations"][fingerprint] = updated
        try:
            atomic_save(data)
        except OSError:
            return 503, "Could not save feedback; nothing was changed."
    return 200, "Investigation feedback saved. It will be available after restarting HA Audit."



def render_power_evidence(fingerprint: str) -> tuple[int, bytes]:
    """On-demand read-only verification of a saved switch relationship.

    Requires both a current audit finding and a physical switch saved by the
    user. The imported evidence module performs bounded Recorder API reads;
    this UI does not change feedback, audit results, or issue priorities.
    """
    family = next(
        (item for item in current_families()
         if item.get("stable_fingerprint") == fingerprint), None
    )
    context = load_context()
    saved = context.get("investigations", {}).get(fingerprint) if context else None
    switch = saved.get("power_entity_id") if isinstance(saved, dict) else None
    if (family is None or not isinstance(switch, str)
            or not re.fullmatch(r"switch\.[a-z0-9_]+", switch)):
        return 404, b"No saved power switch for this current finding."

    title = str(family.get("title", "Unnamed issue"))
    result = check_power_state(str(family.get("family_id", "")), switch)
    samples = result.get("samples", [])
    labels = {
        "off": "OFF — consistent with expected power loss",
        "on": "ON — investigate further",
        "unknown": "UNKNOWN — no conclusion",
    }
    rows = []
    for sample in samples if isinstance(samples, list) else []:
        if not isinstance(sample, dict):
            continue
        stamp = escape(sample.get("observed_at_utc", "Not provided"))
        state = str(sample.get("power_state", "unknown"))
        label = escape(labels.get(state, labels["unknown"]))
        evidence = escape(sample.get("evidence", "No details"))
        rows.append(f"<tr><td>{stamp}</td><td>{label}</td><td>{evidence}</td></tr>")

    if rows:
        details = ('<div class="scroll"><table><thead><tr><th>Log timestamp (UTC)</th>'
                   '<th>Switch at timestamp</th><th>Evidence</th></tr></thead><tbody>'
                   + "".join(rows) + '</tbody></table></div>')
    else:
        reason = result.get("message", "No suitable log timestamps are available.")
        details = '<p>' + escape(reason) + '</p>'

    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>HA Audit — Power-state evidence</title><style>'
            ':root{font-family:system-ui,sans-serif;color-scheme:light dark}'
            'body{max-width:1080px;margin:0 auto;padding:1.25rem;line-height:1.5}'
            '.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%}'
            'th,td{border-bottom:1px solid GrayText;padding:.65rem;text-align:left}'
            'th{font-weight:700}a{color:LinkText}code{overflow-wrap:anywhere}'
            '</style></head><body><p><a href="./">&larr; Back to HA Audit</a></p>'
            '<h1>Power-state evidence</h1><h2>' + escape(title) + '</h2>'
            '<p>Saved power-control switch: <code>' + escape(switch) + '</code></p>'
            + details
            + '<p><strong>Interpretation:</strong> These checks use at most four sampled '
              'first/last System Log record timestamps, <strong>not every error occurrence</strong>. '
              'An OFF result is consistent with the power-off explanation but does not prove '
              'the cause. ON warrants investigation; missing history is UNKNOWN. '
              'The switch relationship remains user-confirmed. '
              '<strong>No audit priorities, findings, or saved feedback are changed.</strong></p>'
            '</body></html>')
    return 200, page.encode("utf-8")


def build_focus() -> str:
    """Put evidenced investigation attention first, without suppressing logs.

    Saved feedback is user-reported. A matching, completed-audit check can
    direct review to power-ON or UNKNOWN samples. Only a user-explained or
    resolved finding with exclusively OFF samples is put in the lower-action
    group; its unexamined errors, priority and original data remain visible.
    """
    context = load_context()
    if context is None:
        return (
            '<h2>Where to focus</h2>'
            '<p class="error">Saved investigation context cannot be read. '
            'No attention guidance has been calculated.</p>'
        )

    families = [family for family in current_families()
                if family.get("final_priority") in ("VERY HIGH", "HIGH", "MEDIUM")]
    if not families:
        return (
            '<h2>Where to focus</h2>'
            '<p class="muted">No current HIGH or MEDIUM findings to review.</p>'
        )

    investigations = context["investigations"]
    power_snapshot = last_audit_power_snapshot()
    maintenance_snapshot = last_audit_maintenance_snapshot()
    activity_statuses = latest_activity_by_fingerprint()
    priority_order = {"VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2}
    groups: dict[str, list[dict]] = {
        "Investigate / continue": [],
        "Monitoring": [],
        "Explanation to verify": [],
        "Sampled power-off — no immediate action": [],
    }
    assessments: dict[str, str] = {}
    for family in families:
        key = family.get("stable_fingerprint")
        if not isinstance(key, str) or not key:
            continue
        saved = investigations.get(key, {})
        if not isinstance(saved, dict):
            saved = {}
        status = saved.get("status")
        assessment = power_sample_assessment(family, saved, power_snapshot)
        assessments[key] = assessment
        if assessment == "on":
            # Fresh evidence overrides user-reported 'Explained'/'Monitoring'
            # in triage only; their saved investigation status is untouched.
            group = "Investigate / continue"
        elif status == "Monitoring":
            group = "Monitoring"
        elif status in ("Explained", "Resolved"):
            group = ("Sampled power-off — no immediate action"
                     if assessment == "off_only" else "Explanation to verify")
        else:
            # Unreviewed findings and investigations in progress stay actionable.
            group = "Investigate / continue"
        groups[group].append(family)

    for group in groups.values():
        group.sort(key=lambda f: (
            priority_order.get(f.get("final_priority"), 99),
            0 if assessments.get(f.get("stable_fingerprint")) == "on" else 1,
            str(f.get("title", "")),
        ))

    card_text = {
        "Investigate / continue": (
            "Unreviewed/open issues or sampled errors while their controlling "
            "switch was ON. Prioritise these investigations."
        ),
        "Monitoring": (
            "A change or observation is being monitored; check for fresh evidence."
        ),
        "Explanation to verify": (
            "User marked these Explained/Resolved, but the latest power evidence "
            "is missing, incomplete or unknown. Confirm before dismissing errors."
        ),
        "Sampled power-off — no immediate action": (
            "Previously explained findings with exclusively OFF samples. "
            "No immediate action is indicated for those samples; unchecked "
            "errors and future ON/UNKNOWN events still need review."
        ),
    }
    cards: list[str] = []
    for title, group in groups.items():
        count = len(group)
        examples: list[str] = []
        for item in group[:4]:
            assessment = assessments.get(item.get("stable_fingerprint"), "unverified")
            extra = ""
            if assessment == "on":
                extra = ' <span class="focus-flag">(power ON during sampled error)</span>'
            elif assessment == "unknown":
                extra = ' <span class="muted">(power state unknown for some samples)</span>'
            elif assessment == "off_only" and title == "Sampled power-off — no immediate action":
                extra = ' <span class="muted">(checked samples OFF only)</span>'
            saved = investigations.get(item.get("stable_fingerprint"), {})
            if isinstance(saved, dict):
                maintenance_label = maintenance_focus_label(item, saved, maintenance_snapshot)
                if maintenance_label:
                    extra += ' <span class="muted">(' + escape(maintenance_label) + ')</span>'
            if title in ("Monitoring", "Explanation to verify", "Sampled power-off — no immediate action"):
                hint = activity_focus_hint(item, activity_statuses)
                if hint:
                    extra += ' <span class="muted">(' + escape(hint) + ')</span>'
            examples.append(
                '<li><strong>' + escape(item.get("final_priority", "")) + '</strong> '
                + escape(item.get("title", "Unnamed finding")) + extra + '</li>'
            )
        more = ('<p class="muted">And ' + str(count - 4) + ' more below.</p>') if count > 4 else ''
        cards.append(
            '<section class="focus-card"><h3>' + escape(title)
            + ' <span class="focus-count">(' + str(count) + ')</span></h3>'
            '<p class="muted">' + escape(card_text[title]) + '</p>'
            + ('<ul>' + ''.join(examples) + '</ul>' if examples else '<p>None.</p>')
            + more + '</section>'
        )
    return (
        '<h2>Where to focus</h2>'
        '<p class="muted">Investigation recommendations consider saved feedback '
        'and last-audit sampled power/maintenance evidence. Latest activity '
        'indicators use independent run-to-run System Log comparisons when available. '
        'A most-recent sample '
        'is not proof of new activity; historical outside-window evidence remains '
        'visible. This does <strong>not</strong> '
        'change original technical priority, recurrence, investigation status, '
        'or underlying System Log evidence.</p>'
        '<div class="focus-grid">' + ''.join(cards) + '</div>'
    )


def build_issues() -> str:
    families = current_families()
    if not families:
        return '<p class="muted">Issue details are not yet available; the full audit remains below.</p>'

    context = load_context()
    investigations = context.get("investigations", {}) if context else {}
    power_snapshot = last_audit_power_snapshot()
    maintenance_snapshot = last_audit_maintenance_snapshot()
    activity_statuses = latest_activity_by_fingerprint()
    reader_guidance = current_reader_guidance()
    if not context:
        return '<p class="error">Investigation storage cannot be read. Feedback is disabled.</p>'

    ranked = [family for family in families
              if family.get("final_priority") in ("VERY HIGH", "HIGH", "MEDIUM")]
    rank = {"VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2}
    ranked.sort(key=lambda item: (rank[item["final_priority"]], str(item.get("title", ""))))

    rows: list[str] = []
    for family in ranked[:20]:
        fingerprint = family.get("stable_fingerprint")
        if not isinstance(fingerprint, str) or not fingerprint:
            continue
        recurrence = family.get("recurrence", {})
        rec_class = recurrence.get("class", "Unknown") if isinstance(recurrence, dict) else "Unknown"
        saved = investigations.get(fingerprint, {})
        if not isinstance(saved, dict):
            saved = {}
        old_status = saved.get("status", "Not reviewed")
        old_note = saved.get("note", "")
        old_power_entity = saved.get("power_entity_id", "")
        old_window = saved.get("maintenance_window", {})
        if (not isinstance(old_window, dict)
                or old_window.get("schedule") not in MAINTENANCE_FREQUENCIES):
            old_window = {}
        old_maintenance_start = old_window.get("start_local", "")
        old_maintenance_end = old_window.get("end_local", "")
        old_maintenance_tz = old_window.get("timezone", "")
        old_frequency = old_window.get("schedule", "daily")
        old_weekdays = old_window.get("weekdays", [])
        if not isinstance(old_weekdays, list):
            old_weekdays = []
        old_month_day = old_window.get("day_of_month", "")
        old_occurrence = old_window.get("occurrence", "")
        old_weekday = old_window.get("weekday", "")
        if not isinstance(old_status, str) or old_status not in STATUSES:
            old_status = "Not reviewed"
        if not isinstance(old_note, str):
            old_note = ""
        if not isinstance(old_power_entity, str):
            old_power_entity = ""
        if not isinstance(old_maintenance_start, str):
            old_maintenance_start = ""
        if not isinstance(old_maintenance_end, str):
            old_maintenance_end = ""
        if not isinstance(old_maintenance_tz, str):
            old_maintenance_tz = ""
        options = "".join(
            '<option value="' + escape(item) + '"'
            + (' selected' if item == old_status else '')
            + '>' + escape(item) + '</option>'
            for item in STATUSES
        )
        frequency_labels = (
            ("daily", "Daily"),
            ("weekly", "Weekly — selected weekdays"),
            ("monthly_date", "Monthly — calendar date"),
            ("monthly_weekday", "Monthly — nth weekday"),
        )
        frequency_options = "".join(
            '<option value="' + value + '"' + (' selected' if value == old_frequency else '')
            + '>' + label + '</option>'
            for value, label in frequency_labels
        )
        weekly_checks = "".join(
            '<label><input type="checkbox" name="maintenance_weekdays" value="'
            + str(index) + '"' + (' checked' if index in old_weekdays else '')
            + '>' + escape(label) + '</label>'
            for index, label in enumerate(WEEKDAYS)
        )
        occurrence_options = "<option value=\"\">Select…</option>" + "".join(
            '<option value="' + item + '"'
            + (' selected' if item == old_occurrence else '')
            + '>' + item.capitalize() + '</option>'
            for item in MAINTENANCE_OCCURRENCES
        )
        weekday_options = '<option value="">Select…</option>' + "".join(
            '<option value="' + str(index) + '"'
            + (' selected' if index == old_weekday else '')
            + '>' + escape(label) + '</option>'
            for index, label in enumerate(WEEKDAYS)
        )
        # Keep the overview concise: notes stay inside Review / update.
        # Show last-run evidence without a live Recorder request on page load.
        summary = (escape(old_status)
                   + activity_status_line(family, activity_statuses)
                   + show_power_summary(family, saved, power_snapshot)
                   + show_maintenance_summary(family, saved, maintenance_snapshot))
        feedback_form = (
            '<details><summary>Review / update</summary>'
            '<form method="post" action="">'
            '<input type="hidden" name="token" value="' + escape(CSRF_TOKEN) + '">'
            '<input type="hidden" name="fingerprint" value="' + escape(fingerprint) + '">'
            '<label>Status <select name="status">' + options + '</select></label>'
            '<label>Power-control switch (optional) '
            '<input name="power_entity_id" type="text" maxlength="' + str(MAX_POWER_ENTITY_LENGTH) + '" '
            'pattern="switch[.][a-z0-9_]+" placeholder="switch.example_plug" '
            'value="' + escape(old_power_entity) + '"></label>'
            '<p class="muted">Only enter a switch you have confirmed physically powers this device. '
            'This relationship is user-reported until verified against Home Assistant evidence.</p>'
            '<fieldset class="maintenance-settings"><legend>Scheduled maintenance (optional)</legend>'
            '<p class="muted">Save a recurring local-time schedule; this is user-reported context, '
            'not proof maintenance occurred. To remove a schedule, clear Start, End and Time zone. '
            'Overnight windows belong to the day they start. Automatic verification comes later.</p>'
            '<label>Frequency <select name="maintenance_frequency">' + frequency_options + '</select></label>'
            '<div class="maintenance-extra" data-maintenance-for="weekly">'
            '<span>Days of week</span><div class="weekday-options">' + weekly_checks + '</div></div>'
            '<div class="maintenance-extra" data-maintenance-for="monthly_date">'
            '<label>Day of month (1–31) <input name="maintenance_month_day" type="number" '
            'min="1" max="31" step="1" placeholder="1–31" '
            'value="' + escape(old_month_day) + '"></label>'
            '<small class="muted">Day 31 is skipped in months without a 31st.</small></div>'
            '<div class="maintenance-extra" data-maintenance-for="monthly_weekday">'
            '<label>Occurrence <select name="maintenance_occurrence">' + occurrence_options + '</select></label>'
            '<label>Weekday <select name="maintenance_weekday">' + weekday_options + '</select></label>'
            '</div>'
            '<label>Start (local time) <input name="maintenance_start_local" type="time" step="60" '
            'value="' + escape(old_maintenance_start) + '"></label>'
            '<label>End (local time) <input name="maintenance_end_local" type="time" step="60" '
            'value="' + escape(old_maintenance_end) + '"></label>'
            '<label>Time zone (IANA) <input name="maintenance_timezone" type="text" '
            'maxlength="' + str(MAX_MAINTENANCE_TZ_LENGTH) + '" '
            'placeholder="Europe/London" value="' + escape(old_maintenance_tz) + '"></label>'
            '</fieldset>'
            '<label>What did you establish or change? '
            '<textarea name="note" maxlength="' + str(MAX_NOTE_LENGTH) + '" rows="8" required placeholder="What happened, why, or what to monitor next?">'
            + escape(old_note) + '</textarea></label>'
            '<button type="submit">Save feedback</button></form></details>'
        )
        rows.append(
            '<tr><td><strong>' + escape(family.get("final_priority", "")) + '</strong></td>'
            '<td>' + escape(family.get("title", "Unnamed issue"))
            + render_reader_guidance(family, reader_guidance) + '</td>'
            '<td>' + escape(rec_class) + '</td>'
            '<td><div>' + summary + '</div>' + feedback_form + '</td></tr>'
        )

    if not rows:
        return '<p class="muted">No current HIGH or MEDIUM findings with usable identifiers.</p>'
    return (
        '<div class="table-scroll"><table class="issues-table"><thead><tr><th>Priority</th><th>Finding</th>'
        '<th>Recurrence</th><th>Your investigation</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div>'
        '<p class="muted">Saved feedback is private and does not alter audit priorities. '
        'Saved notes are included in the AI handoff; original audit priorities stay unchanged.</p>'
    )


def render_page(message: str = "", *, error: bool = False) -> bytes:
    if not report_is_current("summary", REPORT):
        status_note = ('<p class="error" role="alert">Latest audit incomplete or '
                       'unverified. Earlier reports are hidden; check the app Log '
                       'and restart the audit.</p>')
    else:
        status_note = ""
    notice = ('<p role="status" class="' + ('error' if error else 'notice') + '">'
              + escape(message) + '</p>') if message else ""
    page = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HA Audit</title><style>
:root{font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color-scheme:light dark}
body{margin:0;background:Canvas;color:CanvasText}header{padding:1.25rem 1.5rem;border-bottom:1px solid GrayText}
main{margin:0 auto;max-width:1200px;padding:1.25rem 1.5rem 3rem}h1{margin:0;font-size:1.6rem}
h2{font-size:1.2rem;margin-top:1.8rem}.muted{opacity:.7;font-size:.92rem}
.table-scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;text-align:left}
th,td{border-bottom:1px solid GrayText;padding:.7rem .6rem;font-size:.92rem;vertical-align:top}
th{font-weight:700}td{min-width:100px}details{margin-top:.3rem}summary{cursor:pointer}
/* Give explanations a readable column even when investigation forms are open. */
.issues-table{table-layout:fixed;min-width:1050px}
.issues-table th:nth-child(1){width:9%}
.issues-table th:nth-child(2){width:33%}
.issues-table th:nth-child(3){width:12%}
.issues-table th:nth-child(4){width:46%}
.issues-table td{min-width:0;overflow-wrap:anywhere}
.issues-table form{min-width:0}
.issues-table input,.issues-table select,.issues-table textarea{max-width:100%;width:100%;box-sizing:border-box}
.issues-table input[type=checkbox]{width:auto}
form{display:grid;gap:.6rem;margin-top:.5rem;min-width:230px}label{display:grid;gap:.2rem}
#copy-ai-handoff{margin-right:.5rem}.full-summary{margin-top:2rem}
.full-summary>summary{font-size:1.18rem;font-weight:700}
.full-summary>pre{margin-top:1rem}
select,textarea,input,button{font:inherit;padding:.4rem;border-radius:5px}
fieldset{border:1px solid GrayText;border-radius:6px;display:grid;gap:.5rem;min-width:0}
fieldset p{margin:.1rem 0 .3rem}button{cursor:pointer;justify-self:start}
[hidden]{display:none!important}.maintenance-extra{display:grid;gap:.4rem}
.weekday-options{display:flex;gap:.6rem;flex-wrap:wrap}
.weekday-options label{display:inline-flex;gap:.2rem;align-items:center;white-space:nowrap;font-size:.9rem}
.weekday-options input{margin:0}
form textarea{box-sizing:border-box;width:100%;min-height:11rem;line-height:1.5;resize:vertical}
#ai-handoff-text{width:100%;box-sizing:border-box;margin:.6rem 0 1rem;font: .88rem ui-monospace,monospace;white-space:pre}
#copy-result{margin-left:.5rem;font-size:.9rem}a{color:LinkText}
.reader-guidance{font-size:.88rem;line-height:1.45}
.reader-guidance p{margin:.55rem 0;overflow-wrap:anywhere}
.focus-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}
.focus-card{border:1px solid GrayText;border-radius:8px;padding:.65rem 1rem}
.focus-card h3{font-size:1rem;margin:.35rem 0}
.focus-card p{margin:.5rem 0}.focus-card ul{padding-left:1.4rem;margin:.65rem 0}
.focus-card li{font-size:.9rem;margin:.35rem 0}
.focus-count{font-weight:400;opacity:.75}
.focus-flag{font-weight:600}
.power-evidence,.maintenance-evidence{border-left:3px solid GrayText;padding:.35rem 0 .35rem .65rem;margin-top:.6rem;
font-size:.87rem;line-height:1.5;max-width:370px}
.power-evidence a{display:inline-block;margin-top:.25rem}
pre{border:1px solid GrayText;border-radius:8px;padding:1rem;white-space:pre-wrap;
overflow-wrap:anywhere;line-height:1.5;font-size:.9rem}.notice{font-weight:700}
.error{font-weight:700;color:#b3261e}
</style></head><body><header><h1>HA Audit</h1><p class="muted">Investigation feedback · focused review</p></header>
<main>""" + status_note + notice + build_ai_export() + build_focus() + build_manual_core_review() + '<h2>Issues needing review</h2>' + build_issues() + """
<details class="full-summary"><summary>Show complete latest audit summary</summary><pre>""" + escape(read_summary()) + """</pre></details>
<p class="muted">Investigation feedback is stored privately and preserved across audit runs.</p>
</main><script src="copy.js" defer></script></body></html>"""
    return page.encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "HA-Audit-UI"
    sys_version = ""

    def _allowed(self) -> bool:
        peer = self.client_address[0]
        return peer == INGRESS_PROXY or (ALLOW_LOCALHOST and peer in ("127.0.0.1", "::1"))

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'self'; form-action 'self'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._allowed():
            self._send(403, b"Forbidden", "text/plain; charset=utf-8")
            return
        path = urlsplit(self.path).path
        if path == "/health":
            self._send(200, b"ok\n", "text/plain; charset=utf-8")
            return
        if path == "/verify-power":
            try:
                values = parse_qs(urlsplit(self.path).query, max_num_fields=2)
            except ValueError:
                self._send(400, b"Invalid query", "text/plain; charset=utf-8")
                return
            identifiers = values.get("fingerprint", [])
            if len(identifiers) != 1 or not (0 < len(identifiers[0]) <= 100):
                self._send(400, b"Invalid finding", "text/plain; charset=utf-8")
                return
            status, content = render_power_evidence(identifiers[0])
            content_type = ("text/html; charset=utf-8" if status == 200
                            else "text/plain; charset=utf-8")
            self._send(status, content, content_type)
            return
        if path == "/copy.js":
            self._send(200, COPY_JS.encode("utf-8"), "text/javascript; charset=utf-8")
            return
        if path == "/ai-handoff.md":
            handoff = read_handoff()
            if handoff is None:
                self._send(404, b"AI handoff unavailable", "text/plain; charset=utf-8")
                return
            self._send(200, handoff.encode("utf-8"), "text/markdown; charset=utf-8")
            return
        if path not in ("/", "/index.html"):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        self._send(200, render_page(), "text/html; charset=utf-8")

    def do_POST(self) -> None:
        if not self._allowed():
            self._send(403, b"Forbidden", "text/plain; charset=utf-8")
            return
        if urlsplit(self.path).path not in ("/", "/index.html"):
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/x-www-form-urlencoded":
            self._send(415, b"Unsupported form format", "text/plain; charset=utf-8")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_POST_BYTES:
            self._send(413, b"Invalid form size", "text/plain; charset=utf-8")
            return
        try:
            fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True, max_num_fields=24)
        except (UnicodeDecodeError, ValueError):
            self._send(400, b"Invalid form", "text/plain; charset=utf-8")
            return
        if fields.get("token") != [CSRF_TOKEN]:
            self._send(403, b"Invalid form token", "text/plain; charset=utf-8")
            return
        if fields.get("action") == ["manual_core_review"]:
            required_manual = {"token", "action", "release_family", "official_group", "decision"}
            if (set(fields) not in (required_manual, required_manual | {"confirmed"})
                    or any(len(fields.get(key, [])) != 1 for key in required_manual)
                    or fields["decision"][0] not in ("confirmed", "remove")
                    or (fields["decision"][0] == "confirmed" and fields.get("confirmed") != ["yes"])
                    or (fields["decision"][0] == "remove" and "confirmed" in fields)):
                self._send(400, b"Invalid manual review form", "text/plain; charset=utf-8")
                return
            status, message = save_manual_core_review(
                fields["release_family"][0], fields["official_group"][0], fields["decision"][0]
            )
            self._send(status, render_page(message, error=status != 200), "text/html; charset=utf-8")
            return
        if "action" in fields:
            self._send(400, b"Invalid action", "text/plain; charset=utf-8")
            return
        required = ("fingerprint", "status", "note")
        optional = ("power_entity_id", "maintenance_start_local",
                    "maintenance_end_local", "maintenance_timezone",
                    "maintenance_frequency", "maintenance_month_day",
                    "maintenance_occurrence", "maintenance_weekday")
        multi = "maintenance_weekdays"
        if (any(len(fields.get(field, [])) != 1 for field in required)
                or any(len(fields.get(field, [])) > 1 for field in optional)
                or len(fields.get(multi, [])) > 7
                or any(field not in (*required, *optional, multi, "token") for field in fields)):
            self._send(400, b"Invalid fields", "text/plain; charset=utf-8")
            return
        status, message = save_feedback(
            fields["fingerprint"][0], fields["status"][0], fields["note"][0],
            fields.get("power_entity_id", [""])[0],
            *(fields[field][0] if field in fields else None for field in (
                "maintenance_start_local", "maintenance_end_local",
                "maintenance_timezone", "maintenance_frequency")),
            fields.get("maintenance_weekdays", []),
            *(fields[field][0] if field in fields else None for field in (
                "maintenance_month_day", "maintenance_occurrence", "maintenance_weekday")),
        )
        self._send(status, render_page(message, error=status != 200), "text/html; charset=utf-8")


if __name__ == "__main__":
    warning = initialize_context()
    if warning:
        print("HA Audit: " + warning, flush=True)
    else:
        print("HA Audit: persistent investigation storage ready", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
