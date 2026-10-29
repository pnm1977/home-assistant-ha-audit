#!/usr/bin/env python3
"""HA Audit Ingress UI: findings and persistent user investigation feedback.

Feedback is deliberately separate from audit evidence and priority calculations.
Physical power-control relationships can be recorded as structured user context,
but are not accepted as verified evidence or reasons to suppress issues.
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
from urllib.parse import parse_qs, urlsplit

PORT = int(os.environ.get("HA_AUDIT_WEB_PORT", "8099"))
REPORT = Path("/config/ha_audit_latest.txt")
ISSUES = Path("/config/log_priority_final.json")
HANDOFF = Path("/config/ha_audit_ai_handoff.md")
CONTEXT = Path("/config/investigation_context.json")
MAX_REPORT_BYTES = 256 * 1024
MAX_HANDOFF_BYTES = 256 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_POST_BYTES = 65536
MAX_NOTE_LENGTH = 4000
MAX_POWER_ENTITY_LENGTH = 128
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


def read_summary() -> str:
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
}());"""


def current_families() -> list[dict]:
    payload = read_json(ISSUES)
    if not payload or not isinstance(payload.get("families"), list):
        return []
    return [family for family in payload["families"] if isinstance(family, dict)]


def load_context() -> dict | None:
    data = read_json(CONTEXT)
    if (not data or data.get("schema_version") != 1
            or not isinstance(data.get("investigations"), dict)):
        return None
    return data


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


def save_feedback(fingerprint: str, status: str, note: str,
                  power_entity_id: str = "") -> tuple[int, str]:
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
        data["investigations"][fingerprint] = {
            **existing,
            "family_id": str(matching.get("family_id", ""))[:100],
            "title": str(matching.get("title", "Unnamed issue"))[:200],
            "status": status,
            "note": note,
            "power_entity_id": power_entity_id,
            "updated_at_utc": timestamp,
            "history": [*history, entry],
        }
        try:
            atomic_save(data)
        except OSError:
            return 503, "Could not save feedback; nothing was changed."
    return 200, "Investigation feedback saved. It will be available after restarting HA Audit."


def build_focus() -> str:
    """Separate investigation attention from the original technical priority.

    This is deliberately a UI-only triage view. Feedback is user-reported,
    not proof of a root cause or a reason to suppress errors. Do not write
    to log_priority_final.json or change any existing investigation record.
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
    priority_order = {"VERY HIGH": 0, "HIGH": 1, "MEDIUM": 2}
    groups: dict[str, list[dict]] = {
        "Investigate / continue": [], "Monitoring": [], "Explanation to verify": []
    }
    for family in families:
        key = family.get("stable_fingerprint")
        if not isinstance(key, str) or not key:
            continue
        saved = investigations.get(key, {})
        status = saved.get("status") if isinstance(saved, dict) else None
        if status == "Monitoring":
            group = "Monitoring"
        elif status in ("Explained", "Resolved"):
            group = "Explanation to verify"
        else:
            # Unreviewed findings and investigations in progress are actionable.
            group = "Investigate / continue"
        groups[group].append(family)

    for group in groups.values():
        group.sort(key=lambda f: (
            priority_order.get(f.get("final_priority"), 99),
            str(f.get("title", "")),
        ))

    card_text = {
        "Investigate / continue": "No conclusion recorded yet, or investigation in progress.",
        "Monitoring": "A change or observation is being monitored; check for fresh evidence.",
        "Explanation to verify": "User has marked these explained or resolved; check that new errors agree with the explanation.",
    }
    cards: list[str] = []
    for title, group in groups.items():
        count = len(group)
        examples = "".join(
            '<li><strong>' + escape(item.get("final_priority", "")) + '</strong> '
            + escape(item.get("title", "Unnamed finding")) + '</li>'
            for item in group[:4]
        )
        extra = ('<p class="muted">And ' + str(count - 4) + ' more below.</p>') if count > 4 else ''
        cards.append(
            '<section class="focus-card"><h3>' + escape(title)
            + ' <span class="focus-count">(' + str(count) + ')</span></h3>'
            '<p class="muted">' + escape(card_text[title]) + '</p>'
            + ('<ul>' + examples + '</ul>' if examples else '<p>None.</p>')
            + extra + '</section>'
        )
    return (
        '<h2>Where to focus</h2>'
        '<p class="muted">Suggested investigation workflow based on saved user feedback. '
        'This is <strong>not</strong> a verified cause, severity reduction or '
        'replacement for the original audit priority.</p>'
        '<div class="focus-grid">' + ''.join(cards) + '</div>'
    )


def build_issues() -> str:
    families = current_families()
    if not families:
        return '<p class="muted">Issue details are not yet available; the full audit remains below.</p>'

    context = load_context()
    investigations = context.get("investigations", {}) if context else {}
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
        if not isinstance(old_status, str) or old_status not in STATUSES:
            old_status = "Not reviewed"
        if not isinstance(old_note, str):
            old_note = ""
        if not isinstance(old_power_entity, str):
            old_power_entity = ""
        options = "".join(
            '<option value="' + escape(item) + '"'
            + (' selected' if item == old_status else '')
            + '>' + escape(item) + '</option>'
            for item in STATUSES
        )
        # Keep the overview concise: details and existing notes stay inside Review / update.
        summary = escape(old_status)
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
            '<label>What did you establish or change? '
            '<textarea name="note" maxlength="' + str(MAX_NOTE_LENGTH) + '" rows="8" required placeholder="What happened, why, or what to monitor next?">'
            + escape(old_note) + '</textarea></label>'
            '<button type="submit">Save feedback</button></form></details>'
        )
        rows.append(
            '<tr><td><strong>' + escape(family.get("final_priority", "")) + '</strong></td>'
            '<td>' + escape(family.get("title", "Unnamed issue")) + '</td>'
            '<td>' + escape(rec_class) + '</td>'
            '<td><div>' + summary + '</div>' + feedback_form + '</td></tr>'
        )

    if not rows:
        return '<p class="muted">No current HIGH or MEDIUM findings with usable identifiers.</p>'
    return (
        '<div class="table-scroll"><table><thead><tr><th>Priority</th><th>Finding</th>'
        '<th>Recurrence</th><th>Your investigation</th></tr></thead><tbody>'
        + "".join(rows) + '</tbody></table></div>'
        '<p class="muted">Saved feedback is private and does not alter audit priorities. '
        'Saved notes are included in the AI handoff; original audit priorities stay unchanged.</p>'
    )


def render_page(message: str = "", *, error: bool = False) -> bytes:
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
form{display:grid;gap:.6rem;margin-top:.5rem;min-width:230px}label{display:grid;gap:.2rem}
#copy-ai-handoff{margin-right:.5rem}.full-summary{margin-top:2rem}
.full-summary>summary{font-size:1.18rem;font-weight:700}
.full-summary>pre{margin-top:1rem}
select,textarea,button{font:inherit;padding:.4rem;border-radius:5px}button{cursor:pointer;justify-self:start}
form textarea{box-sizing:border-box;width:100%;min-height:11rem;line-height:1.5;resize:vertical}
#ai-handoff-text{width:100%;box-sizing:border-box;margin:.6rem 0 1rem;font: .88rem ui-monospace,monospace;white-space:pre}
#copy-result{margin-left:.5rem;font-size:.9rem}a{color:LinkText}
.focus-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem}
.focus-card{border:1px solid GrayText;border-radius:8px;padding:.65rem 1rem}
.focus-card h3{font-size:1rem;margin:.35rem 0}
.focus-card p{margin:.5rem 0}.focus-card ul{padding-left:1.4rem;margin:.65rem 0}
.focus-card li{font-size:.9rem;margin:.35rem 0}
.focus-count{font-weight:400;opacity:.75}
pre{border:1px solid GrayText;border-radius:8px;padding:1rem;white-space:pre-wrap;
overflow-wrap:anywhere;line-height:1.5;font-size:.9rem}.notice{font-weight:700}
.error{font-weight:700;color:#b3261e}
</style></head><body><header><h1>HA Audit</h1><p class="muted">Investigation feedback · focused review</p></header>
<main>""" + notice + build_ai_export() + build_focus() + '<h2>Issues needing review</h2>' + build_issues() + """
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
            fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True, max_num_fields=8)
        except (UnicodeDecodeError, ValueError):
            self._send(400, b"Invalid form", "text/plain; charset=utf-8")
            return
        if fields.get("token") != [CSRF_TOKEN]:
            self._send(403, b"Invalid form token", "text/plain; charset=utf-8")
            return
        if (any(len(fields.get(field, [])) != 1 for field in ("fingerprint", "status", "note"))
                or len(fields.get("power_entity_id", [""])) != 1):
            self._send(400, b"Invalid fields", "text/plain; charset=utf-8")
            return
        status, message = save_feedback(
            fields["fingerprint"][0], fields["status"][0], fields["note"][0],
            fields.get("power_entity_id", [""])[0],
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
